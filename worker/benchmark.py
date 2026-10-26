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
        self,
        *,
        description: str,
        amount_pence: int,
        account_kind: str,
        prompt_version: str | None = None,
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


@dataclass
class WarmRun:
    """Timing-only result for a warm unresolved-item workload.

    Warm items are timed separately from the labelled quality cases so a slow
    cold model load or an unrelated quality run can never be counted as warm
    throughput evidence.
    """

    total: int = 0
    errors: int = 0
    durations_ms: list[float] = field(default_factory=list)

    @property
    def completed(self) -> int:
        """Items the runtime actually processed (never negative)."""
        return max(0, self.total - self.errors)

    @property
    def total_seconds(self) -> float:
        return sum(self.durations_ms) / 1000.0

    def as_dict(self) -> dict[str, Any]:
        durations = sorted(self.durations_ms)
        return {
            "total": self.total,
            "completed": self.completed,
            "errors": self.errors,
            "median_ms": durations[len(durations) // 2] if durations else None,
            "p95_ms": durations[min(len(durations) - 1, int(len(durations) * 0.95))]
            if durations
            else None,
            "total_seconds": round(self.total_seconds, 2),
        }


def evaluate(
    cases: list[dict], client: SuggestingClient, prompt_version: str = "v1"
) -> BenchmarkReport:
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
                prompt_version=prompt_version,
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


def measure_warm(
    cases: list[dict], client: SuggestingClient, prompt_version: str = "v1"
) -> WarmRun:
    """Time a warm workload of unresolved items; no labels are required.

    Failures are counted, never hidden, but do not abort the run: the timing
    gate measures wall time for the whole workload, exactly as acceptance does.
    """
    run = WarmRun(total=len(cases))
    for case in cases:
        started = time.perf_counter()
        try:
            client.suggest_classification(
                description=str(case["description"]),
                amount_pence=int(case["amount_pence"]),
                account_kind=str(case.get("account_kind", "current")),
                prompt_version=prompt_version,
            )
        except Exception:  # bounded failure is counted, not hidden
            run.errors += 1
        run.durations_ms.append((time.perf_counter() - started) * 1000)
    return run


def meets_quality_gate(report: BenchmarkReport, minimum_cases: int = 50) -> bool:
    """Apply the approved quality/coverage bar, not a fit/resource claim."""
    return (
        report.total >= minimum_cases
        and report.accuracy is not None
        and report.accuracy >= 0.90
        and report.coverage is not None
        and report.coverage >= 0.50
    )


def meets_time_gate(
    run: WarmRun, minimum_items: int = 100, maximum_seconds: float = 600.0
) -> bool:
    """Warm workload gate: `minimum_items` completed items inside the budget.

    The approved target is 100 unresolved items within ten minutes of warm
    inference. A shorter, cold, or partly failing run can never satisfy it:
    items that raised are not throughput, so `errors` must be zero and the
    successfully processed `completed` count must reach the minimum.
    """
    return (
        run.errors == 0
        and run.completed >= minimum_items
        and run.total_seconds <= maximum_seconds
    )


def qualify(
    quality_report: BenchmarkReport,
    warm_run: WarmRun | None = None,
    *,
    minimum_cases: int = 50,
    warm_minimum_items: int = 100,
    warm_maximum_seconds: float = 600.0,
) -> dict[str, bool]:
    """Report the quality and timing gates separately, plus their conjunction.

    A missing warm workload means the timing gate has not been demonstrated, so
    the combined gate stays false rather than silently passing on quality alone.
    """
    quality = meets_quality_gate(quality_report, minimum_cases)
    timing = warm_run is not None and meets_time_gate(
        warm_run, warm_minimum_items, warm_maximum_seconds
    )
    return {
        "meets_quality_gate": quality,
        "meets_time_gate": timing,
        "meets_gates": quality and timing,
    }
