"""Drain released work once, or poll while the laptop is awake.

Usage: python -m worker --base-url http://host:8000 [--poll-interval SECONDS]
"""

import argparse
import json
import math
import os
import sys
import time
from pathlib import Path

from worker.advisory import client_from_env
from worker.client import LeaseLost, WorkerClient, process_available


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--token", default=os.environ.get("WORKER_TOKEN"))
    parser.add_argument("--work-root", type=Path, default=None)
    parser.add_argument(
        "--poll-interval", type=float, default=0,
        help="Seconds between drains; zero exits when idle (default).",
    )
    args = parser.parse_args(argv)

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


if __name__ == "__main__":
    sys.exit(main())
