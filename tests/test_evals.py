"""The eval harness itself: cases run through the production path, recordings replay."""

import io
import json

import pytest
from django.core.management import call_command

from planner import evals, report
from planner.evals import RecordingLLM, load_cases, run_suite, summarise
from planner.llm import FakeLLM


@pytest.fixture
def tmp_evals(tmp_path, monkeypatch):
    monkeypatch.setattr(evals, "CASSETTES", tmp_path / "cassettes")
    monkeypatch.setattr(evals, "RESULTS", tmp_path / "results")
    return tmp_path


def test_every_case_runs_and_the_baseline_passes(tmp_evals):
    results = run_suite(FakeLLM(), load_cases())
    summary = summarise(results)
    assert summary["cases"] == len(load_cases()) >= 20
    assert summary["valid_plan_rate"] == 1.0


def test_capped_case_gets_16_weeks(tmp_evals):
    [result] = run_suite(FakeLLM(), load_cases(["chem-long-capped"]))
    assert result.ok


def test_recordings_replay_without_calling_the_model(tmp_evals):
    live = RecordingLLM(FakeLLM())
    run_suite(live, load_cases(["chem-typical"]))
    assert live.calls == 1

    class Unreachable(FakeLLM):
        def complete_json(self, *a, **k):
            raise AssertionError("should have replayed")

    replay = RecordingLLM(Unreachable(), offline=True)
    [result] = run_suite(replay, load_cases(["chem-typical"]))
    assert result.ok and replay.calls == 0


def test_offline_without_a_recording_is_a_recorded_failure(tmp_evals):
    [result] = run_suite(RecordingLLM(FakeLLM(), offline=True), load_cases(["calc-mid"]))
    assert not result.ok and "No recording" in result.failure


def test_command_writes_results_and_report(tmp_evals, monkeypatch, settings):
    settings.BASE_DIR = tmp_evals
    (tmp_evals / "docs").mkdir()
    (tmp_evals / "evals").mkdir()
    (tmp_evals / "evals" / "decision.md").write_text("## Decision\n\nUse the fake.")
    monkeypatch.setattr(report, "CASES", evals.CASES)
    call_command(
        "run_evals",
        "--model",
        "fake",
        "--case",
        "chem-short",
        "--report",
        stdout=io.StringIO(),
    )
    data = json.loads((tmp_evals / "results" / "fake@v2.json").read_text())
    assert data["summary"]["cases"] == 1
    text = (tmp_evals / "docs" / "EVALS.md").read_text()
    assert "| `fake` | v2 | 100% |" in text and "Use the fake." in text
