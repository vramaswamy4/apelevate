"""The study planner: context building, checks, the model client, the service, the pages."""

import json
from datetime import timedelta

import httpx
import pytest
from django.urls import reverse
from django.utils import timezone

from planner.checks import check_plan, errors, warnings
from planner.context import MAX_WEEKS, build_context, plan_window
from planner.llm import (
    Completion,
    FakeLLM,
    LLMError,
    LLMRateLimited,
    LLMSchemaError,
    OpenAICompatibleLLM,
)
from planner.models import StudyPlan
from planner.prompts import PLAN_SCHEMA, user_message
from planner.services import PlannerError, generate_plan


@pytest.fixture
def exam(chemistry):
    """An exam six weeks away, one chemistry class in week 2."""
    return timezone.localdate() + timedelta(weeks=6)


@pytest.fixture
def ctx(chemistry, exam, make_class):
    make_class(starts_in=timedelta(days=9), title="Week two class")
    weak = list(chemistry.units.filter(number=2))
    return build_context(chemistry, exam, 5, weak)


def good_plan(ctx):
    return FakeLLM().complete_json([], PLAN_SCHEMA, name="t", hint=ctx).data


# --- context --------------------------------------------------------------------------------


def test_window_is_capped_at_the_last_16_weeks_before_the_exam():
    today = timezone.localdate()
    start, weeks = plan_window(today + timedelta(weeks=33), today)
    assert weeks == MAX_WEEKS
    assert start == today + timedelta(weeks=33 - MAX_WEEKS)
    start, weeks = plan_window(today + timedelta(days=10), today)
    assert (start, weeks) == (today, 2)


def test_context_computes_weeks_and_class_weeks(ctx):
    assert ctx.weeks == 6
    assert ctx.weak_units == [2]
    [c] = ctx.classes
    assert c.week == 2
    assert set(c.topics) <= ctx.topic_codes
    assert "1.10" in ctx.topic_codes


def test_prompt_lists_only_real_codes_and_classes(ctx):
    text = user_message(ctx)
    assert "N = 6 week(s)" in text
    assert "1.10 Topic 1.10" in text
    assert f"#{ctx.classes[0].id} week 2" in text
    assert "Weak units (start these early): Unit 2" in text


def test_identical_inputs_have_identical_fingerprints(ctx, chemistry, exam):
    again = build_context(chemistry, exam, 5, list(chemistry.units.filter(number=2)))
    assert again.fingerprint("m") == ctx.fingerprint("m")
    assert ctx.fingerprint("m") != ctx.fingerprint("other-model")


# --- checks ---------------------------------------------------------------------------------


def test_the_fake_models_plan_passes(ctx):
    assert errors(check_plan(good_plan(ctx), ctx)) == []


@pytest.mark.parametrize(
    ("mutate", "code"),
    [
        (lambda p, c: p["weeks"][0]["topics"].append("9.99"), "unknown_topic"),
        (lambda p, c: p["weeks"][0]["classes"].append(424242), "unknown_class"),
        (lambda p, c: p["weeks"][0]["classes"].append(c.classes[0].id), "class_wrong_week"),
        (lambda p, c: p["weeks"][0].update(hours=40), "hours_over"),
        (lambda p, c: p["weeks"][0].update(hours=0), "hours_invalid"),
        (lambda p, c: p["weeks"].pop(), "week_numbering"),
    ],
)
def test_rule_breaks_are_errors(ctx, mutate, code):
    plan = good_plan(ctx)
    mutate(plan, ctx)
    assert code in {f.code for f in errors(check_plan(plan, ctx))}


def test_quality_problems_are_warnings(ctx):
    plan = good_plan(ctx)
    for week in plan["weeks"]:
        week["topics"] = [t for t in week["topics"] if not t.startswith("2.")]
        week["classes"] = []
    plan["weeks"][-1]["topics"].append("2.1")  # weak unit 2 only in the last week
    plan["weeks"][0]["tasks"] = []
    codes = {f.code for f in warnings(check_plan(plan, ctx))}
    assert {"weak_unit_late", "no_tasks"} <= codes
    plan["weeks"][-1]["topics"].remove("2.1")
    assert "unit_uncovered" in {f.code for f in warnings(check_plan(plan, ctx))}


