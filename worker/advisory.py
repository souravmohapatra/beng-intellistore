"""Client and schemas for isolated local LLM advisory inference.

Advisory output is purely suggestive; it never alters financial facts, dates,
amounts, or balances, and must be explicitly accepted by the user to take effect.
"""

import datetime
from dataclasses import dataclass
from enum import StrEnum
import json
import logging
import time
from typing import Any
import urllib.error
import urllib.request

logger = logging.getLogger(__name__)

ADVISORY_SCHEMA_VERSION = 1

# Optional advice must never turn malformed configuration into unbounded work.
# These hard caps apply on top of any INFERENCE_* environment value.
AUTOMATIC_ADVICE_MAX_ATTEMPTS = 2
AUTOMATIC_ADVICE_MAX_RETRY_DELAY_SECONDS = 10.0
# Stay this far inside the heartbeat lease so a request cannot outlive it.
LEASE_SAFETY_MARGIN_SECONDS = 5.0


def remaining_seconds(expiry, margin: float = LEASE_SAFETY_MARGIN_SECONDS):
    """Seconds until a lease expiry minus a safety margin.

    `expiry` is the ISO-8601 `lease_expires_at` returned by the worker API (or an
    aware datetime). Unknown/unparseable input returns None so callers keep their
    configured defaults instead of failing an optional advice path.
    """
    if expiry is None:
        return None
    try:
        parsed = (
            datetime.datetime.fromisoformat(expiry.replace("Z", "+00:00"))
            if isinstance(expiry, str)
            else expiry
        )
        if not isinstance(parsed, datetime.datetime) or parsed.tzinfo is None:
            return None
        delta = (
            parsed - datetime.datetime.now(datetime.timezone.utc)
        ).total_seconds()
    except (TypeError, ValueError):
        return None
    return max(0.0, delta - margin)


class AdvisoryClassification(StrEnum):
    SPENDING = "spending"
    INCOME = "income"
    TRANSFER = "transfer"
    REFUND = "refund"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class AdvisorySuggestion:
    version: int
    classification: AdvisoryClassification
    confidence: float
    explanation: str
    model: str
    prompt_version: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "classification": self.classification.value,
            "confidence": self.confidence,
            "explanation": self.explanation,
            "model": self.model,
            "prompt_version": self.prompt_version,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AdvisorySuggestion":
        version = int(data.get("version", 0))
        if version != ADVISORY_SCHEMA_VERSION:
            raise ValueError(f"Unsupported advisory schema version: {version}")
        raw_classification = data.get("classification")
        try:
            classification = AdvisoryClassification(raw_classification)
        except ValueError:
            raise ValueError(f"Unknown advisory classification: {raw_classification}")

        confidence = float(data.get("confidence", 0.0))
        if not (0.0 <= confidence <= 1.0):
            raise ValueError(f"Confidence out of range: {confidence}")

        explanation = str(data.get("explanation", "")).strip()
        model = str(data.get("model", "")).strip()
        prompt_version = str(data.get("prompt_version", "")).strip()

        if not explanation:
            raise ValueError("Explanation is required")
        if not model:
            raise ValueError("Model is required")

        return cls(
            version=version,
            classification=classification,
            confidence=confidence,
            explanation=explanation,
            model=model,
            prompt_version=prompt_version,
        )


class AdvisoryClientError(Exception):
    """Base error for advisory inference operations."""


class AdvisoryUnavailableError(AdvisoryClientError):
    """Raised when the inference service is unreachable or timing out."""


class AdvisoryFormatError(AdvisoryClientError):
    """Raised when the inference response is malformed or invalid."""


