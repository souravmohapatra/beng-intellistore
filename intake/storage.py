"""Durable local storage for accepted originals.

Bytes are written to a temporary file on the same filesystem, flushed to disk,
and atomically renamed into a content-addressed path. A returned
``StoredOriginal`` means the bytes are durable; any failure raises
``StorageUnavailable`` and leaves no accepted receipt.
"""

import hashlib
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path

from django.conf import settings


class StorageUnavailable(Exception):
    """Local storage could not preserve an original."""


@dataclass(frozen=True)
class StoredOriginal:
    sha256: str
    byte_size: int
    stored_path: str


def store_original(data: bytes) -> StoredOriginal:
    digest = hashlib.sha256(data).hexdigest()
    relative = Path("originals") / digest[:2] / digest
    destination = Path(settings.DATA_DIR) / relative
    try:
        destination.parent.mkdir(parents=True, exist_ok=True)
        handle_fd, temporary = tempfile.mkstemp(
            dir=destination.parent, prefix=".incoming-"
        )
        try:
            with os.fdopen(handle_fd, "wb") as handle:
                handle.write(data)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, destination)
        except BaseException:
            Path(temporary).unlink(missing_ok=True)
            raise
        directory_fd = os.open(destination.parent, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    except OSError as exc:
        raise StorageUnavailable(str(exc)) from exc
    return StoredOriginal(digest, len(data), str(relative))
