"""Behavioral tests for the Revolut personal GBP slice."""

import json
from datetime import date

from django.test import TestCase
from django.urls import reverse

from interpretation.revolut import parse_pages
from jobs.models import WorkerCredential
from ledger.models import Account, AccountKind, Transaction, Upload
from ledger.tests.statement_fixtures import revolut_pages
from ledger.tests.support import UploadSetupMixin
from worker.client import build_result


class RevolutParsingTests(TestCase):
    def parse(self, include_savings=True):
        return parse_pages(revolut_pages(include_savings=include_savings))

    def test_personal_gbp_rows_keep_signed_amounts_and_running_balances(self):
        result = self.parse()

        self.assertTrue(result.recognised)
        self.assertTrue(result.reconciled, [issue.message for issue in result.issues])
        self.assertEqual(
            [
                (row.posted_on, row.description, row.transaction_type, row.amount_pence, row.balance_pence)
                for row in result.rows
            ],
            [
                (date(2026, 8, 5), "Uber Eats", "Merchant", -1240, 48760),
                (
                    date(2026, 8, 6),
                    "Transfer to Example Digital Assets Europe Ltd",
                    "Exchange",
                    -3000,
                    45760,
                ),
                (date(2026, 8, 10), "Exchanged to GBP", "Exchange", 2500, 48260),
                (date(2026, 8, 21), "HappyCow", "Merchant", -760, 47500),
            ],
        )
        self.assertEqual((result.opening_pence, result.closing_pence), (50000, 47500))
        self.assertEqual(
            [(balance.kind, balance.observed_on) for balance in result.balances],
            [("opening", date(2026, 8, 1)), ("closing", date(2026, 8, 31))],
        )

    def test_excluded_sections_are_named_and_savings_is_deferred(self):
        result = self.parse()

        self.assertEqual(
            [(section["name"], section["status"]) for section in result.excluded_sections],
            [
                ("personal_account_usd", "ignored"),
                ("joint_account_gbp", "ignored"),
                ("crypto", "ignored"),
                ("savings_account_gbp", "deferred"),
            ],
        )

    def test_foreign_and_joint_rows_never_become_gbp_transactions(self):
        result = self.parse()

        descriptions = [row.description for row in result.rows]
        self.assertNotIn("Foreign Purchase", descriptions)
        self.assertNotIn("Joint Shop", descriptions)
        self.assertEqual(len(result.rows), 4)

    def test_running_balance_disagreement_is_reported(self):
        pages = revolut_pages()
        pages[-3] = [
            (x, y, "£487.00" if (x, y, text) == (385, 564, "£487.60") else text)
            for x, y, text in pages[-3]
        ]

        result = parse_pages(pages)

        self.assertFalse(result.reconciled)
        self.assertIn("running_balance_mismatch", [issue.code for issue in result.issues])


class RevolutPublicationTests(UploadSetupMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.credential, self.token = WorkerCredential.issue("revolut-laptop")

    def api(self, name, payload, args=()):
        return self.client.post(
            reverse(name, args=args),
            data=json.dumps(payload) if payload else "",
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {self.token}",
        )

    def import_statement(self, include_savings=True, account=None):
        from django.core.files.uploadedfile import SimpleUploadedFile
        from ledger.tests.statement_fixtures import positioned_statement_pdf

        pdf = positioned_statement_pdf(revolut_pages(include_savings=include_savings))
        self.upload(pdf, filename="revolut.pdf", account=account or self.account)
        self.client.post(reverse("jobs:process_now"))
        claim = self.api("jobs:claim", None).json()
        parsed = parse_pages(revolut_pages(include_savings=include_savings))
        return self.api("jobs:result", build_result(claim, parsed), args=[claim["job"]])

    def test_personal_gbp_is_imported_and_savings_keeps_the_receipt_incomplete(self):
        response = self.import_statement()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["outcome"], "partial")
        upload = Upload.objects.get()
        self.assertEqual(upload.status, Upload.Status.NEEDS_REVIEW)
        self.assertEqual(
            list(Transaction.objects.values_list("description", flat=True)),
            ["Uber Eats", "Transfer to Example Digital Assets Europe Ltd", "Exchanged to GBP", "HappyCow"],
        )
        detail = self.client.get(reverse("ledger:upload_detail", args=[upload.pk]))
        self.assertContains(detail, "savings_account_gbp")
        self.assertContains(detail, "joint_account_gbp")

    def test_statement_without_savings_is_complete(self):
        response = self.import_statement(include_savings=False)

        self.assertEqual(response.json()["outcome"], "imported")
        self.assertEqual(Upload.objects.get().status, Upload.Status.IMPORTED)
        self.assertEqual(Transaction.objects.count(), 4)

    def test_revolut_statement_assigned_to_a_card_requests_review(self):
        card = Account.objects.create(name="Revolut Card", kind=AccountKind.CARD)

        response = self.import_statement(account=card)

        self.assertEqual(response.json()["outcome"], "failed")
        self.assertEqual(Transaction.objects.count(), 0)
