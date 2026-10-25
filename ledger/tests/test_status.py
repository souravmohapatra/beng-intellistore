"""Behavioral tests for the operational status page."""

import json
import tempfile
from pathlib import Path

from django.test import Client, TestCase, override_settings
from django.urls import reverse

from jobs.models import AdviceRequest, Job
from ledger.models import Transaction, Upload
from ledger.tests.fixtures import text_pdf
from ledger.tests.support import UploadSetupMixin


class StatusPageTests(UploadSetupMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.status_dir = Path(tempfile.mkdtemp())
        self.status_file = self.status_dir / "backup.json"
        self.success_file = self.status_dir / "backup-last-success.json"
        self.override = override_settings(
            BACKUP_STATUS_FILE=str(self.status_file),
            BACKUP_LAST_SUCCESS_FILE=str(self.success_file),
        )
        self.override.enable()
        self.addCleanup(self.override.disable)
        self.addCleanup(
            lambda: __import__("shutil").rmtree(self.status_dir, ignore_errors=True)
        )

    def test_requires_login(self):
        response = Client().get(reverse("ledger:status"))
        self.assertEqual(response.status_code, 302)

    def test_absent_backup_status_is_stated_honestly(self):
        response = self.client.get(reverse("ledger:status"))
        self.assertContains(response, "No backup outcome recorded")
        self.assertContains(response, "No completed processing yet")
        self.assertContains(response, "No suggestion recorded")
        self.assertNotContains(response, "All systems normal")

    def test_failed_backup_and_advice_are_visible_with_next_action(self):
        self.status_file.parent.mkdir(parents=True, exist_ok=True)
        self.status_file.write_text(
            json.dumps(
                {
                    "status": "failed",
                    "finished_at": "20260101T030000Z",
                    "generation": "",
                    "message": "destination unavailable",
                }
            )
        )
        self.upload(text_pdf(), filename="status.pdf")
        receipt = Upload.objects.get(filename="status.pdf")
        Transaction.objects.create(
            account=self.account,
            upload=receipt,
            posted_on="2026-08-09",
            description="TO SOMEONE",
            transaction_type="Others",
            amount_pence=-500,
            balance_pence=None,
            source_page=1,
            source_row=1,
            source_text="TO SOMEONE",
        )
        AdviceRequest.objects.create(
            transaction=Transaction.objects.get(), status=AdviceRequest.Status.FAILED
        )
        Job.objects.filter(upload=receipt).update(status=Job.Status.FAILED)

        response = self.client.get(reverse("ledger:status"))

        self.assertContains(response, "destination unavailable")
        self.assertContains(response, "Local data is untouched")
        self.assertContains(response, "Some advice requests exhausted their attempts")
        self.assertContains(response, "Some processing failed")
        self.assertContains(response, "1 upload(s)", count=1)

    def test_failed_attempt_retains_the_previous_success(self):
        self.status_file.parent.mkdir(parents=True, exist_ok=True)
        self.status_file.write_text(
            json.dumps(
                {
                    "status": "failed",
                    "finished_at": "20260102T030000Z",
                    "generation": "",
                    "message": "destination unavailable",
                }
            )
        )
        self.success_file.write_text(
            json.dumps(
                {
                    "status": "success",
                    "finished_at": "20260101T030000Z",
                    "generation": "/backup/generation-20260101T030000Z",
                    "message": "",
                }
            )
        )

        response = self.client.get(reverse("ledger:status"))

        self.assertContains(response, "destination unavailable")
        self.assertContains(response, "20260101T030000Z")
        self.assertContains(response, "generation-20260101T030000Z")
        self.assertNotContains(response, "None recorded")

    def test_failure_without_a_success_states_the_window_is_unestablished(self):
        self.status_file.parent.mkdir(parents=True, exist_ok=True)
        self.status_file.write_text(
            json.dumps({"status": "failed", "finished_at": "x", "message": "down"})
        )

        response = self.client.get(reverse("ledger:status"))

        self.assertContains(response, "None recorded")
        self.assertContains(response, "recovery window is not yet established")

    def test_successful_backup_reports_generation(self):
        self.status_file.parent.mkdir(parents=True, exist_ok=True)
        self.status_file.write_text(
            json.dumps(
                {
                    "status": "success",
                    "finished_at": "20260101T030000Z",
                    "generation": "/backup/generation-20260101T030000Z",
                    "message": "",
                }
            )
        )

        response = self.client.get(reverse("ledger:status"))

        self.assertContains(response, "generation-20260101T030000Z")
        self.assertContains(response, "success")
        self.assertNotContains(response, "Backup failed")

    def test_corrupt_status_file_is_treated_as_absent(self):
        self.status_file.parent.mkdir(parents=True, exist_ok=True)
        self.status_file.write_text("{not-json")

        response = self.client.get(reverse("ledger:status"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No backup outcome recorded")
