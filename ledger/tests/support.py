"""Shared setup for intake tests: isolated data directory and signed-in client."""

import shutil
import tempfile
import time
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management.base import CommandError
from django.db import OperationalError, connections
from django.test import LiveServerTestCase, override_settings
from django.urls import reverse

from ledger.models import Account, AccountKind


class RetryingLiveServerTestCase(LiveServerTestCase):
    """Live server tests whose subprocess clients can briefly hold DB locks.

    PostgreSQL can report a deadlock while flushing between these tests if a
    finishing HTTP request still holds a relation lock. Retrying the flush after
    closing this thread's connection is safe and avoids a flaky suite; genuine
    flush failures still surface after the bounded attempts.
    """

    def _fixture_teardown(self):
        last_error = None
        for attempt in range(6):
            try:
                return super()._fixture_teardown()
            except (OperationalError, CommandError) as exc:
                last_error = exc
                connections.close_all()
                time.sleep(0.25 * (attempt + 1))
        raise last_error


class UploadSetupMixin:
    def setUp(self):
        self.data_dir = Path(tempfile.mkdtemp())
        self.settings_override = override_settings(DATA_DIR=self.data_dir)
        self.settings_override.enable()
        self.addCleanup(self.settings_override.disable)
        self.addCleanup(shutil.rmtree, self.data_dir, ignore_errors=True)

        self.account = Account.objects.create(
            name="Lloyds Current", kind=AccountKind.CURRENT
        )
        self.user = get_user_model().objects.create_user(
            username="sourav", password="local-dev-password"
        )
        self.client.force_login(self.user)

    def upload(self, data, filename="statement.pdf", account=None, savings_account=None):
        payload = {
            "account": (account or self.account).pk,
            "file": SimpleUploadedFile(filename, data, content_type="application/pdf"),
        }
        if savings_account is not None:
            payload["savings_account"] = savings_account.pk
        return self.client.post(reverse("ledger:uploads"), payload)

    def stored_blobs(self):
        originals = self.data_dir / "originals"
        if not originals.exists():
            return []
        return [path for path in originals.rglob("*") if path.is_file()]
