"""The prompt and the output schema. Kept together because they change together."""

from .context import PlanContext

PROMPT_VERSION = "v2"

PLAN_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["summary", "weeks", "final_week_advice"],
    "properties": {
        "summary": {"type": "string"},
        "weeks": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["week", "focus", "topics", "classes", "hours", "tasks"],
                "properties": {
                    "week": {"type": "integer"},
                    "focus": {"type": "string"},
                    "topics": {"type": "array", "items": {"type": "string"}},
                    "classes": {"type": "array", "items": {"type": "integer"}},
                    "hours": {"type": "number"},
                    "tasks": {"type": "array", "items": {"type": "string"}},
                },
            },
        },
        "final_week_advice": {"type": "string"},
    },
}

SYSTEM = """You are an experienced AP teacher writing a week-by-week study plan for one student.
Return only JSON matching the schema. Follow every rule:
1. Produce exactly one entry per week, numbered 1 to N in order, where N is given.
2. Use only topic codes from the list you are given, written exactly (for example "5.2").
3. Recommend only live classes from the list you are given, by id, and only in the week the
   list says each class happens. When you recommend a class, that week's topics must include
   at least one of the class's topics.
4. Never plan more hours in a week than the student has.
5. Every unit must appear in at least one week's topics list. If there are fewer weeks than
   units, cover several units in a week. Start the student's weak units in the first half of
   the plan and come back to them before the exam.
6. Keep the last week (or the last two, for plans longer than eight weeks) for mixed review and
   timed practice rather than new material. Review weeks still list the topic codes they
   review.
7. Tasks are concrete actions a student can do in one sitting ("Do 10 free-response questions
   on rate laws, then mark them against the scoring guide"), not vague advice.
8. "focus" is one short line. "summary" is two or three sentences on the overall approach."""


def user_message(ctx: PlanContext) -> str:
    lines = [
        f"Subject: {ctx.subject}",
        f"Exam date: {ctx.exam_date}. The plan has N = {ctx.weeks} week(s); "
        f"week 1 starts {ctx.start_date}.",
        f"Study time available: {ctx.hours_per_week} hours per week.",
    ]
    if ctx.weak_units:
        weak = ", ".join(
            f"Unit {u.number} ({u.name})" for u in ctx.units if u.number in ctx.weak_units
        )
        lines.append(f"Weak units (start these early): {weak}.")
    else:
        lines.append("Weak units: none given.")
    lines.append("")
    lines.append("Units and topics (use these codes only):")
    for unit in ctx.units:
        topics = "; ".join(f"{t.code} {t.name}" for t in unit.topics)
        lines.append(f"Unit {unit.number} {unit.name}: {topics}")
    lines.append("")
    if ctx.classes:
        lines.append("Live classes the student can join (id, week, title, topics):")
        for c in ctx.classes:
            lines.append(f"#{c.id} week {c.week}: {c.title} [{', '.join(c.topics)}]")
    else:
        lines.append(
            "Live classes: none scheduled before the exam. Leave every classes list empty."
        )
    return "\n".join(lines)


def correction_message(problems) -> str:
    listed = "\n".join(f"- {p.message}" for p in problems)
    return (
        "Your plan broke these rules:\n"
        f"{listed}\n"
        "Return the whole plan again as JSON with every problem fixed."
    )
