"""Behavioral tests for the bounded advisory evaluation harness."""

import contextlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
from unittest import mock

from django.test import SimpleTestCase

from worker.benchmark import (
    WarmRun,
    evaluate,
    measure_warm,
    meets_quality_gate,
    meets_time_gate,
    qualify,
)


class FakeSuggestion:
    def __init__(self, classification):
        self.classification = type("C", (), {"value": classification})()


class ScriptedClient:
    def __init__(self, answers):
        self.answers = list(answers)
        self.calls = 0

    def suggest_classification(self, **kwargs):
        self.calls += 1
        answer = self.answers.pop(0)
        if isinstance(answer, Exception):
            raise answer
        return FakeSuggestion(answer)


class BenchmarkTests(SimpleTestCase):
    def case(self, label, answer, rules_label=None):
        entry = {
            "description": "synthetic",
            "amount_pence": -100,
            "account_kind": "current",
            "label": label,
        }
        if rules_label:
            entry["rules_label"] = rules_label
        return entry

    def passing_quality_report(self):
        cases = [self.case("spending", "spending") for _ in range(50)]
        return evaluate(cases, ScriptedClient(["spending"] * 50))

    def test_accuracy_counts_only_non_abstained_suggestions(self):
        cases = [
            self.case("spending", "spending"),
            self.case("spending", "unknown"),
            self.case("income", "income"),
            self.case("transfer", "spending"),
        ]
        report = evaluate(cases, ScriptedClient(["spending", "unknown", "income", "spending"]))

        self.assertEqual(report.total, 4)
        self.assertEqual(report.abstained, 1)
        self.assertEqual(report.answered, 3)
        self.assertEqual(report.correct, 2)
        self.assertAlmostEqual(report.accuracy, 2 / 3)
        self.assertAlmostEqual(report.coverage, 3 / 4)
        self.assertEqual(report.per_class["transfer"], {"total": 1, "answered": 1, "correct": 0})

    def test_errors_are_abstentions_and_reported_not_hidden(self):
        report = evaluate(
            [self.case("spending", RuntimeError("runtime down"))],
            ScriptedClient([RuntimeError("runtime down")]),
        )

        self.assertEqual(report.abstained, 1)
        self.assertEqual(report.errors, 1)
        self.assertEqual(report.answered, 0)
        self.assertIsNone(report.accuracy)
        self.assertEqual(report.cases[0].error, "RuntimeError")

    def test_rules_baseline_is_compared_when_supplied(self):
        cases = [
            self.case("spending", "spending", rules_label="spending"),
            self.case("transfer", "transfer", rules_label=None),
        ]
        report = evaluate(cases, ScriptedClient(["spending", "transfer"]))

        self.assertEqual(report.baseline_answered, 1)
        self.assertEqual(report.baseline_correct, 1)

    def test_invalid_label_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "not an allowed classification"):
            evaluate([self.case("loan", "loan")], ScriptedClient([]))

    def test_warm_workload_is_timed_without_labels(self):
        cases = [
            {"description": "TO SOMEONE", "amount_pence": -500, "account_kind": "current"}
            for _ in range(3)
        ]
        run = measure_warm(cases, ScriptedClient(["transfer", "unknown", RuntimeError("down")]))

        self.assertEqual(run.total, 3)
        self.assertEqual(run.errors, 1)
        self.assertEqual(run.completed, 2)
        self.assertEqual(len(run.durations_ms), 3)
        self.assertGreaterEqual(run.total_seconds, 0.0)

    def test_quality_gate_needs_the_approved_case_count_and_bars(self):
        self.assertTrue(meets_quality_gate(self.passing_quality_report()))
        too_few = evaluate(
            [self.case("spending", "spending")], ScriptedClient(["spending"])
        )
        self.assertFalse(meets_quality_gate(too_few))

    def test_time_gate_requires_100_completed_warm_items_inside_the_budget(self):
        too_few = WarmRun(total=50, durations_ms=[1000.0] * 50)
        self.assertFalse(meets_time_gate(too_few))

        inside_budget = WarmRun(total=100, durations_ms=[1000.0] * 100)
        self.assertTrue(meets_time_gate(inside_budget))

        over_budget = WarmRun(total=100, durations_ms=[7000.0] * 100)
        self.assertFalse(meets_time_gate(over_budget))

        # Errors are not throughput: a fast run that failed items cannot pass,
        # even when the raw item count reaches the minimum.
        errored = WarmRun(total=100, errors=100, durations_ms=[1.0] * 100)
        self.assertEqual(errored.completed, 0)
        self.assertFalse(meets_time_gate(errored))

        partly_errored = WarmRun(total=150, errors=60, durations_ms=[1000.0] * 150)
        self.assertEqual(partly_errored.completed, 90)
        self.assertFalse(meets_time_gate(partly_errored))

    def test_quality_pass_with_time_fail_keeps_the_combined_gate_false(self):
        report = self.passing_quality_report()
        slow_warm = WarmRun(total=100, durations_ms=[7000.0] * 100)

        result = qualify(report, slow_warm)

        self.assertTrue(result["meets_quality_gate"])
        self.assertFalse(result["meets_time_gate"])
        self.assertFalse(result["meets_gates"])

    def test_qualification_without_a_warm_run_does_not_pass_on_quality_alone(self):
        result = qualify(self.passing_quality_report(), None)

        self.assertTrue(result["meets_quality_gate"])
        self.assertFalse(result["meets_time_gate"])
        self.assertFalse(result["meets_gates"])


