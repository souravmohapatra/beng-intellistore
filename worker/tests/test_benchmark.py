"""Behavioral tests for the bounded advisory evaluation harness."""

from django.test import SimpleTestCase

from worker.benchmark import evaluate, meets_gates, meets_time_gate


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

    def test_quality_and_time_gates(self):
        passing_cases = [self.case("spending", "spending") for _ in range(50)]
        passing = evaluate(
            passing_cases, ScriptedClient(["spending"] * 50)
        )
        self.assertTrue(meets_gates(passing))
        self.assertTrue(meets_time_gate(passing))

        too_few = evaluate([self.case("spending", "spending")], ScriptedClient(["spending"]))
        self.assertFalse(meets_gates(too_few))
