"""Bounded local-advice evaluation harness.

Runs labelled ambiguous cases against a configured inference client. Labels are
supplied by the operator from outside Git; this module neither invents expected
values nor hides abstentions. It reports quality, coverage, per-class failures
and timings so a candidate can be accepted or rejected explicitly.
"""

from dataclasses import dataclass, field
import time
from typing import Any, Protocol


class SuggestingClient(Protocol):
    def suggest_classification(
        self, *, description: str, amount_pence: int, account_kind: str
    ) -> Any: ...


@dataclass
class CaseOutcome:
    description: str
    label: str
    suggestion: str | None
    correct: bool | None
    milliseconds: float
    error: str | None = None


@dataclass
class BenchmarkReport:
    total: int = 0
    answered: int = 0
    correct: int = 0
    abstained: int = 0
    errors: int = 0
    accuracy: float | None = None
    coverage: float | None = None
    per_class: dict[str, dict[str, int]] = field(default_factory=dict)
    durations_ms: list[float] = field(default_factory=list)
    baseline_correct: int = 0
    baseline_answered: int = 0
    cases: list[CaseOutcome] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        durations = sorted(self.durations_ms)
        return {
            "total": self.total,
            "answered": self.answered,
            "correct": self.correct,
            "abstained": self.abstained,
            "errors": self.errors,
            "accuracy_non_abstained": self.accuracy,
            "coverage": self.coverage,
            "per_class": self.per_class,
            "baseline_answered": self.baseline_answered,
            "baseline_correct": self.baseline_correct,
            "median_ms": durations[len(durations) // 2] if durations else None,
            "p95_ms": durations[min(len(durations) - 1, int(len(durations) * 0.95))]
            if durations
            else None,
            "total_seconds": round(sum(durations) / 1000, 2),
            "cases": [
                {
                    "description": case.description,
                    "label": case.label,
                    "suggestion": case.suggestion,
                    "correct": case.correct,
                    "milliseconds": round(case.milliseconds, 1),
                    "error": case.error,
                }
                for case in self.cases
            ],
        }


def evaluate(cases: list[dict], client: SuggestingClient) -> BenchmarkReport:
    """Evaluate labelled cases; 'unknown' and errors count as abstentions."""
    report = BenchmarkReport(total=len(cases))
    allowed = {"spending", "income", "transfer", "refund", "unknown"}
    for case in cases:
        label = str(case.get("label", "")).strip().lower()
        if label not in allowed:
            raise ValueError(f"Case label is not an allowed classification: {label!r}")
        baseline = case.get("rules_label")
        if baseline in {"spending", "income", "transfer", "refund"}:
            report.baseline_answered += 1
            if baseline == label:
                report.baseline_correct += 1

        started = time.perf_counter()
        error = None
        suggested = None
        try:
            suggestion = client.suggest_classification(
                description=str(case["description"]),
                amount_pence=int(case["amount_pence"]),
                account_kind=str(case.get("account_kind", "current")),
            )
            suggested = str(suggestion.classification.value)
        except Exception as exc:  # bounded failure is reported, not hidden
            error = type(exc).__name__
        elapsed = (time.perf_counter() - started) * 1000
        report.durations_ms.append(elapsed)

        outcomes = report.per_class.setdefault(
            label, {"total": 0, "answered": 0, "correct": 0}
        )
        outcomes["total"] += 1
        if suggested is None or suggested == "unknown":
            report.abstained += 1
            if error:
                report.errors += 1
            report.cases.append(
                CaseOutcome(
                    str(case["description"]),
                    label,
                    suggested,
                    None,
                    elapsed,
                    error,
                )
            )
            continue
        report.answered += 1
        outcomes["answered"] += 1
        correct = suggested == label
        if correct:
            report.correct += 1
            outcomes["correct"] += 1
        report.cases.append(
            CaseOutcome(str(case["description"]), label, suggested, correct, elapsed)
        )

    if report.answered:
        report.accuracy = report.correct / report.answered
    if report.total:
        report.coverage = report.answered / report.total
    return report


def meets_gates(report: BenchmarkReport, minimum_cases: int = 50) -> bool:
    """Apply the approved quality/coverage bar, not a fit/resource claim."""
    return (
        report.total >= minimum_cases
        and report.accuracy is not None
        and report.accuracy >= 0.90
        and report.coverage is not None
        and report.coverage >= 0.50
    )


def meets_time_gate(report: BenchmarkReport, maximum_seconds: float = 600.0) -> bool:
    """Warm workload gate: the measured run must finish inside the budget."""
    return report.total > 0 and sum(report.durations_ms) / 1000 <= maximum_seconds
