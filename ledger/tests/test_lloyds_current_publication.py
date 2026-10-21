"""Behavioral tests for Lloyds Current publication through the worker API."""

import json
import subprocess
from datetime import date
import sys
import tempfile
from pathlib import Path

from django.test import LiveServerTestCase, TestCase
from django.urls import reverse

from interpretation.lloyds_current import parse
from jobs.models import Job, WorkerCredential
from ledger.models import Account, AccountKind, BalanceObservation, Transaction, Upload
from ledger.tests.statement_fixtures import extract_text, lloyds_current_pdf
from ledger.tests.support import UploadSetupMixin
from worker.client import build_result

BASE_DIR = Path(__file__).resolve().parents[2]

EXPECTED_TRANSACTIONS = [
    ("2026-08-01", "COFFEE SHOP", "Card payment", -320, 119680),
    ("2026-08-02", "SALARY ACME LTD", "Bank credit", 250000, 369680),
    ("2026-08-03", "RENT PAYMENT", "DD", -95000, 274680),
    ("2026-08-04", "CORNER STORE", "Card payment", -1244, 273436),
    ("2026-08-05", "REFUND CORNER STORE", "Refund", 1244, 274680),
    ("2026-08-06", "CASH WITHDRAWAL", "Cash withdrawal", -10000, 264680),
]


class PublicationTestCase(UploadSetupMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.credential, self.token = WorkerCredential.issue("parser-laptop")

    def api(self, name, payload, args=()):
        return self.client.post(
            reverse(name, args=args),
            data=json.dumps(payload),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {self.token}",
        )

    def release_and_claim(self, filename="lloyds-current.pdf", account=None):
        self.upload(lloyds_current_pdf(), filename=filename, account=account)
        self.client.post(reverse("jobs:process_now"))
        response = self.api("jobs:claim", None)
        self.assertEqual(response.status_code, 200)
        return response.json()

    def payload(self, claim, pdf=None):
        pdf = pdf or lloyds_current_pdf()
        parsed = parse(extract_text(pdf))
        return build_result(claim, parsed)

    def submit(self, claim, payload):
        return self.api("jobs:result", payload, args=[claim["job"]])


class ImportTests(PublicationTestCase):
    def test_imported_result_commits_exact_transactions_and_balances(self):
        claim = self.release_and_claim()

        response = self.submit(claim, self.payload(claim))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["outcome"], "imported")
        upload = Upload.objects.get(filename="lloyds-current.pdf")
        self.assertEqual(upload.status, Upload.Status.IMPORTED)
        self.assertEqual(Job.objects.get().status, Job.Status.COMPLETED)
        self.assertEqual(
            list(
                Transaction.objects.order_by("posted_on").values_list(
                    "posted_on", "description", "transaction_type", "amount_pence", "balance_pence"
                )
            ),
            [(date.fromisoformat(day), *rest) for day, *rest in EXPECTED_TRANSACTIONS],
        )
        self.assertEqual(
            list(
                BalanceObservation.objects.order_by("kind").values_list(
                    "kind", "observed_on", "amount_pence"
                )
            ),
            [
                ("closing", date(2026, 8, 31), 264680),
                ("opening", date(2026, 8, 1), 120000),
            ],
        )

    def test_transaction_page_shows_rows_and_reaches_the_original(self):
        claim = self.release_and_claim()
        self.submit(claim, self.payload(claim))
        upload = Upload.objects.get()

        page = self.client.get(
            reverse("ledger:account_transactions", args=[self.account.pk])
        )

        self.assertContains(page, "SALARY ACME LTD")
        self.assertContains(page, "£2,500.00")
        self.assertContains(page, "£1,196.80")
        self.assertContains(page, "page 1")
        self.assertContains(page, reverse("ledger:upload_original", args=[upload.pk]))

    def test_repeated_identical_submission_adds_no_extra_effects(self):
        claim = self.release_and_claim()
        payload = self.payload(claim)

        self.submit(claim, payload)
        self.submit(claim, payload)

        self.assertEqual(Transaction.objects.count(), 6)
        self.assertEqual(BalanceObservation.objects.count(), 2)


