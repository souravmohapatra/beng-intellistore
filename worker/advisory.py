"""Client and schemas for isolated local LLM advisory inference.

Advisory output is purely suggestive; it never alters financial facts, dates,
amounts, or balances, and must be explicitly accepted by the user to take effect.
"""

from dataclasses import dataclass
from enum import StrEnum
import json
import logging
from typing import Any
import urllib.error
import urllib.request

logger = logging.getLogger(__name__)

ADVISORY_SCHEMA_VERSION = 1


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

    def __init__(self, base_url: str, model: str = "qwen2.5:7b-instruct", timeout_seconds: float = 10.0):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout_seconds = timeout_seconds

    def suggest_classification(
        self,
        description: str,
        amount_pence: int,
        account_kind: str,
        prompt_version: str = "v1",
    ) -> AdvisorySuggestion:
        """Query the model to classify an ambiguous or unresolved transaction."""
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
            with urllib.request.urlopen(req, timeout=self.timeout_seconds) as resp:
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
        parsed["prompt_version"] = prompt_version

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
) -> dict[str, list[dict]]:
    """Ask for bounded advice on ambiguous rows; never fail the import.

    Only rows whose source type looks unresolved are sent. Each suggestion is
    stamped with its source location so the application can attach it to the
    exact transaction. Advice failure yields no entries for that row.
    """
    advices: dict[str, list[dict]] = {}
    for name, rows, kind in _advice_sections(parsed):
        entries: list[dict] = []
        for row in rows:
            if str(row.transaction_type or "").strip().lower() not in UNRESOLVED_TYPE_HINTS:
                continue
            suggestion = _advise_with_retry(
                client, row, kind, max_attempts, retry_delay_seconds
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


def _advise_with_retry(client, row, account_kind, max_attempts, retry_delay_seconds):
    last_error = None
    for attempt in range(max_attempts):
        try:
            return client.suggest_classification(
                description=row.description,
                amount_pence=row.amount_pence,
                account_kind=account_kind,
            )
        except Exception as err:  # optional advice must never break the import
            last_error = err
            if attempt + 1 < max_attempts and retry_delay_seconds:
                import time

                time.sleep(retry_delay_seconds)
    # Message text may include a URL, never financial contents.
    logger.warning("local advice unavailable for an unresolved row: %s", last_error)
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
        model=os.environ.get("INFERENCE_MODEL", "qwen2.5:7b-instruct"),
        timeout_seconds=timeout,
    )
