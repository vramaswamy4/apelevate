"""The eval harness: run the planner over fixed cases, score every plan, compare models.

Each case builds a real context (curriculum from seed_curriculum, synthetic classes at fixed
offsets) inside a transaction that's rolled back, then calls ``services.run_model`` - the same
code the page uses, retry included. Model responses are recorded as cassettes keyed on the
exact request, so results can be re-scored without calling the model again (or holding a key).
"""

import hashlib
import io
import json
import statistics
import time
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path

from django.conf import settings
from django.core.management import call_command
from django.db import transaction
from django.utils import timezone

from accounts.models import MentorProfile, User
from catalog.models import Subject, Subtopic
from classes.models import TutoringClass

from .checks import ERROR, WARNING, errors
from .context import build_context
from .llm import Completion, LLMRateLimited, LLMSchemaError
from .prompts import PROMPT_VERSION
from .services import run_model

ROOT = Path(settings.BASE_DIR) / "evals"
CASES = ROOT / "cases.json"
CASSETTES = ROOT / "cassettes"
RESULTS = ROOT / "results"
# Evals run "as of" a fixed moment with fixed class ids, so the prompt for a case is identical
# on every run and recorded responses replay.
EVAL_NOW = datetime(2026, 9, 1, 12, 0, tzinfo=UTC)


def load_cases(ids=None):
    cases = json.loads(CASES.read_text())
    return [c for c in cases if not ids or c["id"] in ids]


class RecordingLLM:
    """Wraps a model client; replays a recorded response for an identical request."""

    def __init__(self, llm, *, fresh=False, offline=False):
        self.llm = llm
        self.model = llm.model
        self.fresh = fresh
        self.offline = offline
        self.calls = 0

    def _path(self, messages, schema):
        key = json.dumps(
            {"model": self.model, "messages": messages, "schema": schema}, sort_keys=True
        )
        digest = hashlib.sha256(key.encode()).hexdigest()[:24]
        return CASSETTES / self.model.replace("/", "__") / f"{digest}.json"

    def complete_json(self, messages, schema, *, name, hint=None, temperature=0.3):
        path = self._path(messages, schema)
        if path.exists() and not self.fresh:
            recorded = json.loads(path.read_text())
            if "schema_error" in recorded:
                raise LLMSchemaError(recorded["schema_error"])
            return Completion(**recorded)
        if self.offline:
            raise LookupError(f"No recording for this request ({path.name}); run with a key.")
        for wait in (20, 40, 60, 60, 0):
            self.calls += 1
            try:
                completion = self.llm.complete_json(
                    messages, schema, name=name, hint=hint, temperature=temperature
                )
                break
            except LLMSchemaError as exc:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(json.dumps({"schema_error": exc.detail}, indent=1))
                raise
            except LLMRateLimited:
                # A provider quota, not a model failure: wait it out rather than score it.
                if not wait:
                    raise
                time.sleep(wait)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(asdict(completion), indent=1))
        return completion


@dataclass
class CaseResult:
    case: str
    model: str
    ok: bool  # a plan with no rule breaks came back (after at most one retry)
    first_attempt_ok: bool
    attempts: int
    errors: list = field(default_factory=list)
    warnings: list = field(default_factory=list)
    class_use: float | None = None  # share of available classes the plan recommends
    input_tokens: int = 0
    output_tokens: int = 0
    latency_ms: int = 0
    failure: str = ""


def _setup_case(case, index, now):
    subject = Subject.objects.get(slug=case["subject"])
    mentor_user = User.objects.create_user(f"eval-mentor-{case['id']}@example.com", None)
    mentor = MentorProfile.objects.create(user=mentor_user, bio="eval")
    mentor.subjects.add(subject)
    for i, spec in enumerate(case["classes"]):
        c = TutoringClass.objects.create(
            pk=9000 + index * 100 + i,
            mentor=mentor,
            subject=subject,
            title=f"Class {i + 1}: unit {spec['unit']}",
            starts_at=now + timedelta(days=spec["day"]),
            meeting_url="https://zoom.us/j/1",
        )
        c.subtopics.set(
            Subtopic.objects.filter(
                unit__subject=subject, unit__number=spec["unit"], number__in=spec["topics"]
            )
        )
    exam = timezone.localdate(now) + timedelta(weeks=case["weeks_to_exam"])
    weak = list(subject.units.filter(number__in=case["weak_units"]))
    return build_context(subject, exam, case["hours_per_week"], weak, now=now)


def run_case(case, index, llm, now) -> CaseResult:
    with transaction.atomic():
        ctx = _setup_case(case, index, now)
        transaction.set_rollback(True)
    try:
        run = run_model(ctx, llm)
    except Exception as exc:
        return CaseResult(case["id"], llm.model, False, False, 0, failure=str(exc))
    recommended = {cid for w in (run.plan or {}).get("weeks", []) for cid in w.get("classes", [])}
    return CaseResult(
        case=case["id"],
        model=run.model,
        ok=run.plan is not None,
        first_attempt_ok=not errors(run.first_attempt_findings),
        attempts=run.attempts,
        errors=[f.code for f in run.findings if f.severity == ERROR],
        warnings=[f.code for f in run.findings if f.severity == WARNING],
        class_use=(len(recommended) / len(ctx.classes)) if ctx.classes and run.plan else None,
        input_tokens=run.input_tokens,
        output_tokens=run.output_tokens,
        latency_ms=run.latency_ms,
    )


def run_suite(llm, cases, *, now=None, on_result=None):
    """Run every case. Curriculum is seeded once, inside a transaction that's rolled back."""
    now = now or EVAL_NOW
    all_ids = [c["id"] for c in json.loads(CASES.read_text())]
    results = []
    with transaction.atomic():
        call_command("seed_curriculum", verbosity=0, stdout=io.StringIO())
        for case in cases:
            result = run_case(case, all_ids.index(case["id"]), llm, now)
            results.append(result)
            if on_result:
                on_result(result)
        transaction.set_rollback(True)
    return results


def summarise(results) -> dict:
    n = len(results)
    ok = [r for r in results if r.ok]
    warn_counts: dict[str, int] = {}
    for r in ok:
        for w in r.warnings:
            warn_counts[w] = warn_counts.get(w, 0) + 1
    uses = [r.class_use for r in ok if r.class_use is not None]
    return {
        "model": results[0].model if results else "",
        "cases": n,
        "valid_plan_rate": len(ok) / n if n else 0,
        "first_attempt_rate": sum(r.first_attempt_ok for r in results) / n if n else 0,
        "clean_plan_rate": sum(r.ok and not r.warnings for r in results) / n if n else 0,
        "warnings_per_plan": (sum(len(r.warnings) for r in ok) / len(ok)) if ok else None,
        "warning_counts": dict(sorted(warn_counts.items())),
        "class_use": statistics.mean(uses) if uses else None,
        "median_latency_ms": statistics.median(r.latency_ms for r in ok) if ok else None,
        "mean_tokens": statistics.mean(r.input_tokens + r.output_tokens for r in ok)
        if ok
        else None,
        "failures": [r.case for r in results if not r.ok],
    }


def write_results(model, results):
    RESULTS.mkdir(parents=True, exist_ok=True)
    path = RESULTS / f"{model.replace('/', '__')}@{PROMPT_VERSION}.json"
    summary = {**summarise(results), "prompt": PROMPT_VERSION}
    path.write_text(
        json.dumps({"summary": summary, "cases": [asdict(r) for r in results]}, indent=1)
    )
    return path
