"""HTTP diagnostic for dashboard/period/search response time.

This measures server response completion, not the agreed "submission to usable
visible" browser journey. It is a diagnostic only: AC-27 requires browser-level
measurement on the mini-PC.

Usage:
    python scripts/latency_benchmark.py --base-url http://127.0.0.1:8029 \
        --username ... --password-env INTELLISTORE_BENCH_PASSWORD \
        [--runs 30] [--output report.json]

Reports cold first load separately plus p50/p95/max for warm repetitions. Do not
present its exit status as the release latency gate. Run it against an isolated
deployment and never seed live data.
"""

import argparse
import json
import os
from pathlib import Path
import statistics
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from http.cookiejar import CookieJar


class Session:
    def __init__(self, base_url):
        self.base_url = base_url.rstrip("/")
        self.jar = CookieJar()
        self.opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(self.jar)
        )

    def get(self, path):
        started = time.perf_counter()
        with self.opener.open(f"{self.base_url}{path}", timeout=60) as response:
            body = response.read()
            status = response.status
        return status, (time.perf_counter() - started) * 1000, body

    def login(self, username, password):
        status, _elapsed, body = self.get("/login/")
        if status != 200:
            raise SystemExit(f"login page returned {status}")
        token = _csrf_token(body)
        data = urllib.parse.urlencode(
            {"username": username, "password": password, "csrfmiddlewaretoken": token}
        ).encode()
        request = urllib.request.Request(
            f"{self.base_url}/login/",
            data=data,
            headers={"Referer": f"{self.base_url}/login/"},
        )
        with self.opener.open(request, timeout=60) as response:
            if response.status != 200:
                raise SystemExit(f"login returned {response.status}")
            if b"Statement Intelligence" not in response.read():
                raise SystemExit("login did not reach the application")
        # Confirm authentication with a second request.
        status, _elapsed, body = self.get("/")
        if b"Sign in" in body and b"Account overview" not in body:
            raise SystemExit("authentication failed")


def _csrf_token(body):
    marker = b'name="csrfmiddlewaretoken" value="'
    start = body.find(marker)
    if start < 0:
        raise SystemExit("no CSRF token on login page")
    start += len(marker)
    return body[start : body.find(b'"', start)].decode()


def measure(session, path, runs):
    cold = session.get(path)
    samples = [session.get(path)[1] for _ in range(runs)]
    ordered = sorted(samples)
    return {
        "path": path,
        "cold_ms": round(cold[1], 1),
        "p50_ms": round(statistics.median(ordered), 1),
        "p95_ms": round(ordered[min(len(ordered) - 1, int(len(ordered) * 0.95))], 1),
        "max_ms": round(ordered[-1], 1),
        "samples": len(samples),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--username", required=True)
    parser.add_argument(
        "--password-env",
        default="INTELLISTORE_BENCH_PASSWORD",
        help="Environment variable holding the password.",
    )
    parser.add_argument("--runs", type=int, default=30)
    parser.add_argument("--month", default="")
    parser.add_argument("--search", default="SYNTHETIC")
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()
    password = os.environ.get(args.password_env)
    if not password:
        parser.error(f"set {args.password_env}")
    if args.runs < 1:
        parser.error("--runs must be positive")

    session = Session(args.base_url)
    session.login(args.username, password)
    query = f"?month={args.month}" if args.month else ""
    paths = [
        f"/{query}",
        "/search/?q=" + urllib.parse.quote(args.search),
        "/accounts/",
        "/review/",
    ]
    report = {
        "mode": "http-diagnostic",
        "base_url": args.base_url,
        "runs": args.runs,
        "results": [measure(session, path, args.runs) for path in paths],
    }
    report["p95_max_ms"] = max(item["p95_ms"] for item in report["results"])
    report["diagnostic_under_two_seconds"] = report["p95_max_ms"] <= 2000
    text = json.dumps(report, indent=2)
    if args.output:
        args.output.write_text(text, encoding="utf-8")
    print(text)
    return 0 if report["diagnostic_under_two_seconds"] else 2


if __name__ == "__main__":
    sys.exit(main())
