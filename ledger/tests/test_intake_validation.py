"""Behavioral tests for intake rejection, content checks and account identity."""

from django.test import TestCase
from django.urls import reverse

from ledger.models import Account, AccountKind, Upload
from ledger.tests.fixtures import BINARY_JUNK, CORRUPT_PDF, CSV_TEXT, blank_pdf, encrypted_pdf, text_pdf
from ledger.tests.support import UploadSetupMixin

TWENTY_MIB = 20 * 1024 * 1024


class RejectionTests(UploadSetupMixin, TestCase):
    def assert_rejected(self, response, message, status=400):
        self.assertEqual(response.status_code, status)
        self.assertContains(response, message, status_code=status)
        self.assertEqual(Upload.objects.count(), 0)
        self.assertEqual(self.stored_blobs(), [])

    def test_file_larger_than_twenty_mib_is_rejected(self):
        response = self.upload(b"a" * (TWENTY_MIB + 1), filename="huge.txt")

        self.assert_rejected(response, "larger than 20 MiB", status=413)

    def test_exactly_twenty_mib_is_accepted(self):
        response = self.upload(b"a" * TWENTY_MIB, filename="large.txt")

        self.assertEqual(response.status_code, 302)
        self.assertEqual(Upload.objects.count(), 1)

    def test_more_than_one_hundred_pdf_pages_is_rejected(self):
        response = self.upload(text_pdf(pages=101))

        self.assert_rejected(response, "more than 100 pages")

    def test_one_hundred_pdf_pages_is_accepted(self):
        response = self.upload(text_pdf(pages=100))

        self.assertEqual(response.status_code, 302)
        self.assertEqual(Upload.objects.count(), 1)

    def test_password_protected_pdf_is_rejected(self):
        response = self.upload(encrypted_pdf())

        self.assert_rejected(response, "password-protected")

    def test_damaged_pdf_is_rejected(self):
        response = self.upload(CORRUPT_PDF)

        self.assert_rejected(response, "damaged or unreadable")

    def test_image_only_pdf_is_rejected(self):
        response = self.upload(blank_pdf())

        self.assert_rejected(response, "no selectable text")

    def test_unknown_binary_content_is_rejected_by_content_not_extension(self):
        response = self.upload(BINARY_JUNK, filename="statement.pdf")

        self.assert_rejected(response, "file type is not supported")


class ContentOverExtensionTests(UploadSetupMixin, TestCase):
    def test_csv_content_named_pdf_is_treated_as_readable_text(self):
        response = self.upload(CSV_TEXT, filename="statement.pdf")

        self.assertEqual(response.status_code, 302)
        upload = Upload.objects.get()
        self.assertEqual(upload.status, Upload.Status.PENDING)

    def test_pdf_content_named_csv_is_still_read_as_a_pdf(self):
        response = self.upload(text_pdf(), filename="statement.csv")

        self.assertEqual(response.status_code, 302)
        self.assertEqual(Upload.objects.get().original.content_type, "application/pdf")


class PendingStatusTests(UploadSetupMixin, TestCase):
    def test_readable_upload_waits_for_interpretation_without_claiming_import(self):
        self.upload(CSV_TEXT, filename="export.txt")
        upload = Upload.objects.get()

        self.assertEqual(upload.status, Upload.Status.PENDING)
        detail = self.client.get(
            reverse("ledger:upload_detail", args=[upload.pk])
        )
        self.assertContains(detail, "Pending")
        self.assertNotContains(detail, "Imported")
        self.assertContains(detail, "Waiting for release")


class AccountSelectionTests(UploadSetupMixin, TestCase):
    def test_last_selected_account_is_remembered(self):
        savings = Account.objects.create(
            name="Revolut Savings", kind=AccountKind.SAVINGS
        )
        self.upload(CSV_TEXT, account=savings)

        page = self.client.get(reverse("ledger:uploads"))

        self.assertContains(page, f'value="{savings.pk}" selected')

    def test_identity_mismatch_is_visible_without_reassignment(self):
        savings = Account.objects.create(
            name="Revolut Savings", kind=AccountKind.SAVINGS
        )
        self.upload(CSV_TEXT, filename="personal.txt")
        response = self.upload(CSV_TEXT, filename="personal.txt", account=savings)

        second = Upload.objects.order_by("pk").last()
        self.assertRedirects(
            response, reverse("ledger:upload_detail", args=[second.pk])
        )
        self.assertEqual(second.account, savings)
        self.assertIn("Lloyds Current", second.review_note)
        detail = self.client.get(
            reverse("ledger:upload_detail", args=[second.pk])
        )
        self.assertContains(detail, "previously accepted for")
