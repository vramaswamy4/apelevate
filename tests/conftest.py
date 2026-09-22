from datetime import timedelta

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone

from accounts.models import MentorProfile, User
from catalog.models import Subject, Subtopic, Unit
from classes.models import TutoringClass
from payments.bundles import get_bundle
from payments.services import complete_purchase, start_purchase

PASSWORD = "correct-horse-battery-staple"
PDF_BYTES = b"%PDF-1.4\n%test\n"
PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"\x00" * 16


@pytest.fixture(autouse=True)
def _db(db):
    """Every test gets a database; there's nothing here worth testing without one."""


@pytest.fixture
def make_user():
    counter = iter(range(1, 10_000))

    def make(email=None, first_name="Test", last_name="User", **extra):
        n = next(counter)
        return User.objects.create_user(
            email or f"user{n}@example.com",
            PASSWORD,
            first_name=first_name,
            last_name=last_name,
            **extra,
        )

    return make


@pytest.fixture
def student(make_user):
    return make_user("student@example.com", "Sam", "Carter")


@pytest.fixture
def staff(make_user):
    return make_user("staff@example.com", "Amira", "Haddad", is_staff=True)


@pytest.fixture
def curriculum():
    """Two subjects, each with two units of three topics, plus a topic numbered 10."""
    subjects = {}
    for slug, name in [("ap-chemistry", "AP Chemistry"), ("ap-physics-1", "AP Physics 1")]:
        subject = Subject.objects.create(name=name, slug=slug)
        for u in (1, 2):
            unit = Unit.objects.create(subject=subject, number=u, name=f"{name} unit {u}")
            for t in (1, 2, 3):
                Subtopic.objects.create(unit=unit, number=t, name=f"Topic {u}.{t}")
        subjects[slug] = subject
    Subtopic.objects.create(
        unit=subjects["ap-chemistry"].units.get(number=1), number=10, name="Topic 1.10"
    )
    return subjects


@pytest.fixture
def chemistry(curriculum):
    return curriculum["ap-chemistry"]


@pytest.fixture
def physics(curriculum):
    return curriculum["ap-physics-1"]


@pytest.fixture
def mentor(make_user, chemistry):
    """A user with a mentor profile for AP Chemistry."""
    user = make_user("mentor@example.com", "Priya", "Nair")
    profile = MentorProfile.objects.create(user=user, bio="Scored a 5.")
    profile.subjects.add(chemistry)
    return user


@pytest.fixture
def make_class(mentor, chemistry):
    def make(starts_in=timedelta(days=3), mentor_user=None, subject=None, **fields):
        subject = subject or chemistry
        profile = (mentor_user or mentor).mentor_profile
        c = TutoringClass.objects.create(
            mentor=profile,
            subject=subject,
            title=fields.pop("title", "Moles and mass spec"),
            starts_at=timezone.now() + starts_in,
            meeting_url="https://us02web.zoom.us/j/81234567890?pwd=abc",
            meeting_id="812 3456 7890",
            meeting_passcode="s3cret",
            **fields,
        )
        c.subtopics.set(Subtopic.objects.filter(unit__subject=subject)[:2])
        return c

    return make


@pytest.fixture
def give_tokens():
    """Credit tokens the way production does: a verified (fake-provider) purchase."""

    def give(user, bundle_key="five"):
        purchase = start_purchase(user, get_bundle(bundle_key))
        complete_purchase(purchase)
        user.refresh_from_db()
        return purchase

    return give


@pytest.fixture
def pdf():
    return lambda name="doc.pdf": SimpleUploadedFile(name, PDF_BYTES, "application/pdf")


@pytest.fixture
def png():
    return lambda name="doc.png": SimpleUploadedFile(name, PNG_BYTES, "image/png")


@pytest.fixture
def make_application(pdf):
    from accounts.models import MentorApplication

    def make(user, subject, **fields):
        return MentorApplication.objects.create(
            user=user,
            subject=subject,
            bio="Scored a 5.",
            ap_experience="Took the exam in May.",
            teaching_experience="Peer tutor.",
            motivation="I know where people get stuck.",
            score_report=pdf(),
            cv=pdf(),
            **fields,
        )

    return make