# --- the OpenAI-compatible client, against a fake server --------------------------------------


def chat_server(content, status=200, usage=None):
    seen = []

    def handler(request):
        seen.append(request)
        if status != 200:
            return httpx.Response(status, json={"error": {"message": "nope"}})
        return httpx.Response(
            200,
            json={
                "model": "openai/gpt-oss-20b",
                "choices": [{"message": {"content": content}}],
                "usage": usage or {"prompt_tokens": 1200, "completion_tokens": 800},
            },
        )

    return handler, seen


def client(handler):
    return OpenAICompatibleLLM(
        "https://api.example/v1",
        "gsk_test",
        "openai/gpt-oss-20b",
        reasoning_effort="low",
        transport=httpx.MockTransport(handler),
    )


def test_client_requests_strict_structured_output(ctx):
    handler, seen = chat_server(json.dumps(good_plan(ctx)))
    result = client(handler).complete_json(
        [{"role": "user", "content": "hi"}], PLAN_SCHEMA, name="study_plan"
    )
    body = json.loads(seen[0].content)
    assert seen[0].url.path == "/v1/chat/completions"
    assert seen[0].headers["Authorization"] == "Bearer gsk_test"
    assert body["response_format"]["json_schema"]["strict"] is True
    assert body["response_format"]["json_schema"]["schema"] == PLAN_SCHEMA
    assert body["reasoning_effort"] == "low"
    assert body["max_completion_tokens"] == 4096
    assert (result.input_tokens, result.output_tokens) == (1200, 800)
    assert result.data["weeks"]


def test_provider_schema_rejection_is_a_schema_error():
    def handler(request):
        return httpx.Response(
            400,
            json={
                "error": {
                    "code": "json_validate_failed",
                    "message": "Generated JSON does not match the expected schema. "
                    "Error: jsonschema: '/weeks/5' additionalProperties "
                    "'final_week_advice' not allowed",
                }
            },
        )

    with pytest.raises(LLMSchemaError, match="final_week_advice"):
        client(handler).complete_json([], {}, name="x")


def test_a_schema_rejection_gets_the_corrective_retry(student, chemistry, exam):
    class SchemaThenGood(Scripted):
        def complete_json(self, messages, schema, *, name, hint=None, temperature=0.3):
            if not self.calls:
                self.calls.append(list(messages))
                raise LLMSchemaError("'final_week_advice' not allowed")
            return super().complete_json(messages, schema, name=name, hint=hint)

    llm = SchemaThenGood(good_plan)
    plan = generate(student, chemistry, exam, llm)
    assert plan.attempts == 2
    assert "final_week_advice" in llm.calls[1][-1]["content"]


def test_client_errors_are_typed():
    with pytest.raises(LLMRateLimited):
        client(chat_server("", status=429)[0]).complete_json([], {}, name="x")
    with pytest.raises(LLMError):
        client(chat_server("", status=500)[0]).complete_json([], {}, name="x")
    with pytest.raises(LLMError, match="valid JSON"):
        client(chat_server("not json")[0]).complete_json([], {}, name="x")


# --- the service ----------------------------------------------------------------------------


class Scripted:
    """Returns the given plans in order, recording what it was sent."""

    model = "scripted"

    def __init__(self, *plans):
        self.plans = list(plans)
        self.calls = []

    def complete_json(self, messages, schema, *, name, hint=None, temperature=0.3):
        self.calls.append(list(messages))
        plan = self.plans.pop(0)
        data = plan(hint) if callable(plan) else plan
        return Completion(data, json.dumps(data), self.model, 1000, 500, 900)


def with_invented_topic(ctx):
    plan = good_plan(ctx)
    plan["weeks"][0]["topics"].append("4.99")
    return plan


def generate(student, chemistry, exam, llm, weak=()):
    return generate_plan(student, chemistry, exam, 5, list(weak), llm=llm)


def test_generates_and_records_a_plan(student, chemistry, exam):
    plan = generate(student, chemistry, exam, Scripted(good_plan))
    assert plan.status == StudyPlan.Status.OK
    assert (plan.attempts, plan.input_tokens, plan.output_tokens) == (1, 1000, 500)
    assert plan.starts_on == timezone.localdate()


