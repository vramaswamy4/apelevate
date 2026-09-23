"""Checks a generated plan against the facts it was built from.

Errors are rule breaks that make a plan wrong (an invented topic, a class in the wrong week,
more hours than the student has). They trigger one corrective retry and, if they persist, the
plan is rejected: nothing the model invents reaches a student. Warnings are quality problems
(a unit never covered, weak units left late). They're shown with the plan and scored by the
evals, but don't block it.
"""

from dataclasses import dataclass

from .context import PlanContext

ERROR, WARNING = "error", "warning"
HOURS_TOLERANCE = 0.5


@dataclass(frozen=True)
class Finding:
    code: str
    severity: str
    message: str

    def as_dict(self):
        return {"code": self.code, "severity": self.severity, "message": self.message}


def check_plan(plan: dict, ctx: PlanContext) -> list[Finding]:
    findings: list[Finding] = []
    weeks = plan.get("weeks") or []

    def error(code, message):
        findings.append(Finding(code, ERROR, message))

    def warning(code, message):
        findings.append(Finding(code, WARNING, message))

    numbers = [w.get("week") for w in weeks]
    if numbers != list(range(1, ctx.weeks + 1)):
        error(
            "week_numbering",
            f"The plan must have weeks 1 to {ctx.weeks} in order; it has {numbers}.",
        )

    valid_topics = ctx.topic_codes
    class_week = {c.id: c.week for c in ctx.classes}
    class_topics = {c.id: set(c.topics) for c in ctx.classes}

    for w in weeks:
        n = w.get("week")
        for code in w.get("topics", []):
            if code not in valid_topics:
                error("unknown_topic", f"Week {n} uses topic {code!r}, which doesn't exist.")
        for class_id in w.get("classes", []):
            if class_id not in class_week:
                error(
                    "unknown_class", f"Week {n} recommends class #{class_id}, which isn't listed."
                )
            elif class_week[class_id] != n:
                error(
                    "class_wrong_week",
                    f"Class #{class_id} happens in week {class_week[class_id]}, not week {n}.",
                )
            elif not class_topics[class_id] & set(w.get("topics", [])):
                warning(
                    "class_off_topic",
                    f"Week {n} recommends class #{class_id} but studies none of its topics.",
                )
        hours = w.get("hours", 0)
        if not isinstance(hours, int | float) or hours <= 0:
            error("hours_invalid", f"Week {n} has {hours!r} hours.")
        elif hours > ctx.hours_per_week + HOURS_TOLERANCE:
            error(
                "hours_over",
                f"Week {n} plans {hours} hours; the student has {ctx.hours_per_week}.",
            )
        if not w.get("tasks"):
            warning("no_tasks", f"Week {n} has no tasks.")

    # Coverage and ordering, judged on the topics that exist.
    unit_of = ctx.unit_of_topic
    first_week_of_unit: dict[int, int] = {}
    for w in weeks:
        for code in w.get("topics", []):
            if code in unit_of:
                first_week_of_unit.setdefault(unit_of[code], w.get("week"))
    for unit in ctx.units:
        if unit.number not in first_week_of_unit:
            warning("unit_uncovered", f"Unit {unit.number} ({unit.name}) is never studied.")
    half = max(1, (ctx.weeks + 1) // 2)
    for number in ctx.weak_units:
        first = first_week_of_unit.get(number)
        if first is not None and first > half:
            warning(
                "weak_unit_late",
                f"Weak unit {number} starts in week {first}, after the first half (week {half}).",
            )
    return findings


def errors(findings):
    return [f for f in findings if f.severity == ERROR]


def warnings(findings):
    return [f for f in findings if f.severity == WARNING]
