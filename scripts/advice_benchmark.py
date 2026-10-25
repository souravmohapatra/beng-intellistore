"""Evaluate local advice candidates against privately labelled cases.

Usage:
    python scripts/advice_benchmark.py --cases /path/to/labels.json \
        [--url http://127.0.0.1:11435] [--model qwen2.5:7b-instruct] \
        [--output /path/to/report.json]

The labelled JSON is a list of objects with at least:
    description, amount_pence, label
Optional: account_kind ("current"|"card"|"savings"), rules_label.

Keep real cases, labels and reports outside this repository. The script prints
only aggregate statistics; per-case text is included in the report file you
choose, so treat that file as private.
"""

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from worker.advisory import LocalInferenceClient
from worker.benchmark import evaluate, meets_gates


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", required=True, type=Path)
    parser.add_argument("--url", default="http://127.0.0.1:11435")
    parser.add_argument("--model", default="qwen2.5:7b-instruct")
    parser.add_argument("--prompt-version", default="v1")
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    cases = json.loads(args.cases.read_text(encoding="utf-8"))
    if not isinstance(cases, list):
        parser.error("case file must contain a JSON list")

    client = LocalInferenceClient(
        args.url, model=args.model, timeout_seconds=args.timeout
    )
    report = evaluate(cases, client, prompt_version=args.prompt_version)
    payload = report.as_dict()
    payload["model"] = args.model
    payload["prompt_version"] = args.prompt_version
    payload["url"] = args.url
    payload["meets_gates"] = meets_gates(report)

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
                    "meets_gates",
                )
            },
            indent=2,
        )
    )
    return 0 if payload["meets_gates"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
