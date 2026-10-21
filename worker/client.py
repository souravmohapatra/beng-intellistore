"""Laptop worker: claim assigned work through the application API and report.

The worker never touches PostgreSQL or shared mounts; it downloads only the
source it was assigned, writes it to a temporary directory, and removes that
directory on completion.
"""

import json
import shutil
import tempfile
import urllib.error
import urllib.request
from pathlib import Path


class WorkerError(Exception):
    """The application rejected or failed a worker request."""


class WorkerClient:
    def __init__(self, base_url: str, token: str, timeout: float = 30.0):
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.timeout = timeout

    def _request(self, method: str, path: str, payload=None, raw: bool = False):
        data = None if payload is None else json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            f"{self.base_url}{path}",
            data=data,
            method=method,
            headers={
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                body = response.read()
                if response.status == 204:
                    return None
                return body if raw else json.loads(body)
        except urllib.error.HTTPError as exc:
            detail = exc.read()[:200].decode("utf-8", "replace")
            raise WorkerError(f"{method} {path} failed: {exc.code} {detail}") from exc

    def claim(self):
        return self._request("POST", "/api/worker/claims/")

    def download_source(self, job_id: int) -> bytes:
        return self._request("GET", f"/api/worker/jobs/{job_id}/source/", raw=True)

    def progress(self, job_id: int, stage: str, message: str = ""):
        return self._request(
            "POST",
            f"/api/worker/jobs/{job_id}/progress/",
            {"stage": stage, "message": message},
        )

    def submit_result(self, job_id: int, payload: dict):
        return self._request(
            "POST", f"/api/worker/jobs/{job_id}/result/", payload
        )


def interpret(data: bytes, content_type: str):
    """Interpret an assigned source; None means no supported layout matched."""
    if content_type != "application/pdf":
        return None
    import io

    import pypdf

    from interpretation import amex, lloyds_credit, lloyds_current, revolut

    reader = pypdf.PdfReader(io.BytesIO(data))
    if reader.is_encrypted:
        return None

    token_pages = [_page_tokens(page) for page in reader.pages]
    for positioned_parser in (amex.parse_pages, revolut.parse_pages):
        positioned = positioned_parser(token_pages)
        if positioned.recognised:
            return positioned

    text = "\f".join((page.extract_text() or "") for page in reader.pages)
    for parser in (lloyds_current.parse, lloyds_credit.parse):
        result = parser(text)
        if result.recognised:
            return result
    return None


def _page_tokens(page) -> list[tuple[float, float, str]]:
    tokens: list[tuple[float, float, str]] = []

    def visitor(text, cm, tm, font_dict, font_size):
        cleaned = (text or "").strip()
        if cleaned:
            tokens.append((round(tm[4], 1), round(tm[5], 1), cleaned))

    page.extract_text(visitor_text=visitor)
    return tokens


def build_result(claim: dict, parsed) -> dict:
    if parsed is None:
        return {
            "version": claim["result_version"],
            "attempt": claim["attempt"],
            "outcome": "unsupported",
            "issues": [
                {
                    "code": "unsupported_layout",
                    "message": "No supported statement layout is implemented for this file.",
                }
            ],
            "sections": [],
        }

    reconciled = bool(parsed.reconciled)
    section = {
        "name": parsed.section_name,
        "account_role": "primary",
        "status": "ok" if reconciled else "failed",
        "account_kind_hint": parsed.account_kind_hint,
        "issues": [
            {"code": issue.code, "message": issue.message} for issue in parsed.issues
        ],
        "transactions": [
            {
                "posted_on": row.posted_on.isoformat(),
                "source_transaction_date": getattr(row, "transaction_date", None)
                and row.transaction_date.isoformat(),
                "description": row.description,
                "transaction_type": row.transaction_type,
                "amount_pence": row.amount_pence,
                "balance_pence": getattr(row, "balance_pence", None),
                "page": row.page,
                "row": row.row,
                "source_text": row.source_text,
            }
            for row in (parsed.rows if reconciled else [])
        ],
        "balances": [
            {
                "kind": balance.kind,
                "observed_on": balance.observed_on.isoformat()
                if balance.observed_on is not None
                else None,
                "amount_pence": balance.amount_pence,
            }
            for balance in parsed.balances
        ],
        "stated_totals": {
            "money_in_pence": getattr(parsed, "money_in_pence", None),
            "money_out_pence": getattr(parsed, "money_out_pence", None),
            "payments_received_pence": getattr(parsed, "payments_received_pence", None),
            "payments_and_credits_pence": getattr(parsed, "payments_and_credits_pence", None),
        },
    }
    savings_section = None
    savings = getattr(parsed, "savings", None)
    if savings is not None and savings.recognised:
        savings_ok = not savings.issues
        savings_section = {
            "name": "revolut_savings_gbp",
            "account_role": "savings",
            "status": "ok" if savings_ok else "failed",
            "issues": [
                {"code": issue.code, "message": issue.message}
                for issue in [*savings.issues, *savings.review_notes]
            ],
            "transactions": [
                {
                    "posted_on": row.posted_on.isoformat(),
                    "source_transaction_date": None,
                    "description": row.description,
                    "transaction_type": row.transaction_type,
                    "amount_pence": row.amount_pence,
                    "balance_pence": row.balance_pence,
                    "page": row.page,
                    "row": row.row,
                    "source_text": row.source_text,
                }
                for row in (savings.rows if savings_ok else [])
            ],
            "balances": [
                {
                    "kind": balance.kind,
                    "observed_on": balance.observed_on.isoformat()
                    if balance.observed_on is not None
                    else None,
                    "amount_pence": balance.amount_pence,
                }
                for balance in savings.balances
            ],
            # No source-stated totals apply to an interest-only export.
            "stated_totals": {},
        }

    excluded = [
        {
            "name": excluded_section["name"],
            "status": excluded_section["status"],
            "issues": [
                {
                    "code": excluded_section["status"],
                    "message": excluded_section["reason"],
                }
            ],
            "transactions": [],
            "balances": [],
        }
        for excluded_section in getattr(parsed, "excluded_sections", [])
    ]
    return {
        "version": claim["result_version"],
        "attempt": claim["attempt"],
        "outcome": "imported" if reconciled else "failed",
        "source_identity": getattr(parsed, "source_identity", ""),
        "savings_source_identity": getattr(parsed, "savings_source_identity", ""),
        "issues": section["issues"],
        "sections": [section, *([savings_section] if savings_section else []), *excluded],
    }


def process_one(client: WorkerClient, work_root: Path | None) -> dict | None:
    """Claim and process one job, cleaning temporary files in all cases."""
    claim = client.claim()
    if claim is None:
        return None

    workdir = Path(tempfile.mkdtemp(dir=work_root) if work_root else tempfile.mkdtemp())
    try:
        source = workdir / "source"
        data = client.download_source(claim["job"])
        source.write_bytes(data)
        client.progress(claim["job"], "downloaded")

        parsed = interpret(data, claim["upload"]["content_type"])
        client.progress(claim["job"], "interpreted")

        submitted = client.submit_result(claim["job"], build_result(claim, parsed))
        return {"job": claim["job"], **submitted}
    finally:
        shutil.rmtree(workdir, ignore_errors=True)