class RejectionTests(PublicationTestCase):
    def test_server_rejects_reconciliation_failure_and_requests_review(self):
        claim = self.release_and_claim()
        payload = self.payload(claim)
        payload["sections"][0]["transactions"][0]["amount_pence"] = -999

        response = self.submit(claim, payload)

        self.assertEqual(response.status_code, 200)
        upload = Upload.objects.get()
        self.assertEqual(upload.status, Upload.Status.NEEDS_REVIEW)
        self.assertEqual(Transaction.objects.count(), 0)
        detail = self.client.get(reverse("ledger:upload_detail", args=[upload.pk]))
        self.assertContains(detail, "running_balance_mismatch")

    def test_amount_tampering_that_preserves_the_sum_is_still_rejected(self):
        claim = self.release_and_claim()
        payload = self.payload(claim)
        rows = payload["sections"][0]["transactions"]
        rows[0]["amount_pence"] = 320
        rows[1]["amount_pence"] = 249360

        response = self.submit(claim, payload)

        self.assertEqual(response.json()["outcome"], "failed")
        self.assertEqual(Upload.objects.get().status, Upload.Status.NEEDS_REVIEW)
        self.assertEqual(Transaction.objects.count(), 0)
        stored = __import__("jobs.models", fromlist=["JobResult"]).JobResult.objects.get()
        self.assertEqual(stored.outcome, "failed")

    def test_missing_balance_anchors_are_rejected(self):
        claim = self.release_and_claim()
        payload = self.payload(claim)
        payload["sections"][0]["balances"] = []

        self.submit(claim, payload)

        upload = Upload.objects.get()
        self.assertEqual(upload.status, Upload.Status.NEEDS_REVIEW)
        self.assertEqual(Transaction.objects.count(), 0)
        detail = self.client.get(reverse("ledger:upload_detail", args=[upload.pk]))
        self.assertContains(detail, "missing_balance_anchor")

    def test_account_identity_mismatch_is_visible_and_commits_nothing(self):
        card = Account.objects.create(name="Lloyds Credit", kind=AccountKind.CARD)
        claim = self.release_and_claim(filename="lloyds-credit-card.pdf", account=card)

        response = self.submit(claim, self.payload(claim))

        self.assertEqual(response.status_code, 200)
        upload = Upload.objects.get(filename="lloyds-credit-card.pdf")
        self.assertEqual(upload.account, card)
        self.assertEqual(upload.status, Upload.Status.NEEDS_REVIEW)
        self.assertEqual(Transaction.objects.count(), 0)
        detail = self.client.get(reverse("ledger:upload_detail", args=[upload.pk]))
        self.assertContains(detail, "account_identity_mismatch")
        self.assertContains(detail, "Outcome: failed")
        self.assertContains(detail, "Needs review")

    def test_duplicate_source_location_is_rejected(self):
        claim = self.release_and_claim()
        payload = self.payload(claim)
        payload["sections"][0]["transactions"][1]["page"] = 1
        payload["sections"][0]["transactions"][1]["row"] = 1

        self.submit(claim, payload)

        self.assertEqual(Upload.objects.get().status, Upload.Status.NEEDS_REVIEW)
        self.assertEqual(Transaction.objects.count(), 0)

    def test_non_integer_amounts_are_rejected_before_recording(self):
        claim = self.release_and_claim()
        payload = self.payload(claim)
        payload["sections"][0]["transactions"][0]["amount_pence"] = "3.20"

        response = self.submit(claim, payload)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(Transaction.objects.count(), 0)
        self.assertEqual(Upload.objects.get().status, Upload.Status.PENDING)


class WorkerInterpretationTests(UploadSetupMixin, LiveServerTestCase):
    def test_worker_imports_a_lloyds_current_statement_end_to_end(self):
        self.upload(lloyds_current_pdf(), filename="lloyds-current.pdf")
        upload = Upload.objects.get(filename="lloyds-current.pdf")
        self.client.post(reverse("jobs:process_now"))
        _credential, token = WorkerCredential.issue("e2e-laptop")
        work_root = Path(tempfile.mkdtemp())
        self.addCleanup(lambda: __import__("shutil").rmtree(work_root, ignore_errors=True))

        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "worker",
                "--base-url",
                self.live_server_url,
                "--token",
                token,
                "--work-root",
                str(work_root),
            ],
            cwd=BASE_DIR,
            capture_output=True,
            text=True,
            timeout=120,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("imported", completed.stdout)
        self.assertEqual(Transaction.objects.count(), 6)
        self.assertEqual(Upload.objects.get(pk=upload.pk).status, Upload.Status.IMPORTED)
        self.assertEqual(list(work_root.iterdir()), [])
