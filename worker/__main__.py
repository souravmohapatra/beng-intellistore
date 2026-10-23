"""Drain released work against the application, then exit.

Usage: python -m worker --base-url http://host:8000 --token <token> [--work-root DIR]
"""

import argparse
import json
import os
import sys
from pathlib import Path

from worker.client import LeaseLost, WorkerClient, process_available


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--token", default=os.environ.get("WORKER_TOKEN"))
    parser.add_argument("--work-root", type=Path, default=None)
    args = parser.parse_args(argv)

    if not args.token:
        parser.error("--token or WORKER_TOKEN is required")

    client = WorkerClient(args.base_url, args.token)
    processed = False
    try:
        for result in process_available(client, args.work_root):
            processed = True
            print(json.dumps(result))
    except LeaseLost as exc:
        print(f"lease lost; stopping: {exc}")
        return 3
    if not processed:
        print("no work")
    return 0


if __name__ == "__main__":
    sys.exit(main())
