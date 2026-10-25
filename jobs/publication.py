"""Validate and commit versioned worker results.

The worker is untrusted input: every monetary fact is re-checked here, sections
commit independently, and an unvalidated section contributes no financial facts.
"""

from dataclasses import dataclass
from datetime import date

from jobs.models import PublishedSection, SourceMapping
from ledger.models import (
    BalanceObservation,
    ClassificationSuggestion,
    Correction,
    DuplicateMatch,
    Transaction,
    Upload,
)
from reporting.totals import classify_source

SECTION_ACCOUNT_KINDS = {
    "lloyds_current": "current",
    "lloyds_credit": "card",
    "amex": "card",
    "revolut_personal_gbp": "current",
    "revolut_savings_gbp": "savings",
}
MAX_TRANSACTIONS_PER_SECTION = 5000
MAX_AMOUNT_PENCE = 10**12


class SectionRejected(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def validate_result_payload(body: dict) -> None:
    if body.get("outcome") in {"imported", "failed"}:
        sections = body.get("sections")
        if not isinstance(sections, list) or not sections:
            raise ValueError("sections must be a non-empty list")
        for section in sections:
            if not isinstance(section, dict) or not isinstance(section.get("name"), str):
                raise ValueError("each section needs a name")
            if section.get("status") not in {"ok", "failed", "ignored", "deferred"}:
                raise ValueError("section status is not supported")
            for key in ("transactions", "balances", "issues"):
                if not isinstance(section.get(key, []), list):
                    raise ValueError(f"section {key} must be a list")
            if section.get("status") == "ok":
                try:
                    for row in section.get("transactions", []):
                        _transaction_fields(row)
                    for balance in section.get("balances", []):
                        _balance_fields(balance)
                except SectionRejected as exc:
                    raise ValueError(exc.message) from exc
    issues = body.get("issues", [])
    if not isinstance(issues, list):
        raise ValueError("issues must be a list")


@dataclass(frozen=True)
class PublicationOutcome:
    status: str
    committed: int
    rejected: int
    deferred: int


def apply_result(job, body: dict) -> PublicationOutcome:
    """Commit a validated result and return the new upload status."""
    outcome = body["outcome"]
    upload = job.upload

    if outcome == "unsupported":
        return PublicationOutcome(Upload.Status.UNSUPPORTED, 0, 0, 0)
    if outcome == "failed":
        return PublicationOutcome(Upload.Status.NEEDS_REVIEW, 0, 0, 0)

    upload = job.upload
    identity = body.get("source_identity") or ""
    mapping = SourceMapping.objects.filter(source_identity=identity).first() if identity else None
    if mapping is not None and not _mapping_consistent(mapping, upload, body):
        body.setdefault("server_issues", []).append(
            {
                "section": "source_mapping",
                "code": "source_identity_mismatch",
                "message": (
                    "This source was previously confirmed against different named "
                    "accounts; confirm the mapping before importing."
                ),
            }
        )
        return PublicationOutcome(Upload.Status.NEEDS_REVIEW, 0, 1, 0)

    committed = 0
    rejected = 0
    deferred = 0
    duplicate_sections = 0
    server_issues = body.setdefault("server_issues", [])
    prior_sections = PublishedSection.objects.filter(
        upload__original_id=upload.original_id
    ).exclude(upload=upload)

    for section in body["sections"]:
        status = section.get("status")
        if status == "ignored":
            continue
        if status == "ok" and section.get("account_role") == "savings" and upload.savings_account is None:
            deferred += 1
            server_issues.append(
                {
                    "section": section["name"],
                    "code": "mapping_required",
                    "message": "Choose the savings account for this consolidated statement.",
                }
            )
            continue
        if status == "deferred":
            deferred += 1
            server_issues.append(
                {
                    "section": section["name"],
                    "code": "section_deferred",
                    "message": "This section is not implemented yet and was not imported.",
                }
            )
            continue
        if status == "ok":
            try:
                section_account = _section_account(upload, section)
            except SectionRejected as exc:
                rejected += 1
                server_issues.append(
                    {"section": section["name"], "code": exc.code, "message": exc.message}
                )
                continue
            if prior_sections.filter(
                name=section["name"], account=section_account
            ).exists():
                duplicate_sections += 1
                server_issues.append(
                    {
                        "section": section["name"],
                        "code": "already_imported_section",
                        "message": (
                            "These bytes were already committed for this account "
                            "section; no duplicate effects were added."
                        ),
                    }
                )
                continue
        try:
            publish_section(upload, section)
            committed += 1
        except SectionRejected as exc:
            rejected += 1
            server_issues.append(
                {"section": section["name"], "code": exc.code, "message": exc.message}
            )

    if committed and not rejected and not deferred:
        status = Upload.Status.IMPORTED
    elif duplicate_sections and not committed and not rejected and not deferred:
        status = Upload.Status.DUPLICATE
    else:
        status = Upload.Status.NEEDS_REVIEW
    if identity and committed and not rejected:
        _store_mapping(identity, upload, mapping, body)

    return PublicationOutcome(status, committed, rejected, deferred)


def _mapping_consistent(mapping, upload, body) -> bool:
    if mapping.primary_account_id != upload.account_id:
        return False
    if (
        upload.savings_account_id is not None
        and mapping.savings_account_id is not None
        and mapping.savings_account_id != upload.savings_account_id
    ):
        return False
    reported_savings = body.get("savings_source_identity") or ""
    if (
        upload.savings_account_id is not None
        and mapping.savings_source_identity
        and reported_savings
        and mapping.savings_source_identity != reported_savings
    ):
        return False
    return True


def _store_mapping(identity: str, upload, mapping, body) -> None:
    savings = upload.savings_account or (mapping.savings_account if mapping else None)
    savings_identity = body.get("savings_source_identity") or (
        mapping.savings_source_identity if mapping else ""
    )
    if upload.savings_account is None and mapping is None:
        savings_identity = ""
    SourceMapping.objects.update_or_create(
        source_identity=identity,
        defaults={
            "primary_account": upload.account,
            "savings_account": savings,
            "savings_source_identity": savings_identity,
        },
    )


def publish_section(upload, section: dict) -> None:
    name = section["name"]
    if section.get("status") != "ok":
        raise SectionRejected("section_failed", f"Section {name} reported a failed outcome.")

    expected_kind = SECTION_ACCOUNT_KINDS.get(name)
    if expected_kind is None:
        raise SectionRejected("unsupported_section", f"Section {name} is not supported.")
    account = _section_account(upload, section)
    if expected_kind != account.kind:
        raise SectionRejected(
            "account_identity_mismatch",
            f"This {name.replace('_', ' ')} statement does not match the selected "
            f"{account.get_kind_display().lower()} account.",
        )

    rows = [_transaction_fields(row) for row in section.get("transactions", [])]
    balances = [_balance_fields(balance) for balance in section.get("balances", [])]
    if not rows and not (expected_kind == "savings" and balances):
        raise SectionRejected("empty_section", f"Section {name} contained no transactions.")
    if len(rows) > MAX_TRANSACTIONS_PER_SECTION:
        raise SectionRejected("section_too_large", f"Section {name} has too many transactions.")
    if len({(row["page"], row["row"]) for row in rows}) != len(rows):
        raise SectionRejected("duplicate_source_row", "Two rows share a source location.")

    _check_reconciliation(rows, balances, section)

    created = []
    for row in rows:
        created.append(Transaction.objects.create(
            account=account,
            upload=upload,
            posted_on=row["posted_on"],
            source_transaction_date=row["source_transaction_date"],
            description=row["description"],
            transaction_type=row["transaction_type"],
            amount_pence=row["amount_pence"],
            balance_pence=row["balance_pence"],
            source_page=row["page"],
            source_row=row["row"],
            source_text=row["source_text"],
        ))
    _flag_overlap_candidates(created)
    _store_suggestions(created, section.get("suggestions", []))
    PublishedSection.objects.get_or_create(
        upload=upload, name=name, defaults={"account": account}
    )
    for balance in balances:
        BalanceObservation.objects.create(
            account=account,
            upload=upload,
            kind=balance["kind"],
            observed_on=balance["observed_on"],
            amount_pence=balance["amount_pence"],
        )


def _flag_overlap_candidates(created) -> None:
    """Flag cross-original rows with identical date/amount/description for review.

    Tuple equality alone is never treated as proof; both rows stay and the
    affected totals become provisional until a person decides.
    """
    for transaction in created:
        peers = Transaction.objects.filter(
            account_id=transaction.account_id,
            posted_on=transaction.posted_on,
            amount_pence=transaction.amount_pence,
            description=transaction.description,
        ).exclude(upload_id=transaction.upload_id)
        if peers.exists():
            transaction.needs_review = True
            transaction.save(update_fields=["needs_review"])
            peers.update(needs_review=True)


ADVISORY_VERSION = 1
MAX_ADVICE_PER_SECTION = 200
ADVISORY_CLASSIFICATIONS = {choice for choice, _label in Correction.Classification.choices}


def advisory_fields(entry) -> dict:
    """Validate one advisory entry; raise ValueError if it must not be shown."""
    if not isinstance(entry, dict):
        raise ValueError("suggestion must be an object")
    try:
        version = _bounded_int(entry["version"])
        confidence = float(entry["confidence"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("suggestion fields are malformed") from exc
    classification = entry.get("classification")
    explanation = str(entry.get("explanation") or "").strip()
    model = str(entry.get("model") or "").strip()
    prompt_version = str(entry.get("prompt_version") or "").strip()
    if version != ADVISORY_VERSION:
        raise ValueError("unsupported advisory version")
    if not isinstance(classification, str) or classification not in ADVISORY_CLASSIFICATIONS:
        raise ValueError("unsupported advisory classification")
    if not 0.0 <= confidence <= 1.0:
        raise ValueError("advice confidence is out of range")
    if not explanation:
        raise ValueError("advice explanation is required")
    if not model:
        raise ValueError("advice model is required")
    return {
        "version": version,
        "classification": classification,
        "confidence": confidence,
        "explanation": explanation[:500],
        "model": model[:100],
        "prompt_version": prompt_version[:20],
    }


def _store_suggestions(created, raw_suggestions) -> None:
    """Store only well-formed advice for rows the deterministic rules left unresolved.

    Advice is optional: malformed entries are dropped rather than failing the
    import, and a suggestion never changes a financial fact by itself. Duplicate
    or contradictory advice for one row is kept separate for the user to review.
    """
    if not isinstance(raw_suggestions, list):
        return
    by_location = {(row.source_page, row.source_row): row for row in created}
    stored = 0
    for entry in raw_suggestions:
        if stored >= MAX_ADVICE_PER_SECTION:
            return
        try:
            page = _positive_int(entry["page"])
            row_number = _positive_int(entry["row"])
            fields = advisory_fields(entry)
        except (KeyError, TypeError, ValueError):
            continue
        transaction = by_location.get((page, row_number))
        if transaction is None:
            continue
        if classify_source(transaction) is not None:
            # Deterministic evidence already resolves this row; advice adds nothing.
            continue
        ClassificationSuggestion.objects.create(transaction=transaction, **fields)
        stored += 1


def _section_account(upload, section: dict):
    """Resolve the confirmed named account for a section without reassigning."""
    if section.get("account_role") == "savings":
        if upload.savings_account is None:
            raise SectionRejected(
                "mapping_required",
                "Choose the savings account for this consolidated statement.",
            )
        return upload.savings_account
    return upload.account


def _transaction_fields(row: dict) -> dict:
    if not isinstance(row, dict):
        raise SectionRejected("invalid_transaction", "Transaction entries must be objects.")
    try:
        posted_on = date.fromisoformat(str(row["posted_on"]))
        amount = _bounded_int(row["amount_pence"])
        balance = row.get("balance_pence")
        balance = None if balance is None else _bounded_int(balance)
        page = _positive_int(row["page"])
        row_number = _positive_int(row["row"])
    except (KeyError, TypeError, ValueError) as exc:
        raise SectionRejected("invalid_transaction", "A transaction entry is malformed.") from exc

    source_date = row.get("source_transaction_date")
    if source_date is not None:
        try:
            source_date = date.fromisoformat(str(source_date))
        except ValueError as exc:
            raise SectionRejected(
                "invalid_transaction", "A transaction purchase date is malformed."
            ) from exc

    return {
        "posted_on": posted_on,
        "source_transaction_date": source_date,
        "description": str(row.get("description", ""))[:500],
        "transaction_type": str(row.get("transaction_type", ""))[:60],
        "amount_pence": amount,
        "balance_pence": balance,
        "page": page,
        "row": row_number,
        "source_text": str(row.get("source_text", ""))[:1000],
    }


def _balance_fields(balance: dict) -> dict:
    if not isinstance(balance, dict) or balance.get("kind") not in {"opening", "closing"}:
        raise SectionRejected("invalid_balance", "A balance anchor is malformed.")
    try:
        raw_observed = balance.get("observed_on")
        observed_on = None if raw_observed is None else date.fromisoformat(str(raw_observed))
        amount = _bounded_int(balance["amount_pence"])
    except (TypeError, ValueError) as exc:
        raise SectionRejected("invalid_balance", "A balance anchor is malformed.") from exc
    return {"kind": balance["kind"], "observed_on": observed_on, "amount_pence": amount}


def _bounded_int(value) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("amounts must be integer pence")
    if abs(value) > MAX_AMOUNT_PENCE:
        raise ValueError("amount out of range")
    return value


def _positive_int(value) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError("locator must be a positive integer")
    return value


def _check_reconciliation(rows: list[dict], balances: list[dict], section: dict) -> None:
    opening = next((b for b in balances if b["kind"] == "opening"), None)
    closing = next((b for b in balances if b["kind"] == "closing"), None)
    if opening is None or closing is None:
        raise SectionRejected(
            "missing_balance_anchor",
            "The section has no opening and closing balance evidence; nothing was imported.",
        )

    section_kind = SECTION_ACCOUNT_KINDS.get(section["name"])
    card_section = section_kind == "card"
    savings_section = section_kind == "savings"
    has_running_balances = any(row["balance_pence"] is not None for row in rows)

    if savings_section:
        # Interest-only exports cannot prove principal movements; the supplied
        # anchors stand and any unexplained change is reported by the worker.
        total = opening["amount_pence"] + sum(row["amount_pence"] for row in rows)
    elif card_section and not has_running_balances:
        # Card statements state only debt anchors; validate the debt equation.
        total = (
            opening["amount_pence"]
            + sum(row["amount_pence"] for row in rows if row["amount_pence"] > 0)
            - sum(-row["amount_pence"] for row in rows if row["amount_pence"] < 0)
        )
    else:
        previous = opening["amount_pence"]
        for row in rows:
            if row["balance_pence"] is None:
                raise SectionRejected(
                    "missing_running_balance",
                    f"No running balance accompanies the {row['posted_on'].isoformat()} row.",
                )
            if row["balance_pence"] - previous != row["amount_pence"]:
                raise SectionRejected(
                    "running_balance_mismatch",
                    f"The {row['posted_on'].isoformat()} row states {row['amount_pence']} pence "
                    f"but changes the balance by {row['balance_pence'] - previous} pence.",
                )
            previous = row["balance_pence"]
        total = previous

    if not savings_section and total != closing["amount_pence"]:
        raise SectionRejected(
            "reconciliation_failed",
            f"Opening plus rows gives {total} pence, not the stated "
            f"{closing['amount_pence']} pence; nothing was imported.",
        )

    stated = section.get("stated_totals")
    if not isinstance(stated, dict):
        raise SectionRejected(
            "missing_statement_summary",
            "The section carries no source-stated summary to validate against.",
        )

    credits = -sum(row["amount_pence"] for row in rows if row["amount_pence"] < 0)
    debits = sum(row["amount_pence"] for row in rows if row["amount_pence"] > 0)
    name = section["name"]

    if name == "lloyds_current":
        for key, derived in (("money_in_pence", debits), ("money_out_pence", credits)):
            if stated.get(key) is None:
                raise SectionRejected(
                    "missing_statement_summary",
                    f"The source did not state {key.replace('_pence', '').replace('_', ' ')}.",
                )
            if stated[key] != derived:
                raise SectionRejected(
                    "totals_mismatch",
                    f"Stated {key.replace('_pence', '').replace('_', ' ')} {stated[key]} pence "
                    f"differs from rows {derived} pence.",
                )
    elif name == "lloyds_credit":
        payments = stated.get("payments_received_pence")
        if payments is None:
            raise SectionRejected(
                "missing_statement_summary",
                "The source did not state payments received.",
            )
        if payments > credits:
            raise SectionRejected(
                "totals_mismatch",
                f"Stated payments {payments} pence exceed the {credits} pence of credits.",
            )
    elif name == "amex":
        payments = stated.get("payments_and_credits_pence")
        if payments is None:
            raise SectionRejected(
                "missing_statement_summary",
                "The source did not state payments and credits.",
            )
        if payments != credits:
            raise SectionRejected(
                "totals_mismatch",
                f"Stated payments and credits {payments} pence differ from rows {credits} pence.",
            )
