"""A small client for any OpenAI-compatible chat API (Groq, OpenRouter, Ollama, vLLM, ...).

Plain HTTP with httpx rather than a vendor SDK: the app isn't tied to one provider, switching
models is configuration, and the eval suite decides which model to use. ``FakeLLM`` implements
the same interface with no network, for development and tests.
"""

import json
import logging
import time
from dataclasses import dataclass

import httpx
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

log = logging.getLogger(__name__)


class LLMError(Exception):
    """The model couldn't be reached, refused, or returned something that isn't the schema."""


class LLMRateLimited(LLMError):
    pass


@dataclass(frozen=True)
class Completion:
    data: dict
    raw: str
    model: str
    input_tokens: int
    output_tokens: int
    latency_ms: int


class OpenAICompatibleLLM:
    def __init__(
        self, base_url, api_key, model, *, reasoning_effort=None, timeout=60.0, transport=None
    ):
        self.model = model
        self.reasoning_effort = reasoning_effort
        self._http = httpx.Client(
            base_url=base_url.rstrip("/"),
            timeout=timeout,
            transport=transport,
            headers={"Authorization": f"Bearer {api_key}"},
        )

    def complete_json(self, messages, schema, *, name, hint=None, temperature=0.3) -> Completion:
        body = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            # Constrained decoding: the provider guarantees the output parses against the schema.
            "response_format": {
                "type": "json_schema",
                "json_schema": {"name": name, "strict": True, "schema": schema},
            },
        }
        if self.reasoning_effort:
            body["reasoning_effort"] = self.reasoning_effort
        started = time.monotonic()
        try:
            response = self._http.post("/chat/completions", json=body)
        except httpx.HTTPError as exc:
            raise LLMError(f"Model API unreachable: {exc.__class__.__name__}") from exc
        latency_ms = int((time.monotonic() - started) * 1000)
        if response.status_code == 429:
            raise LLMRateLimited("The model provider's rate limit was hit.")
        if response.status_code != 200:
            log.warning("llm %s: %s", response.status_code, response.text[:500])
            raise LLMError(f"Model API returned {response.status_code}.")
        try:
            payload = response.json()
            raw = payload["choices"][0]["message"]["content"]
            data = json.loads(raw)
            usage = payload.get("usage") or {}
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise LLMError("The model's response wasn't valid JSON.") from exc
        return Completion(
            data=data,
            raw=raw,
            model=payload.get("model", self.model),
            input_tokens=int(usage.get("prompt_tokens", 0)),
            output_tokens=int(usage.get("completion_tokens", 0)),
            latency_ms=latency_ms,
        )


class FakeLLM:
    """Builds a sensible, rule-abiding plan straight from the context. No network, no key.

    Used by tests and by ``make dev`` so the whole feature runs offline. It is deliberately
    simple (units in order, weak units first), which also makes it a baseline for the evals.
    """

    model = "fake"

    def complete_json(self, messages, schema, *, name, hint=None, temperature=0.3) -> Completion:
        ctx = hint
        units = sorted(ctx.units, key=lambda u: (u.number not in ctx.weak_units, u.number))
        teaching_weeks = max(1, ctx.weeks - (1 if ctx.weeks > 1 else 0))
        weeks = [[] for _ in range(ctx.weeks)]
        for i, unit in enumerate(units):
            weeks[min(i * teaching_weeks // max(1, len(units)), teaching_weeks - 1)].append(unit)
        plan_weeks = []
        for n in range(1, ctx.weeks + 1):
            chosen = weeks[n - 1] if n <= teaching_weeks else []
            topics = [t.code for u in chosen for t in u.topics]
            if not chosen:  # review week
                topics = [ctx.units[0].topics[0].code] if ctx.units and ctx.units[0].topics else []
            classes = [c.id for c in ctx.classes if c.week == n and set(c.topics) & set(topics)]
            plan_weeks.append(
                {
                    "week": n,
                    "focus": ", ".join(f"Unit {u.number}" for u in chosen) or "Mixed review",
                    "topics": topics,
                    "classes": classes,
                    "hours": ctx.hours_per_week,
                    "tasks": ["Read the topic notes and do the practice questions for each topic."],
                }
            )
        data = {
            "summary": "Weak units first, then the rest in order, with the last week for review.",
            "weeks": plan_weeks,
            "final_week_advice": "Do one full timed practice exam and review every mistake.",
        }
        raw = json.dumps(data)
        return Completion(data, raw, self.model, len(str(messages)) // 4, len(raw) // 4, 0)


def get_llm(model=None):
    backend = settings.LLM_BACKEND
    if backend == "fake":
        return FakeLLM()
    if backend == "openai":
        if not settings.LLM_API_KEY:
            raise ImproperlyConfigured("LLM_BACKEND is 'openai' but LLM_API_KEY is empty.")
        return OpenAICompatibleLLM(
            settings.LLM_BASE_URL,
            settings.LLM_API_KEY,
            model or settings.LLM_MODEL,
            reasoning_effort=settings.LLM_REASONING_EFFORT or None,
        )
    raise ImproperlyConfigured(f"Unknown LLM_BACKEND {backend!r}")
