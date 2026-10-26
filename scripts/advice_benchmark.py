"""Evaluate local advice candidates against privately labelled cases.

Usage:
    python scripts/advice_benchmark.py --cases /path/to/labels.json \
        [--warm-cases /path/to/unresolved.json] \
        [--url http://127.0.0.1:11435] [--model qwen2.5:7b-instruct] \
        [--output /path/to/report.json]

The labelled JSON is a list of objects with at least:
    description, amount_pence, label
Optional: account_kind ("current"|"card"|"savings"), rules_label.

The optional warm workload is a separate list of at least 100 unresolved items
(description, amount_pence, account_kind). It is timed on its own so a cold
model load or the labelled quality run can never be counted as warm throughput.
The command exits non-zero until both the quality and warm-timing gates pass.

Keep real cases, labels and reports outside this repository. The script prints
only aggregate statistics; per-case text is included in the report file you
choose, so treat that file as private.
"""

import argparse
import json
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from worker.advisory import LocalInferenceClient
from worker.benchmark import evaluate, measure_warm, qualify


def _load_cases(path: Path, what: str) -> list[dict]:
    cases = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(cases, list):
        raise SystemExit(f"{what} file must contain a JSON list")
    return cases


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", required=True, type=Path)
    parser.add_argument(
        "--warm-cases",
        type=Path,
        default=None,
        help="Separate unresolved-item workload (>=100 items) for the timing gate.",
    )
    parser.add_argument("--url", default="http://127.0.0.1:11435")
    parser.add_argument("--model", default="qwen2.5:7b-instruct")
    parser.add_argument(
        "--prompt-version",
        default=os.environ.get("INFERENCE_PROMPT_VERSION", "").strip() or "v1",
        help="Defaults to INFERENCE_PROMPT_VERSION so the benchmark matches production.",
    )
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args(argv)

    cases = _load_cases(args.cases, "case")

    client = LocalInferenceClient(
        args.url,
        model=args.model,
        timeout_seconds=args.timeout,
        prompt_version=args.prompt_version,
    )
    report = evaluate(cases, client, prompt_version=args.prompt_version)

    warm_run = None
    if args.warm_cases is not None:
        warm_cases = _load_cases(args.warm_cases, "warm case")
        warm_run = measure_warm(warm_cases, client, prompt_version=args.prompt_version)

    payload = report.as_dict()
    payload["model"] = args.model
    payload["prompt_version"] = args.prompt_version
    payload["url"] = args.url
    payload["warm"] = warm_run.as_dict() if warm_run is not None else None
    payload.update(qualify(report, warm_run))

    if args.output:
        args.output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print(f"report written to {args.output}")
    print(
        json.dumps(
            {
                key: payload[key]
                for key in (
                    "total",
                    "answered",
                    "correct",
                    "abstained",
                    "errors",
                    "accuracy_non_abstained",
                    "coverage",
                    "median_ms",
                    "p95_ms",
                    "baseline_answered",
                    "baseline_correct",
                    "warm",
                    "meets_quality_gate",
                    "meets_time_gate",
                    "meets_gates",
                )
            },
            indent=2,
        )
    )
    return 0 if payload["meets_gates"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
