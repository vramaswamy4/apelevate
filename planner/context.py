"""The facts a plan is built from, computed by code before the model sees anything.

Everything that can be computed is computed here and handed to the model as data: how many
weeks there are, the date each week starts, which week each class falls in, and the only topic
codes and class ids that exist. The model's job is the judgement (what to study when, and
why), not arithmetic or recall, so there's less for it to get wrong and more for code to check.
"""

import hashlib
import json
import math
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timedelta

from django.db.models import Prefetch
from django.utils import timezone

from catalog.models import Subtopic, Unit
from classes.models import TutoringClass

# Plans cover the run-up to the exam: at most the last 16 weeks. A student planning in September
# for a May exam gets a plan that starts in January; before that, their classes are the plan.
MAX_WEEKS = 16
MAX_CLASSES = 20


@dataclass(frozen=True)
class TopicInfo:
    code: str
    name: str


@dataclass(frozen=True)
class UnitInfo:
    number: int
    name: str
    topics: list[TopicInfo]


@dataclass(frozen=True)
class ClassInfo:
    id: int
    week: int
    title: str
    starts: str  # ISO date, for display
    topics: list[str]  # topic codes


@dataclass(frozen=True)
class PlanContext:
    subject: str
    exam_date: str
    start_date: str
    weeks: int
    hours_per_week: int
    weak_units: list[int]
    units: list[UnitInfo]
    classes: list[ClassInfo] = field(default_factory=list)

    @property
    def topic_codes(self) -> set[str]:
        return {t.code for u in self.units for t in u.topics}

    @property
    def unit_of_topic(self) -> dict[str, int]:
        return {t.code: u.number for u in self.units for t in u.topics}

    def week_start(self, week: int) -> date:
        return date.fromisoformat(self.start_date) + timedelta(weeks=week - 1)

    def as_dict(self) -> dict:
        return asdict(self)

    def fingerprint(self, model: str) -> str:
        payload = json.dumps({"model": model, "context": self.as_dict()}, sort_keys=True)
        return hashlib.sha256(payload.encode()).hexdigest()


def plan_window(exam_date: date, today: date) -> tuple[date, int]:
    """(first day of week 1, number of weeks), ending at the exam."""
    weeks = max(1, min(MAX_WEEKS, math.ceil((exam_date - today).days / 7)))
    start = max(today, exam_date - timedelta(weeks=weeks))
    return start, weeks


def build_context(subject, exam_date: date, hours_per_week: int, weak_units, now=None):
    now = now or timezone.now()
    today = timezone.localdate(now)
    start, weeks = plan_window(exam_date, today)
    units = list(
        Unit.objects.filter(subject=subject)
        .order_by("number")
        .prefetch_related(Prefetch("subtopics", queryset=Subtopic.objects.select_related("unit")))
    )
    window_start = max(now, timezone.make_aware(datetime.combine(start, datetime.min.time())))
    exam_start = timezone.make_aware(datetime.combine(exam_date, datetime.min.time()))
    classes = (
        TutoringClass.objects.filter(
            subject=subject, starts_at__gte=window_start, starts_at__lt=exam_start
        )
        .prefetch_related(Prefetch("subtopics", queryset=Subtopic.objects.select_related("unit")))
        .order_by("starts_at")[:MAX_CLASSES]
    )
    class_infos = []
    for c in classes:
        week = (timezone.localdate(c.starts_at) - start).days // 7 + 1
        if 1 <= week <= weeks:
            class_infos.append(
                ClassInfo(
                    id=c.pk,
                    week=week,
                    title=c.title,
                    starts=timezone.localdate(c.starts_at).isoformat(),
                    topics=[t.code for t in c.subtopics.all()],
                )
            )
    return PlanContext(
        subject=subject.name,
        exam_date=exam_date.isoformat(),
        start_date=start.isoformat(),
        weeks=weeks,
        hours_per_week=hours_per_week,
        weak_units=sorted(u.number for u in weak_units),
        units=[
            UnitInfo(u.number, u.name, [TopicInfo(t.code, t.name) for t in u.subtopics.all()])
            for u in units
        ],
        classes=class_infos,
    )