def test_a_rule_break_gets_one_corrective_retry(student, chemistry, exam):
    llm = Scripted(with_invented_topic, good_plan)
    plan = generate(student, chemistry, exam, llm)
    assert plan.attempts == 2
    assert plan.input_tokens == 2000  # both attempts are counted
    retry = llm.calls[1][-1]["content"]
    assert "4.99" in retry and "broke these rules" in retry


def test_a_plan_that_stays_wrong_is_rejected_not_shown(student, chemistry, exam):
    with pytest.raises(PlannerError, match="couldn't produce"):
        generate(student, chemistry, exam, Scripted(with_invented_topic, with_invented_topic))
    failed = StudyPlan.objects.get()
    assert failed.status == StudyPlan.Status.FAILED
    assert failed.plan is None


def test_identical_request_is_served_from_the_cache(student, chemistry, exam):
    first = generate(student, chemistry, exam, Scripted(good_plan))
    llm = Scripted()  # would fail if called
    assert generate(student, chemistry, exam, llm) == first
    assert llm.calls == []


def test_per_user_daily_limit(student, chemistry, exam, settings):
    settings.PLANNER_DAILY_LIMIT_PER_USER = 1
    generate(student, chemistry, exam, Scripted(good_plan))
    with pytest.raises(PlannerError, match="limit"):
        generate(student, chemistry, exam + timedelta(days=7), Scripted(good_plan))


def test_global_token_budget(student, make_user, chemistry, exam, settings):
    settings.PLANNER_DAILY_TOKEN_BUDGET = 1500
    generate(student, chemistry, exam, Scripted(good_plan))  # uses 1500
    with pytest.raises(PlannerError, match="budget"):
        generate(make_user(), chemistry, exam, Scripted(good_plan))


def test_provider_outage_is_a_friendly_error(student, chemistry, exam):
    class Down:
        model = "down"

        def complete_json(self, *a, **k):
            raise LLMRateLimited("429")

    with pytest.raises(PlannerError, match="unavailable"):
        generate(student, chemistry, exam, Down())
    assert StudyPlan.objects.get().status == StudyPlan.Status.FAILED


# --- pages ----------------------------------------------------------------------------------


def test_build_a_plan_through_the_page(client, student, chemistry, exam, make_class):
    make_class(starts_in=timedelta(days=9), title="Week two class")
    client.force_login(student)
    unit = chemistry.units.get(number=2)
    response = client.post(
        reverse("planner:new"),
        {
            "subject": chemistry.pk,
            "exam_date": exam.isoformat(),
            "hours_per_week": 5,
            "weak_units": [unit.pk],
        },
    )
    plan = StudyPlan.objects.get()
    assert response.status_code == 302
    assert response.url == reverse("planner:detail", args=[plan.pk])
    page = client.get(response.url).content.decode()
    assert "6-week plan" in page
    assert "Week two class" in page  # the recommended live class is linked
    assert "Checked by code" in page


def test_htmx_submit_redirects_with_a_header(client, student, chemistry, exam):
    client.force_login(student)
    response = client.post(
        reverse("planner:new"),
        {"subject": chemistry.pk, "exam_date": exam.isoformat(), "hours_per_week": 4},
        headers={"HX-Request": "true"},
    )
    assert response.status_code == 204
    assert response["HX-Redirect"].startswith("/plan/")


def test_past_exam_date_is_rejected(client, student, chemistry):
    client.force_login(student)
    response = client.post(
        reverse("planner:new"),
        {"subject": chemistry.pk, "exam_date": "2020-05-01", "hours_per_week": 4},
    )
    assert b"in the future" in response.content
    assert not StudyPlan.objects.exists()


def test_unit_picker_loads_the_subjects_units(client, student, chemistry):
    client.force_login(student)
    body = client.get(reverse("planner:unit_options"), {"subject": chemistry.pk}).content
    assert b"Unit 1:" in body and b"Unit 2:" in body


def test_plans_are_private(client, student, make_user, chemistry, exam):
    plan = generate(student, chemistry, exam, Scripted(good_plan))
    client.force_login(make_user())
    assert client.get(reverse("planner:detail", args=[plan.pk])).status_code == 404
