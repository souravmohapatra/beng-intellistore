"""Content inspection for intake: decisions come from bytes, not extensions.

Only formats with an implemented, fixture-backed layout may be treated as
importable. Everything readable but unimplemented is preserved as unsupported.
"""

import io
from dataclasses import dataclass

import pypdf

from ledger.models import Upload

MAX_BYTES = 20 * 1024 * 1024
MAX_PAGES = 100
PDF_MAGIC = b"%PDF-"

# Readable files are preserved and wait for interpretation; the worker decides
# whether a layout is supported, so intake never claims an import.``


class IntakeRejected(Exception):
    """The file cannot be accepted; the message is shown to the user."""


class FileTooLarge(IntakeRejected):
    """The file exceeds the intake size limit."""


@dataclass(frozen=True)
class Inspection:
    content_type: str
    status: str


def inspect(data: bytes, filename: str) -> Inspection:
    if len(data) > MAX_BYTES:
        raise FileTooLarge("This file is larger than 20 MiB.")

    if PDF_MAGIC in data[:1024]:
        return _inspect_pdf(data)

    if _readable_text(data) is not None:
        content_type = "text/csv" if filename.lower().endswith(".csv") else "text/plain"
        return Inspection(content_type=content_type, status=Upload.Status.PENDING)

    raise IntakeRejected(
        "This file type is not supported. Upload a PDF, text or CSV statement."
    )


def _inspect_pdf(data: bytes) -> Inspection:
    try:
        reader = pypdf.PdfReader(io.BytesIO(data))
        if reader.is_encrypted:
            raise IntakeRejected(
                "This PDF is password-protected. Remove the password and try again."
            )
        page_count = len(reader.pages)
        if page_count > MAX_PAGES:
            raise IntakeRejected(
                f"This PDF has {page_count} pages; more than 100 pages is not supported."
            )
        if not any(page.extract_text().strip() for page in reader.pages):
            raise IntakeRejected(
                "This PDF has no selectable text. Scanned PDFs and OCR are not supported."
            )
    except IntakeRejected:
        raise
    except Exception as exc:  # malformed structure, unsupported filters, EOF...
        raise IntakeRejected("This file is damaged or unreadable.") from exc
    return Inspection(content_type="application/pdf", status=Upload.Status.PENDING)


def _readable_text(data: bytes) -> str | None:
    if b"\x00" in data[:4096]:
        return None
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return None
