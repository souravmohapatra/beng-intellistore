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
import math
import os
import json
from pathlib import Path
import statistics
import sys
import time

def timed(page, action, ready_selector):
    started = time.perf_counter()
    action()
    page.wait_for_selector(ready_selector, state="visible", timeout=60_000)
    # Include rendering, not merely the arrival of an HTML response.
    page.evaluate(
        "() => new Promise(resolve => requestAnimationFrame("
        "() => requestAnimationFrame(resolve)))"
    )
    return (time.perf_counter() - started) * 1000


def summarize(name, cold_ms, warm_samples):
    ordered = sorted(warm_samples)
    return {
        "journey": name,
        "first_load_ms": cold_ms,
        "p50_ms": statistics.median(ordered),
        "p95_ms": ordered[math.ceil(len(ordered) * 0.95) - 1],
        "max_ms": ordered[-1],
        "warm_samples": len(warm_samples),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--username", required=True)
    parser.add_argument("--password-env", default="INTELLISTORE_BENCH_PASSWORD")
    parser.add_argument("--runs", type=int, default=30, help="Warm runs per journey")
    parser.add_argument("--month", default="2026-08")
    parser.add_argument("--search", default="SYNTHETIC")
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--host-description", default="not supplied")
    parser.add_argument("--network-description", default="not supplied")
    args = parser.parse_args()
    password = os.environ.get(args.password_env)
    if not password:
        parser.error(f"set {args.password_env}")
    if args.runs < 1:
        parser.error("--runs must be positive")
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
                lambda: None,
                lambda: page.goto(base + "/", wait_until="domcontentloaded"),
                ".metric-grid",
            ),
            "period": (
                lambda: (
                    page.goto(base + "/", wait_until="domcontentloaded"),
                    page.fill("#id_period_month", args.month),
                ),
                lambda: page.get_by_role("button", name="Show period").click(),
                ".metric-grid",
            ),
            "search": (
                lambda: (
                    page.goto(base + "/search/", wait_until="domcontentloaded"),
                    page.fill("#search-query", args.search),
                ),
                lambda: page.get_by_role("button", name="Search", exact=True).click(),
                "table.data-table tbody tr, .empty-state",
            ),
        }

        results = []
        for name, (prepare, action, ready) in journeys.items():
            prepare()
            first_load_ms = timed(page, action, ready)
            samples = []
            for _ in range(args.runs):
                prepare()
                samples.append(timed(page, action, ready))
            results.append(summarize(name, first_load_ms, samples))
        browser_version = browser.version
        browser.close()

    report = {
        "mode": "browser-submit-to-visible",
        "base_url": base,
        "warm_runs_per_journey": args.runs,
        "browser": f"Chromium {browser_version}",
        "viewport": {"width": 1440, "height": 1000},
        "month": args.month,
        "query": args.search,
        "host_description": args.host_description,
        "network_description": args.network_description,
        "cold_policy": "First measured journey only; no server/cache restart.",
        "results": results,
        "p95_max_ms": max(item["p95_ms"] for item in results),
    }
    report["meets_two_seconds"] = report["p95_max_ms"] <= 2000
    report["qualifying_sample_count"] = args.runs >= 30
    text = json.dumps(report, indent=2)
    if args.output:
        args.output.write_text(text, encoding="utf-8")
    print(text)
    return 0 if (
        report["meets_two_seconds"] and report["qualifying_sample_count"]
    ) else 2


if __name__ == "__main__":
    sys.exit(main())
