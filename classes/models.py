from datetime import timedelta

from django.conf import settings
from django.db import models
from django.db.models import Count, Exists, OuterRef, Prefetch, Q
from django.urls import reverse
from django.utils import timezone

from catalog.models import Subtopic


class TutoringClassQuerySet(models.QuerySet):
    def upcoming(self, now=None):
        return self.filter(starts_at__gte=now or timezone.now())

    def past(self, now=None):
        return self.filter(starts_at__lt=now or timezone.now())

    def with_card_data(self):
        """Everything a class card renders, in a fixed number of queries however many cards."""
        # Explicit order_by: Django ignores Meta.ordering once a query has a GROUP BY.
        return (
            self.select_related("subject", "mentor__user")
            .prefetch_related(
                Prefetch("subtopics", queryset=Subtopic.objects.select_related("unit"))
            )
            .annotate(enrolment_count=Count("enrolments", distinct=True))
            .order_by("starts_at", "pk")
        )

    def with_enrolment_flag(self, user):
        if not user.is_authenticated:
            return self.annotate(is_enrolled=models.Value(False))
        return self.annotate(
            is_enrolled=Exists(
                Enrolment.objects.filter(tutoring_class=OuterRef("pk"), student=user)
            )
        )


class TutoringClass(models.Model):
    """A live, mentor-led class on Zoom. Called a "class" everywhere users can see it."""

    DURATION_CHOICES = [
        (30, "30 min"),
        (45, "45 min"),
        (60, "1 hr"),
        (90, "1 hr 30 min"),
        (120, "2 hr"),
    ]

    mentor = models.ForeignKey(
        "accounts.MentorProfile", on_delete=models.PROTECT, related_name="classes"
    )
    subject = models.ForeignKey("catalog.Subject", on_delete=models.PROTECT, related_name="classes")
    subtopics = models.ManyToManyField("catalog.Subtopic", related_name="classes")
    title = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    starts_at = models.DateTimeField(db_index=True)
    duration_minutes = models.PositiveSmallIntegerField(choices=DURATION_CHOICES, default=60)
    meeting_url = models.URLField("Zoom link", max_length=500)
    meeting_id = models.CharField("Zoom meeting ID", max_length=32, blank=True)
    meeting_passcode = models.CharField("Zoom passcode", max_length=32, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    objects = TutoringClassQuerySet.as_manager()

    class Meta:
        ordering = ["starts_at"]
        verbose_name = "class"
        verbose_name_plural = "classes"
        constraints = [
            models.CheckConstraint(
                condition=Q(duration_minutes__gt=0), name="class_duration_positive"
            ),
        ]

    def __str__(self):
        return f"{self.title} ({self.subject}, {self.starts_at:%Y-%m-%d %H:%M} UTC)"

    def get_absolute_url(self):
        return reverse("classes:detail", args=[self.pk])

    @property
    def ends_at(self):
        return self.starts_at + timedelta(minutes=self.duration_minutes)

    def has_started(self, now=None) -> bool:
        return self.starts_at <= (now or timezone.now())

    def can_see_meeting(self, user) -> bool:
        """Zoom details are for the class's mentor, staff, and students who paid to enrol."""
        if not user.is_authenticated:
            return False
        if user.is_staff or self.mentor.user_id == user.pk:
            return True
        return self.enrolments.filter(student=user).exists()


class Enrolment(models.Model):
    # PROTECT: a class with enrolments can't be deleted, because students paid tokens for it.
    tutoring_class = models.ForeignKey(
        TutoringClass, on_delete=models.PROTECT, related_name="enrolments"
    )
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="enrolments"
    )
    tokens_spent = models.PositiveSmallIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["tutoring_class", "student"], name="one_enrolment_per_student_per_class"
            ),
        ]

    def __str__(self):
        return f"{self.student} in {self.tutoring_class.title}"


class ClassRequest(models.Model):
    """A student asking for a class on a unit that has none scheduled."""

    student = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="class_requests"
    )
    unit = models.ForeignKey("catalog.Unit", on_delete=models.CASCADE, related_name="requests")
    notes = models.TextField(blank=True)
    is_open = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.student} wants {self.unit}"
