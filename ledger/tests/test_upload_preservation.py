"""Behavioral tests for durable original preservation and retrieval."""

from pathlib import Path

from django.db import OperationalError, connection
from django.test import TestCase, TransactionTestCase
from django.urls import reverse

from ledger.models import Account, AccountKind, Original, Upload
from ledger.tests.fixtures import text_pdf
from ledger.tests.support import UploadSetupMixin

# A valid PDF with selectable text. Digest and size were established outside the
# application with `shasum -a 256` and `wc -c`.
FIXTURE = text_pdf()
FIXTURE_SHA256 = "b4d0614ed0c91f71d89b2131562dbca7016bdc58cdfdf99820b57be2bd8764ba"
FIXTURE_BYTES = 590


class PreservationTests(UploadSetupMixin, TestCase):
    def test_acceptance_stores_exact_bytes_and_receipt(self):
        response = self.upload(FIXTURE)

        upload = Upload.objects.get()
        self.assertRedirects(
            response, reverse("ledger:upload_detail", args=[upload.pk])
        )
        self.assertEqual(upload.account, self.account)
        self.assertEqual(upload.filename, "statement.pdf")
        self.assertEqual(upload.status, Upload.Status.UNSUPPORTED)
        self.assertEqual(upload.original.sha256, FIXTURE_SHA256)
        self.assertEqual(upload.original.byte_size, FIXTURE_BYTES)
        self.assertEqual(
            (self.data_dir / upload.original.stored_path).read_bytes(), FIXTURE
        )

    def test_receipt_is_listed_and_original_reopens_with_exact_bytes(self):
        self.upload(FIXTURE)
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
        self.upload(FIXTURE)
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

        self.upload(FIXTURE, filename="current.pdf")
        self.upload(FIXTURE, filename="savings.pdf", account=savings)

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

        response = self.upload(FIXTURE)

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
            response = self.upload(FIXTURE)

        self.assertEqual(response.status_code, 503)
        self.assertContains(response, "could not be recorded", status_code=503)
        self.assertEqual(Upload.objects.count(), 0)
        self.assertEqual(Original.objects.count(), 0)
        blobs = self.stored_blobs()
        self.assertEqual(len(blobs), 1)
        self.assertEqual(blobs[0].read_bytes(), FIXTURE)
