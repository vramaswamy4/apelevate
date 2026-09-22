"""Demo accounts and classes so every screen has something on it. Development only."""

from datetime import timedelta

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from accounts.models import MentorApplication, MentorProfile, User
from catalog.models import Subject, Subtopic, Unit
from classes.models import ClassRequest, Enrolment, TutoringClass
from classes.services import enrol
from payments.bundles import get_bundle
from payments.services import complete_purchase, start_purchase

PASSWORD = "apelevate-demo"

# A tiny valid PDF, so the demo application's files download and open.
PDF = (
    b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj 2 0 obj<</Type/Pages/Kids[3 0 R]"
    b"/Count 1>>endobj 3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 200 100]>>endobj\n"
    b"trailer<</Root 1 0 R>>\n%%EOF\n"
)

PEOPLE = {
    "admin": ("admin@apelevate.test", "Amira", "Haddad"),
    "mentor": ("mentor@apelevate.test", "Priya", "Nair"),
    "mentor2": ("omar@apelevate.test", "Omar", "Farouk"),
    "student": ("student@apelevate.test", "Sam", "Carter"),
    "applicant": ("applicant@apelevate.test", "Lena", "Park"),
}
STUDENTS = [
    ("maya", "Maya", "Singh"),
    ("daniel", "Daniel", "Okafor"),
    ("zara", "Zara", "Ali"),
    ("leo", "Leo", "Martins"),
    ("hana", "Hana", "Yousef"),
]


class Command(BaseCommand):
    help = f"Create demo users (password: {PASSWORD}), classes, enrolments and requests."

    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError("seed_demo only runs with DJANGO_DEBUG=1.")
        if not Subject.objects.exists():
            raise CommandError("Run `manage.py seed_curriculum` first.")
        if User.objects.filter(email=PEOPLE["mentor"][0]).exists():
            self.stdout.write("Demo data already present.")
            return
        with transaction.atomic():
            self._seed()
        self.stdout.write(
            "Demo data ready. Sign in with any of: "
            + ", ".join(email for email, *_ in PEOPLE.values())
            + f" (password: {PASSWORD})"
        )

    def _user(self, email, first, last, **extra):
        return User.objects.create_user(
            email, PASSWORD, first_name=first, last_name=last, timezone="Asia/Dubai", **extra
        )

    def _tokens(self, user, bundle_key):
        purchase = start_purchase(user, get_bundle(bundle_key))
        complete_purchase(purchase)

    def _seed(self):
        now = timezone.now().replace(minute=0, second=0, microsecond=0)
        chem = Subject.objects.get(slug="ap-chemistry")
        calc = Subject.objects.get(slug="ap-calculus-ab")
        physics = Subject.objects.get(slug="ap-physics-1")

        self._user(*PEOPLE["admin"], is_staff=True, is_superuser=True)
        priya = self._user(*PEOPLE["mentor"])
        omar = self._user(*PEOPLE["mentor2"])
        sam = self._user(*PEOPLE["student"])
        lena = self._user(*PEOPLE["applicant"])
        students = [sam] + [
            self._user(f"{key}@apelevate.test", first, last) for key, first, last in STUDENTS
        ]

        priya_profile = MentorProfile.objects.create(
            user=priya,
            bio="Scored 5s in AP Chemistry and AP Calculus AB. Two years of peer tutoring.",
        )
        priya_profile.subjects.add(chem, calc)
        omar_profile = MentorProfile.objects.create(
            user=omar, bio="AP Physics 1 (5). Runs his school's physics olympiad club."
        )
        omar_profile.subjects.add(physics)

        for i, student in enumerate(students):
            self._tokens(student, "ten" if i == 0 else "five")

        def topics(subject, unit_number, count=3):
            return Subtopic.objects.filter(unit__subject=subject, unit__number=unit_number)[:count]

        plan = [
            # (mentor, subject, unit, title, days from now, hour UTC, minutes)
            (priya_profile, chem, 1, "Moles, mass spec and PES", -40, 14, 60),
            (priya_profile, chem, 2, "Lewis structures and VSEPR", -33, 14, 90),
            (priya_profile, calc, 1, "Limits from graphs and tables", -26, 15, 60),
            (priya_profile, chem, 5, "Rate laws without the panic", -12, 14, 60),
            (priya_profile, calc, 2, "The derivative, properly defined", -5, 15, 90),
            (omar_profile, physics, 1, "Kinematics graphs", -20, 16, 60),
            (priya_profile, chem, 7, "Equilibrium: Q versus K", 2, 14, 60),
            (priya_profile, calc, 3, "Chain rule drill", 4, 15, 45),
            (priya_profile, chem, 8, "Acids and bases: pH in five steps", 9, 14, 90),
            (omar_profile, physics, 2, "Free-body diagrams that score", 3, 16, 60),
            (omar_profile, physics, 4, "Momentum and collisions", 10, 16, 60),
            (priya_profile, calc, 6, "Riemann sums to the FTC", 16, 15, 60),
        ]
        for n, (mentor, subject, unit, title, days, hour, minutes) in enumerate(plan):
            starts_at = now.replace(hour=hour) + timedelta(days=days)
            is_past = days < 0
            c = TutoringClass.objects.create(
                mentor=mentor,
                subject=subject,
                title=title,
                description="Bring the practice set from the unit review. We'll work through "
                "the free-response questions that trip people up most.",
                # Past classes are created in the future so enrolment rules apply, then moved.
                starts_at=starts_at if not is_past else now + timedelta(days=30),
                duration_minutes=minutes,
                meeting_url=f"https://us02web.zoom.us/j/8{n:02d}4417290{n}",
                meeting_id=f"8{n:02d} 4417 290{n}",
                meeting_passcode=f"ape{n:03d}",
            )
            c.subtopics.set(topics(subject, unit))
            attendees = students[(n % 3) : (n % 3) + 2 + (n % 3)] if is_past else students[1:3]
            for student in attendees:
                student.refresh_from_db(fields=["token_balance"])
                if student.token_balance:
                    enrol(student, c)
            if is_past:
                TutoringClass.objects.filter(pk=c.pk).update(starts_at=starts_at)

        upcoming_for_sam = TutoringClass.objects.filter(starts_at__gt=now, subject=chem).first()
        if not Enrolment.objects.filter(tutoring_class=upcoming_for_sam, student=sam).exists():
            enrol(sam, upcoming_for_sam)

        application = MentorApplication(
            user=lena,
            subject=calc,
            bio="Senior at an IB school in Dubai; took AP Calculus AB as an extra exam.",
            ap_experience="Scored a 5 on AP Calculus AB in May. Self-studied most of it.",
            teaching_experience="Weekly homework help for Grade 10 students since January.",
            motivation="I remember exactly which parts of limits made no sense at first.",
        )
        application.score_report.save("score-report.pdf", ContentFile(PDF), save=False)
        application.cv.save("cv.pdf", ContentFile(PDF), save=False)
        application.save()

        ClassRequest.objects.create(
            student=students[3],
            unit=Unit.objects.get(subject=chem, number=6),
            notes="Calorimetry problems. Our teacher skipped half of it.",
        )
        ClassRequest.objects.create(
            student=sam, unit=Unit.objects.get(subject=calc, number=4), notes="Related rates."
        )
