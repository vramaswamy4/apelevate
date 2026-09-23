import time

from django.core.management.base import BaseCommand, CommandError

from planner.evals import RESULTS, RecordingLLM, load_cases, run_suite, summarise, write_results
from planner.llm import FakeLLM, get_llm
from planner.report import write_report


class Command(BaseCommand):
    help = (
        "Run the study-planner eval cases against one or more models and write "
        "evals/results/<model>.json. --report rebuilds docs/EVALS.md from every results file."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--model",
            action="append",
            default=[],
            help="Model id (repeatable). 'fake' uses the offline baseline.",
        )
        parser.add_argument("--case", action="append", default=[], help="Only these case ids.")
        parser.add_argument("--fresh", action="store_true", help="Ignore recorded responses.")
        parser.add_argument(
            "--offline", action="store_true", help="Replay recordings only; never call a model."
        )
        parser.add_argument(
            "--delay",
            type=float,
            default=0.0,
            help="Seconds to wait between live calls (free-tier rate limits).",
        )
        parser.add_argument("--report", action="store_true", help="Rewrite docs/EVALS.md.")

    def handle(self, *args, model, case, fresh, offline, delay, report, **options):
        cases = load_cases(case)
        if not cases:
            raise CommandError("No matching cases.")
        for name in model:
            if name == "fake":  # offline baseline: nothing to record
                recorder = FakeLLM()
                recorder.calls = 0
            else:
                recorder = RecordingLLM(get_llm(name), fresh=fresh, offline=offline)

            def on_result(r, recorder=recorder):
                mark = "PASS" if r.ok and not r.warnings else ("ok" if r.ok else "FAIL")
                detail = ", ".join(r.errors + r.warnings) or r.failure
                self.stdout.write(f"  {mark:4} {r.case:24} {r.attempts} try  {detail}")
                if delay and recorder.calls:
                    time.sleep(delay)

            self.stdout.write(f"{name}: {len(cases)} cases")
            results = run_suite(recorder, cases, on_result=on_result)
            path = write_results(name, results)
            s = summarise(results)
            self.stdout.write(
                f"  valid {s['valid_plan_rate']:.0%}  first-try {s['first_attempt_rate']:.0%}  "
                f"clean {s['clean_plan_rate']:.0%}  live calls {recorder.calls}  -> {path.name}"
            )
        if report:
            path = write_report(RESULTS)
            self.stdout.write(f"Report written to {path}")
