"""Browser-level latency measurement for the AC-27 release gate.

Measures "submission to usable visible" in Chromium: the time from navigation or
submit click until the expected result surface is visible. Run on the actual
mini-PC over the home LAN against an isolated benchmark copy.

Setup (one-off):
    pip install -r requirements-benchmark.txt
    python -m playwright install chromium

Usage:
    INTELLISTORE_BENCH_PASSWORD=... python scripts/browser_latency_benchmark.py \
        --base-url http://<mini-pc>:8017 --username <user> --runs 30 \
        --month 2026-08 --output ~/private/latency-browser.json
"""

import argparse
import json
import os
from pathlib import Path
import statistics
import sys
import time

def timed(page, action, ready_selector, url_glob=None):
    started = time.perf_counter()
    action()
    if url_glob:
        page.wait_for_url(url_glob, timeout=60_000)
    page.wait_for_selector(ready_selector, state="visible", timeout=60_000)
    return (time.perf_counter() - started) * 1000


def summarize(name, samples):
    ordered = sorted(samples)
    return {
        "journey": name,
        "cold_ms": round(samples[0], 1),
        "p50_ms": round(statistics.median(ordered[1:]), 1),
        "p95_ms": round(ordered[min(len(ordered) - 1, int(len(ordered) * 0.95))], 1),
        "max_ms": round(ordered[-1], 1),
        "samples": len(samples),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--username", required=True)
    parser.add_argument("--password-env", default="INTELLISTORE_BENCH_PASSWORD")
    parser.add_argument("--runs", type=int, default=30)
    parser.add_argument("--month", default="2026-08")
    parser.add_argument("--search", default="SYNTHETIC")
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()
    password = os.environ.get(args.password_env)
    if not password:
        parser.error(f"set {args.password_env}")
    if args.runs < 2:
        parser.error("--runs must be at least 2 (cold + warm)")
    base = args.base_url.rstrip("/")

    from playwright.sync_api import sync_playwright

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        page.goto(f"{base}/login/", wait_until="domcontentloaded")
        page.fill("#id_username", args.username)
        page.fill("#id_password", password)
        page.click("button[type=submit]")
        page.wait_for_selector('a[href="/uploads/"]', timeout=30_000)

        journeys = {
            "dashboard": (
                lambda: page.goto(base + "/", wait_until="domcontentloaded"),
                ".metric-grid",
            ),
            "period": (
                lambda: (
                    page.goto(base + "/", wait_until="domcontentloaded"),
                    page.fill("#id_period_month", args.month),
                    page.click('button:has-text("Show period")'),
                ),
                ".metric-grid",
                "**/?month=*",
            ),
            "search": (
                lambda: (
                    page.goto(base + "/search/", wait_until="domcontentloaded"),
                    page.fill("#search-query", args.search),
                    page.click('button:has-text("Search")'),
                ),
                "table.data-table tbody tr, .empty-state",
            ),
            "review": (
                lambda: page.goto(base + "/review/", wait_until="domcontentloaded"),
                "h1",
            ),
        }

        results = []
        for name, (action, ready, *rest) in journeys.items():
            url_glob = rest[0] if rest else None
            samples = [timed(page, action, ready, url_glob)]
            for _ in range(args.runs - 1):
                samples.append(timed(page, action, ready, url_glob))
            results.append(summarize(name, samples))
        browser.close()

    report = {
        "mode": "browser-submit-to-visible",
        "base_url": base,
        "runs": args.runs,
        "results": results,
        "p95_max_ms": max(item["p95_ms"] for item in results),
    }
    report["meets_two_seconds"] = report["p95_max_ms"] <= 2000
    text = json.dumps(report, indent=2)
    if args.output:
        args.output.write_text(text, encoding="utf-8")
    print(text)
    return 0 if report["meets_two_seconds"] else 2


if __name__ == "__main__":
    sys.exit(main())
