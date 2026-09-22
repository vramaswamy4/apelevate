from datetime import timedelta

from django.urls import reverse
from django.utils import timezone

from classes.models import TutoringClass
from classes.services import enrol
from classes.stats import mentor_by_subject, mentor_monthly, mentor_summary


def run_class(make_class, students, minutes, days_ago):
    c = make_class(duration_minutes=minutes)
    for s in students:
        enrol(s, c)
    TutoringClass.objects.filter(pk=c.pk).update(
        starts_at=timezone.now() - timedelta(days=days_ago)
    )
    return c


def test_summary_is_derived_from_classes_and_enrolments(mentor, make_class, make_user, give_tokens):
    a, b = make_user(), make_user()
    give_tokens(a)
    give_tokens(b)
    run_class(make_class, [a, b], 60, days_ago=10)
    run_class(make_class, [a], 90, days_ago=3)
    make_class(duration_minutes=60)  # upcoming: counts as scheduled, not taught

    summary = mentor_summary(mentor.mentor_profile)
    assert summary.classes_taught == 2
    assert summary.hours_taught == 2.5
    assert summary.enrolments == 3
    assert summary.distinct_students == 2
    assert summary.tokens_earned == 3
    assert summary.upcoming_classes == 1


def test_monthly_hours_are_not_multiplied_by_enrolments(mentor, make_class, make_user, give_tokens):
    """Joining enrolments onto classes before SUM(duration) would count 60 min x 3 students."""
    students = [make_user() for _ in range(3)]
    for s in students:
        give_tokens(s)
    run_class(make_class, students, 60, days_ago=1)
    [row] = mentor_monthly(mentor.mentor_profile)
    assert row["hours"] == 1.0
    assert row["enrolments"] == 3
    assert row["students"] == 3


def test_by_subject(mentor, make_class, student, give_tokens):
    give_tokens(student)
    enrol(student, make_class())
    assert mentor_by_subject(mentor.mentor_profile) == [
        {"tutoring_class__subject__name": "AP Chemistry", "enrolments": 1, "students": 1}
    ]


def test_analytics_page_renders(client, mentor, make_class, student, give_tokens):
    give_tokens(student)
    run_class(make_class, [student], 45, days_ago=2)
    client.force_login(mentor)
    response = client.get(reverse("classes:analytics"))
    assert response.status_code == 200
    assert b"AP Chemistry" in response.content
