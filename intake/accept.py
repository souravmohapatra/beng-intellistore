"""Upload acceptance: inspect, preserve bytes, then record the receipt."""

from pathlib import Path

from django.db import transaction

from intake.inspect import inspect
from intake.storage import store_original
from jobs.models import Job
from ledger.models import Original, Upload


def accept_upload(*, account, filename: str, data: bytes) -> Upload:
    """Preserve ``data`` locally and record a receipt for it.

    Inspection runs before storage, so an unacceptable file leaves no trace. The
    blob is then stored before the database records are created, so a storage
    failure cannot produce a successful receipt; the receipt and its original
    commit together.
    """
    inspection = inspect(data, filename)
    stored = store_original(data)

    with transaction.atomic():
        original, _created = Original.objects.get_or_create(
            sha256=stored.sha256,
            defaults={
                "byte_size": stored.byte_size,
                "content_type": inspection.content_type,
                "stored_path": stored.stored_path,
            },
        )
        upload = Upload.objects.create(
            original=original,
            account=account,
            filename=Path(filename).name or "statement",
            status=inspection.status,
            review_note=_identity_note(stored.sha256, account),
        )
        Job.objects.create(upload=upload)
        return upload


def _identity_note(sha256: str, account) -> str:
    """Flag a file already accepted for other accounts; never reassign it."""
    prior = (
        Upload.objects.filter(original__sha256=sha256)
        .exclude(account=account)
        .select_related("account")
    )
    names = sorted({upload.account.name for upload in prior})
    if not names:
        return ""
    return (
        f"This file was previously accepted for {', '.join(names)}. "
        "Check the selected account before processing."
    )
