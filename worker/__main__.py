"""Drain released work once, or poll while the laptop is awake.

Usage:
    python -m worker --base-url http://host:8000 [--poll-interval SECONDS]
    python -m worker --check-inference   # explicit connectivity check only
"""

import argparse
import json
import math
import os
import sys
import time
from pathlib import Path

from worker.advisory import AdvisoryClientError, client_from_env
from worker.client import LeaseLost, WorkerClient, process_available


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default=None)
    parser.add_argument("--token", default=os.environ.get("WORKER_TOKEN"))
    parser.add_argument("--work-root", type=Path, default=None)
    parser.add_argument(
        "--poll-interval",
        type=float,
        default=0,
        help="Seconds between drains; zero exits when idle (default).",
    )
    parser.add_argument(
        "--check-inference",
        action="store_true",
        help="Send one synthetic request to INFERENCE_URL and exit.",
    )
    args = parser.parse_args(argv)

    if args.check_inference:
        return _check_inference()

    if not args.base_url:
        parser.error("--base-url is required unless --check-inference is used")
    if not args.token:
        parser.error("--token or WORKER_TOKEN is required")
    if not math.isfinite(args.poll_interval) or args.poll_interval < 0:
        parser.error("--poll-interval must be finite and non-negative")

    client = WorkerClient(args.base_url, args.token)
    inference = client_from_env()
    while True:
        processed = False
        try:
            for result in process_available(client, args.work_root, inference):
                processed = True
                print(json.dumps(result), flush=True)
        except LeaseLost as exc:
            print(f"lease lost; stopping: {exc}", flush=True)
            return 3
        if not processed:
            print("no work", flush=True)
        if not args.poll_interval:
            return 0
        time.sleep(args.poll_interval)


def _check_inference() -> int:
    """Verify worker-container connectivity without enabling ordinary advice."""
    inference = client_from_env(force=True)
    if inference is None:
        print("INFERENCE_URL is not set", file=sys.stderr)
        return 2
    try:
        suggestion = inference.suggest_classification(
            description="SYNTHETIC COFFEE SHOP",
            amount_pence=-320,
            account_kind="current",
        )
    except AdvisoryClientError as exc:
        print(f"inference check failed: {type(exc).__name__}", file=sys.stderr)
        return 1
    print(
        json.dumps(
            {
                "classification": suggestion.classification.value,
                "confidence": suggestion.confidence,
                "model": suggestion.model,
                "prompt_version": suggestion.prompt_version,
            }
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