def _load_benchmark_script():
    path = Path(__file__).resolve().parents[2] / "scripts" / "advice_benchmark.py"
    spec = importlib.util.spec_from_file_location("advice_benchmark_cli", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class AdviceBenchmarkCommandTests(SimpleTestCase):
    """Exercise the operator command boundary and its exit status."""

    class PassingClient:
        def __init__(self, *args, **kwargs):
            pass

        def suggest_classification(
            self, *, description, amount_pence, account_kind, prompt_version="v1"
        ):
            return FakeSuggestion("spending")

    def _write(self, directory, name, payload):
        path = Path(directory) / name
        path.write_text(json.dumps(payload), encoding="utf-8")
        return path

    def _run(self, module, *args):
        with mock.patch.object(module, "LocalInferenceClient", self.PassingClient):
            with contextlib.redirect_stdout(io.StringIO()):
                return module.main(list(args))

    def test_exits_nonzero_when_only_the_quality_gate_is_run(self):
        module = _load_benchmark_script()
        with tempfile.TemporaryDirectory() as tmp:
            cases = self._write(
                tmp,
                "cases.json",
                [
                    {
                        "description": "synthetic",
                        "amount_pence": -100,
                        "account_kind": "current",
                        "label": "spending",
                    }
                    for _ in range(50)
                ],
            )
            code = self._run(module, "--cases", str(cases))

        self.assertEqual(code, 2)

    def test_explicit_prompt_version_is_preserved_in_the_report(self):
        module = _load_benchmark_script()

        with tempfile.TemporaryDirectory() as tmp:
            cases = self._write(
                tmp,
                "cases.json",
                [
                    {
                        "description": "synthetic",
                        "amount_pence": -100,
                        "account_kind": "current",
                        "label": "spending",
                    }
                    for _ in range(50)
                ],
            )
            report = Path(tmp) / "report.json"
            self._run(
                module,
                "--cases",
                str(cases),
                "--prompt-version",
                "v9",
                "--output",
                str(report),
            )
            payload = json.loads(report.read_text(encoding="utf-8"))

        self.assertEqual(payload["prompt_version"], "v9")

    def test_exits_nonzero_when_quality_passes_but_warm_timing_fails(self):
        module = _load_benchmark_script()

        with tempfile.TemporaryDirectory() as tmp:
            cases = self._write(
                tmp,
                "cases.json",
                [
                    {
                        "description": "synthetic",
                        "amount_pence": -100,
                        "account_kind": "current",
                        "label": "spending",
                    }
                    for _ in range(50)
                ],
            )
            warm = self._write(
                tmp,
                "warm.json",
                [
                    {
                        "description": "TO SOMEONE",
                        "amount_pence": -500,
                        "account_kind": "current",
                    }
                    for _ in range(100)
                ],
            )
            # Genuine gate path: quality passes from the real 50 cases while a
            # 100-item warm run over the ten-minute budget fails timing.
            slow_warm = WarmRun(total=100, durations_ms=[7000.0] * 100)
            with mock.patch.object(module, "measure_warm", return_value=slow_warm):
                code = self._run(
                    module, "--cases", str(cases), "--warm-cases", str(warm)
                )

        self.assertEqual(code, 2)

    def test_exits_nonzero_when_warm_workload_items_all_fail(self):
        module = _load_benchmark_script()

        with tempfile.TemporaryDirectory() as tmp:
            cases = self._write(
                tmp,
                "cases.json",
                [
                    {
                        "description": "synthetic",
                        "amount_pence": -100,
                        "account_kind": "current",
                        "label": "spending",
                    }
                    for _ in range(50)
                ],
            )
            # 100 malformed items: every call raises (KeyError), so none are
            # successfully processed even though the run is fast.
            warm = self._write(tmp, "warm.json", [{} for _ in range(100)])
            code = self._run(module, "--cases", str(cases), "--warm-cases", str(warm))

        self.assertEqual(code, 2)

    def test_exits_zero_when_quality_and_warm_gates_both_pass(self):
        module = _load_benchmark_script()
        with tempfile.TemporaryDirectory() as tmp:
            cases = self._write(
                tmp,
                "cases.json",
                [
                    {
                        "description": "synthetic",
                        "amount_pence": -100,
                        "account_kind": "current",
                        "label": "spending",
                    }
                    for _ in range(50)
                ],
            )
            warm = self._write(
                tmp,
                "warm.json",
                [
                    {
                        "description": "TO SOMEONE",
                        "amount_pence": -500,
                        "account_kind": "current",
                    }
                    for _ in range(100)
                ],
            )
            code = self._run(module, "--cases", str(cases), "--warm-cases", str(warm))

        self.assertEqual(code, 0)
