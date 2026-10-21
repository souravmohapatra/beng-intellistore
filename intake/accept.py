"""Upload acceptance: preserve bytes first, then record the receipt."""

from pathlib import Path

from django.db import transaction

from intake.storage import store_original
from ledger.models import Original, Upload


def accept_upload(
    *, account, filename: str, data: bytes, content_type: str
) -> Upload:
    """Preserve ``data`` locally and record a receipt for it.

    The blob is stored before the database record is created, so a storage
    failure cannot produce a successful receipt. A database failure can leave an
    orphaned blob but never a receipt without preserved bytes.
    """
    stored = store_original(data)
    with transaction.atomic():
        original, _created = Original.objects.get_or_create(
            sha256=stored.sha256,
            defaults={
                "byte_size": stored.byte_size,
                "content_type": content_type or "application/octet-stream",
                "stored_path": stored.stored_path,
            },
        )
        return Upload.objects.create(
            original=original,
            account=account,
            filename=Path(filename).name or "statement",
        )