class LocalInferenceClient:
    """Client for querying the isolated project Docker inference service."""

    def __init__(
        self,
        base_url: str,
        model: str = "qwen2.5:7b-instruct",
        timeout_seconds: float = 10.0,
        prompt_version: str = "v1",
    ):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.prompt_version = prompt_version

    def suggest_classification(
        self,
        description: str,
        amount_pence: int,
        account_kind: str,
        prompt_version: str | None = None,
        timeout_seconds: float | None = None,
    ) -> AdvisorySuggestion:
        """Query the model to classify an ambiguous or unresolved transaction.

        `timeout_seconds` is an optional upper bound (e.g. remaining job lease);
        the configured timeout still applies when it is larger. Unknown or
        malformed prompt versions fall back to the configured provenance.
        """
        effective_timeout = self.timeout_seconds
        if timeout_seconds is not None:
            effective_timeout = min(self.timeout_seconds, timeout_seconds)
        if effective_timeout <= 0:
            raise AdvisoryUnavailableError(
                "No time remains in the job lease for advisory inference"
            )
        prompt = (
            f"You are a personal financial transaction classifier.\n"
            f"Classify the following transaction into one of: spending, income, transfer, refund, unknown.\n\n"
            f"Account type: {account_kind}\n"
            f"Description: {description}\n"
            f"Amount in pence: {amount_pence}\n\n"
            f"Respond strictly with valid JSON with keys: 'classification', 'confidence' (0.0 to 1.0), 'explanation'."
        )

        payload = {
            "model": self.model,
            "prompt": prompt,
            "format": "json",
            "stream": False,
        }

        endpoint = f"{self.base_url}/api/generate"
        req = urllib.request.Request(
            endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=effective_timeout) as resp:
                if resp.status != 200:
                    raise AdvisoryUnavailableError(f"Inference HTTP error {resp.status}")
                raw_body = resp.read().decode("utf-8")
        except urllib.error.URLError as err:
            raise AdvisoryUnavailableError(f"Failed to connect to inference service: {err}") from err
        except TimeoutError as err:
            raise AdvisoryUnavailableError(f"Inference service timed out: {err}") from err
        except AdvisoryClientError:
            raise
        except Exception as err:
            raise AdvisoryClientError(f"Unexpected error querying inference service: {err}") from err

        try:
            outer = json.loads(raw_body)
            if not isinstance(outer, dict):
                raise ValueError("outer response must be an object")
            response_text = outer.get("response", "")
            parsed = json.loads(response_text)
        except Exception as err:
            raise AdvisoryFormatError(f"Malformed JSON returned by model: {err}") from err

        if not isinstance(parsed, dict):
            raise AdvisoryFormatError("Model output must be a JSON object")

        parsed["version"] = ADVISORY_SCHEMA_VERSION
        parsed["model"] = self.model
        parsed["prompt_version"] = prompt_version or self.prompt_version

        try:
            return AdvisorySuggestion.from_dict(parsed)
        except (ValueError, TypeError) as err:
            raise AdvisoryFormatError(f"Model output failed validation: {err}") from err


UNRESOLVED_TYPE_HINTS = {"", "other", "others", "unknown", "misc", "miscellaneous"}


def collect_advice(
    parsed,
    client: LocalInferenceClient,
    max_attempts: int = 2,
    retry_delay_seconds: float = 2.0,
    max_rows: int = 25,
    on_progress=None,
) -> dict[str, list[dict]]:
    """Ask for bounded advice on ambiguous rows; never fail the import.

    Only rows whose source type looks unresolved are sent, capped by `max_rows`
    so advice cannot consume the whole job lease. Attempts and retry delay are
    additionally clamped to `AUTOMATIC_ADVICE_MAX_ATTEMPTS` /
    `AUTOMATIC_ADVICE_MAX_RETRY_DELAY_SECONDS`, so a malformed INFERENCE_* value
    cannot create unbounded automatic work. `on_progress` renews the job lease
    before every attempt (it may return the fresh `lease_expires_at`, which then
    caps the request timeout); if it raises, advice stops and the error
    propagates so the caller does not publish on a lost lease.
    """
    max_attempts = max(1, min(int(max_attempts), AUTOMATIC_ADVICE_MAX_ATTEMPTS))
    retry_delay_seconds = max(
        0.0, min(float(retry_delay_seconds), AUTOMATIC_ADVICE_MAX_RETRY_DELAY_SECONDS)
    )
    advices: dict[str, list[dict]] = {}
    sent = 0
    for name, rows, kind in _advice_sections(parsed):
        entries: list[dict] = []
        for row in rows:
            if sent >= max_rows:
                advices[name] = entries
                return advices
            if str(row.transaction_type or "").strip().lower() not in UNRESOLVED_TYPE_HINTS:
                continue
            sent += 1
            suggestion = _advise_with_retry(
                client,
                row,
                kind,
                max_attempts,
                retry_delay_seconds,
                on_progress=on_progress,
            )
            if suggestion is None:
                continue
            entries.append(
                {
                    "page": row.page,
                    "row": row.row,
                    "version": suggestion.version,
                    "classification": suggestion.classification.value,
                    "confidence": suggestion.confidence,
                    "explanation": suggestion.explanation,
                    "model": suggestion.model,
                    "prompt_version": suggestion.prompt_version,
                }
            )
        advices[name] = entries
    return advices


