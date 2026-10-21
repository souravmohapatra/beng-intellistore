"""Shared setup for intake tests: isolated data directory and signed-in client."""

import shutil
import tempfile
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse

from ledger.models import Account, AccountKind


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

    def upload(self, data, filename="statement.pdf", account=None):
        return self.client.post(
            reverse("ledger:uploads"),
            {
                "account": (account or self.account).pk,
                "file": SimpleUploadedFile(
                    filename, data, content_type="application/pdf"
                ),
            },
        )

    def stored_blobs(self):
        originals = self.data_dir / "originals"
        if not originals.exists():
            return []
        return [path for path in originals.rglob("*") if path.is_file()]
