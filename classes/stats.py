"""Mentor statistics, computed from classes and enrolments.

The 2022 model stored hours taught, student count and revenue as counters on the mentor row, and
nothing ever updated them. Deriving them from the data means they can't drift.
"""

from dataclasses import dataclass

from django.db.models import Count, Sum
from django.db.models.functions import TruncMonth
from django.utils import timezone

from .models import Enrolment, TutoringClass


@dataclass(frozen=True)
class MentorSummary:
    classes_taught: int
    hours_taught: float
    upcoming_classes: int
    enrolments: int
    distinct_students: int
    tokens_earned: int


def mentor_summary(mentor, now=None) -> MentorSummary:
    now = now or timezone.now()
    classes = TutoringClass.objects.filter(mentor=mentor)
    taught = classes.past(now).aggregate(n=Count("id"), minutes=Sum("duration_minutes"))
    enrolments = Enrolment.objects.filter(tutoring_class__mentor=mentor).aggregate(
        n=Count("id"), students=Count("student", distinct=True), tokens=Sum("tokens_spent")
    )
    return MentorSummary(
        classes_taught=taught["n"],
        hours_taught=round((taught["minutes"] or 0) / 60, 1),
        upcoming_classes=classes.upcoming(now).count(),
        enrolments=enrolments["n"],
        distinct_students=enrolments["students"],
        tokens_earned=enrolments["tokens"] or 0,
    )


def mentor_monthly(mentor, now=None, tzinfo=None) -> list[dict]:
    """One row per month with classes taught, hours, enrolments and distinct students.

    Two grouped queries instead of one: joining enrolments onto classes would multiply each
    class's duration by its enrolment count before the SUM.
    """
    now = now or timezone.now()
    tzinfo = tzinfo or timezone.get_current_timezone()
    class_rows = (
        TutoringClass.objects.filter(mentor=mentor, starts_at__lt=now)
        .annotate(month=TruncMonth("starts_at", tzinfo=tzinfo))
        .values("month")
        .annotate(classes=Count("id"), minutes=Sum("duration_minutes"))
    )
    enrolment_rows = (
        Enrolment.objects.filter(tutoring_class__mentor=mentor, tutoring_class__starts_at__lt=now)
        .annotate(month=TruncMonth("tutoring_class__starts_at", tzinfo=tzinfo))
        .values("month")
        .annotate(enrolments=Count("id"), students=Count("student", distinct=True))
    )
    months: dict = {}
    for row in class_rows:
        months[row["month"]] = {
            "month": row["month"],
            "classes": row["classes"],
            "hours": round(row["minutes"] / 60, 1),
            "enrolments": 0,
            "students": 0,
        }
    for row in enrolment_rows:
        months[row["month"]].update(enrolments=row["enrolments"], students=row["students"])
    return sorted(months.values(), key=lambda r: r["month"], reverse=True)


def mentor_by_subject(mentor) -> list[dict]:
    return list(
        Enrolment.objects.filter(tutoring_class__mentor=mentor)
        .values("tutoring_class__subject__name")
        .annotate(enrolments=Count("id"), students=Count("student", distinct=True))
        .order_by("-enrolments")
    )
