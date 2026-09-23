"""Generating a study plan: limits, cache, model call, validation, one corrective retry."""

import logging
from dataclasses import dataclass
from datetime import date, timedelta

from django.conf import settings
from django.db.models import Sum
from django.db.models.functions import Coalesce
from django.utils import timezone

from .checks import ERROR, Finding, check_plan, errors
from .context import build_context
from .llm import LLMError, LLMSchemaError, get_llm
from .models import StudyPlan
from .prompts import PLAN_SCHEMA, SYSTEM, correction_message, user_message

log = logging.getLogger(__name__)

MAX_ATTEMPTS = 2


class PlannerError(Exception):
    """Safe to show to the user."""


@dataclass
class ModelRun:
    """The outcome of asking the model for a plan, with one corrective retry."""

    plan: dict | None
    findings: list
    first_attempt_findings: list
    attempts: int = 0
    model: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    latency_ms: int = 0


def run_model(ctx, llm) -> ModelRun:
    """Ask for a plan, check it, and give the model one chance to fix rule breaks.

    Used by the page and by the eval suite, so the evals measure exactly what users get.
    Raises LLMError if the provider fails.
    """
    messages = [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": user_message(ctx)},
    ]
    run = ModelRun(plan=None, findings=[], first_attempt_findings=[], model=llm.model)
    for attempt in range(1, MAX_ATTEMPTS + 1):
        run.attempts = attempt
        try:
            completion = llm.complete_json(messages, PLAN_SCHEMA, name="study_plan", hint=ctx)
        except LLMSchemaError as exc:
            # The output wasn't even the right shape. Count it, tell the model, try once more.
            run.findings = [Finding("schema_invalid", ERROR, str(exc))]
            if attempt == 1:
                run.first_attempt_findings = run.findings
            messages = [*messages, {"role": "user", "content": correction_message(run.findings)}]
            continue
        run.model = completion.model
        run.input_tokens += completion.input_tokens
        run.output_tokens += completion.output_tokens
        run.latency_ms += completion.latency_ms
        run.findings = check_plan(completion.data, ctx)
        if attempt == 1:
            run.first_attempt_findings = run.findings
        if not errors(run.findings):
            run.plan = completion.data
            break
        log.info("plan attempt %s broke %s rules", attempt, len(errors(run.findings)))
        messages += [
            {"role": "assistant", "content": completion.raw},
            {"role": "user", "content": correction_message(errors(run.findings))},
        ]
    return run


def _today_start(now):
    return now - timedelta(days=1)


def check_limits(user, now):
    since = _today_start(now)
    mine = StudyPlan.objects.filter(user=user, created_at__gte=since).count()
    if mine >= settings.PLANNER_DAILY_LIMIT_PER_USER:
        raise PlannerError(
            f"You've made {mine} plans in the last 24 hours, which is the limit. "
            "Try again tomorrow."
        )
    used = StudyPlan.objects.filter(created_at__gte=since).aggregate(
        t=Coalesce(Sum("input_tokens"), 0) + Coalesce(Sum("output_tokens"), 0)
    )["t"]
    if used >= settings.PLANNER_DAILY_TOKEN_BUDGET:
        raise PlannerError("The planner has used today's budget. Try again tomorrow.")


def generate_plan(user, subject, exam_date, hours_per_week, weak_units, *, llm=None, now=None):
    """Return a StudyPlan (status OK), reusing an identical recent one when there is one."""
    now = now or timezone.now()
    llm = llm or get_llm()
    ctx = build_context(subject, exam_date, hours_per_week, weak_units, now=now)
    fingerprint = ctx.fingerprint(llm.model)

    cached = (
        StudyPlan.objects.filter(
            user=user,
            input_hash=fingerprint,
            status=StudyPlan.Status.OK,
            created_at__gte=_today_start(now),
        )
        .order_by("-created_at")
        .first()
    )
    if cached:
        return cached

    check_limits(user, now)
    record = StudyPlan(
        user=user,
        subject=subject,
        exam_date=exam_date,
        starts_on=date.fromisoformat(ctx.start_date),
        hours_per_week=hours_per_week,
        input_hash=fingerprint,
        model=llm.model,
        attempts=0,
    )
    try:
        run = run_model(ctx, llm)
    except LLMError as exc:
        record.status = StudyPlan.Status.FAILED
        record.problems = [{"code": "llm_error", "severity": "error", "message": str(exc)}]
        record.save()
        raise PlannerError("The planner is unavailable right now. Try again in a minute.") from exc

    record.plan = run.plan
    record.model = run.model
    record.attempts = run.attempts
    record.input_tokens = run.input_tokens
    record.output_tokens = run.output_tokens
    record.latency_ms = run.latency_ms
    findings = run.findings
    record.problems = [f.as_dict() for f in findings]
    record.status = StudyPlan.Status.OK if record.plan else StudyPlan.Status.FAILED
    record.save()
    record.weak_units.set(weak_units)
    if record.status == StudyPlan.Status.FAILED:
        raise PlannerError(
            "The planner couldn't produce a plan that follows the rules. Try again, or change "
            "the dates or weak units."
        )
    log.info(
        "plan %s: %s, %s attempt(s), %s tokens, %sms",
        record.pk,
        record.model,
        record.attempts,
        record.total_tokens,
        record.latency_ms,
    )
    return record
