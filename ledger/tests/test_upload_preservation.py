"""Behavioral tests for durable original preservation and retrieval."""

import shutil
import tempfile
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import OperationalError, connection
from django.test import TestCase, TransactionTestCase, override_settings
from django.urls import reverse

from ledger.models import Account, AccountKind, Original, Upload

# Synthetic bytes, invented for these tests. Digest and size were established
# independently with `shasum -a 256` and `wc -c`, not by the application.
FIXTURE = (
    b"%PDF-1.7\n"
    b"% synthetic lloyds current fixture\n"
    b"1 0 obj\n"
    b"<<>>\n"
    b"endobj\n"
    b"trailer\n"
    b"<<>>\n"
    b"%%EOF\n"
)
FIXTURE_SHA256 = "59353dc5157b272da4fa20bc691a16af66fd7a4772952edba876e657cfacbd2f"
FIXTURE_BYTES = 83


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

    def upload(self, data=FIXTURE, filename="statement.pdf", account=None):
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
        return [
            path
            for path in (self.data_dir / "originals").rglob("*")
            if path.is_file()
        ]


class PreservationTests(UploadSetupMixin, TestCase):
    def test_acceptance_stores_exact_bytes_and_receipt(self):
        response = self.upload()

        upload = Upload.objects.get()
        self.assertRedirects(
            response, reverse("ledger:upload_detail", args=[upload.pk])
        )
        self.assertEqual(upload.account, self.account)
        self.assertEqual(upload.filename, "statement.pdf")
        self.assertEqual(upload.status, Upload.Status.PENDING)
        self.assertEqual(upload.original.sha256, FIXTURE_SHA256)
        self.assertEqual(upload.original.byte_size, FIXTURE_BYTES)
        self.assertEqual(
            (self.data_dir / upload.original.stored_path).read_bytes(), FIXTURE
        )

    def test_receipt_is_listed_and_original_reopens_with_exact_bytes(self):
        self.upload()
        upload = Upload.objects.get()

        listing = self.client.get(reverse("ledger:uploads"))
        self.assertContains(listing, "statement.pdf")
        self.assertContains(listing, "Lloyds Current")

        original = self.client.get(
            reverse("ledger:upload_original", args=[upload.pk])
        )
        self.assertEqual(original.status_code, 200)
        self.assertEqual(original["Content-Type"], "application/pdf")
        self.assertEqual(b"".join(original.streaming_content), FIXTURE)

    def test_anonymous_visitors_cannot_read_receipts_or_originals(self):
        self.upload()
        upload = Upload.objects.get()
        self.client.logout()

        for url in (
            reverse("ledger:uploads"),
            reverse("ledger:upload_detail", args=[upload.pk]),
            reverse("ledger:upload_original", args=[upload.pk]),
        ):
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 302)
                self.assertTrue(response["Location"].startswith("/login/?next="))

    def test_identical_bytes_create_separate_receipts_with_own_account(self):
        savings = Account.objects.create(
            name="Revolut Savings", kind=AccountKind.SAVINGS
        )

        self.upload(filename="current.pdf")
        self.upload(filename="savings.pdf", account=savings)

        self.assertEqual(Original.objects.count(), 1)
        receipts = list(Upload.objects.order_by("pk"))
        self.assertEqual(len(receipts), 2)
        self.assertEqual(receipts[0].account, self.account)
        self.assertEqual(receipts[0].filename, "current.pdf")
        self.assertEqual(receipts[1].account, savings)
        self.assertEqual(receipts[1].filename, "savings.pdf")
        self.assertEqual(
            (self.data_dir / receipts[1].original.stored_path).read_bytes(), FIXTURE
        )


class StorageFailureTests(UploadSetupMixin, TestCase):
    def test_unavailable_local_storage_never_reports_success(self):
        # A real filesystem failure: the originals directory path is a file.
        (self.data_dir / "originals").write_bytes(b"not a directory")

        response = self.upload()

        self.assertEqual(response.status_code, 503)
        self.assertContains(response, "could not be preserved", status_code=503)
        self.assertEqual(Upload.objects.count(), 0)
        self.assertEqual(Original.objects.count(), 0)

    def test_missing_file_is_rejected_without_a_receipt(self):
        response = self.client.post(
            reverse("ledger:uploads"), {"account": self.account.pk}
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Choose a statement file")
        self.assertEqual(Upload.objects.count(), 0)


class RecordFailureTests(UploadSetupMixin, TransactionTestCase):
    """Fault injection between the storage write and the receipt insert."""

    class FailingReceiptInsert:
        def __call__(self, execute, sql, params, many, context):
            if sql.lstrip().upper().startswith('INSERT INTO "LEDGER_UPLOAD"'):
                raise OperationalError("simulated database failure")
            return execute(sql, params, many, context)

    def test_receipt_failure_reports_no_success_and_keeps_source_bytes(self):
        with connection.execute_wrapper(self.FailingReceiptInsert()):
            response = self.upload()

        self.assertEqual(response.status_code, 503)
        self.assertContains(response, "could not be recorded", status_code=503)
        self.assertEqual(Upload.objects.count(), 0)
        self.assertEqual(Original.objects.count(), 0)
        blobs = self.stored_blobs()
        self.assertEqual(len(blobs), 1)
        self.assertEqual(blobs[0].read_bytes(), FIXTURE)