def _advice_sections(parsed):
    sections = []
    if parsed is None or not getattr(parsed, "reconciled", False):
        return sections
    sections.append(
        (parsed.section_name, parsed.rows, getattr(parsed, "account_kind_hint", "current"))
    )
    savings = getattr(parsed, "savings", None)
    if savings is not None and savings.recognised and not savings.issues:
        sections.append(("revolut_savings_gbp", savings.rows, "savings"))
    return sections


def _advise_with_retry(
    client, row, account_kind, max_attempts, retry_delay_seconds, on_progress=None
):
    """Advise one unresolved row within its heartbeat lease.

    `on_progress` renews the lease before each attempt; its return value, when
    the caller provides the fresh `lease_expires_at`, becomes a deadline cap on
    the request timeout and on whether a retry delay can still fit. Attempts and
    delay are already clamped by `collect_advice`, so this cannot loop forever.
    """
    last_error = None
    for attempt in range(max_attempts):
        lease_expiry = on_progress() if on_progress is not None else None
        remaining = remaining_seconds(lease_expiry)
        if remaining is not None and remaining <= 0:
            # Never start a request that cannot finish before the lease expires.
            break
        call = {
            "description": row.description,
            "amount_pence": row.amount_pence,
            "account_kind": account_kind,
            "prompt_version": getattr(client, "prompt_version", "v1"),
        }
        if remaining is not None:
            call["timeout_seconds"] = remaining
        try:
            return client.suggest_classification(**call)
        except Exception as err:  # optional advice must never break the import
            last_error = err
            if attempt + 1 >= max_attempts:
                break
            # Renew again before waiting; a retry delay counts against the lease.
            lease_expiry = on_progress() if on_progress is not None else None
            remaining = remaining_seconds(lease_expiry)
            if remaining is not None and retry_delay_seconds >= remaining:
                break
            if retry_delay_seconds:
                time.sleep(retry_delay_seconds)
    if last_error is not None:
        # Only the exception class: model text can echo private description content.
        logger.warning(
            "local advice unavailable for an unresolved row (%s)",
            type(last_error).__name__,
        )
    return None


def client_from_env(*, force: bool = False) -> LocalInferenceClient | None:
    """Build the inference client only when explicitly enabled and configured.

    A URL alone is a smoke/qualification setting, not permission to show advice
    during ordinary use. `force` is used only by the explicit connectivity check.
    """
    import os
    import math

    url = os.environ.get("INFERENCE_URL", "").strip()
    if not url:
        return None
    enabled = os.environ.get("INFERENCE_ENABLED", "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    if not enabled and not force:
        return None
    try:
        timeout = float(os.environ.get("INFERENCE_TIMEOUT_SECONDS", "10"))
    except ValueError:
        timeout = 10.0
    if not math.isfinite(timeout) or timeout <= 0:
        timeout = 10.0
    return LocalInferenceClient(
        url,
        model=(
            os.environ.get("INFERENCE_MODEL", "").strip() or "qwen2.5:7b-instruct"
        ),
        timeout_seconds=timeout,
        prompt_version=(
            os.environ.get("INFERENCE_PROMPT_VERSION", "").strip() or "v1"
        ),
    )
