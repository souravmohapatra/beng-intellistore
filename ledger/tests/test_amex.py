"""Behavioral tests for Amex interpretation and publication."""

import json
from datetime import date

from django.test import TestCase
from django.urls import reverse

from interpretation.amex import parse_pages
from jobs.models import WorkerCredential
from ledger.models import Account, AccountKind, Transaction, Upload
from ledger.tests.statement_fixtures import amex_pages, amex_pdf, extract_positioned_token_pages
from ledger.tests.support import UploadSetupMixin
from worker.client import build_result


class AmexParsingTests(TestCase):
    def parse(self):
        return parse_pages(amex_pages())

    def test_monthly_rows_use_process_dates_and_keep_transaction_dates(self):
        result = self.parse()

        self.assertTrue(result.recognised)
        self.assertTrue(result.reconciled, [issue.message for issue in result.issues])
        self.assertEqual(
            [
                (row.transaction_date, row.posted_on, row.description, row.amount_pence)
                for row in result.rows
            ],
            [
                (date(2026, 8, 22), date(2026, 8, 22), "PAYMENT RECEIVED - THANK YOU", -10000),
                (date(2026, 8, 15), date(2026, 8, 15), "COFFEE MERCHANT LONDON", 1200),
                (date(2026, 8, 15), date(2026, 8, 15), "BOOK STORE LONDON", 3000),
                (date(2026, 8, 21), date(2026, 8, 21), "TRAVEL SITE INTERNET", 50025),
                (date(2026, 8, 27), date(2026, 8, 28), "AIRPORT TRANSFER LONDON", 10000),
            ],
        )
        self.assertEqual((result.opening_pence, result.closing_pence), (30000, 84225))
        self.assertEqual((result.payments_and_credits_pence, result.debits_pence), (10000, 64225))

    def test_credit_marker_on_the_following_line_reduces_debt(self):
        result = self.parse()

        payment = result.rows[0]
        self.assertEqual(payment.amount_pence, -10000)
        self.assertIn("CR", payment.source_text)

    def test_annual_summary_is_not_transactions_or_a_monthly_balance(self):
        result = self.parse()

        self.assertEqual(Transaction_count := len(result.rows), 5)
        self.assertNotIn(
            "Total debits for the year", [row.description for row in result.rows]
        )
        self.assertEqual(result.closing_pence, 84225)

    def test_fx_and_exchange_rate_fragments_are_annotations(self):
        result = self.parse()

        descriptions = [row.description for row in result.rows]
        self.assertNotIn("Exchange Rate 1.2345", descriptions)
        self.assertNotIn("Nonsterling Transaction Fee 1.50", descriptions)
        self.assertEqual(len(result.rows), 5)

    def test_pdf_tokens_reconstruct_the_same_rows(self):
        from_pdf = parse_pages(extract_positioned_token_pages(amex_pdf()))

        self.assertTrue(from_pdf.reconciled)
        self.assertEqual(len(from_pdf.rows), 5)
        self.assertEqual(from_pdf.rows[-1].posted_on, date(2026, 8, 28))


class AmexPublicationTests(UploadSetupMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.card = Account.objects.create(name="Amex Credit", kind=AccountKind.CARD)
        self.credential, self.token = WorkerCredential.issue("amex-laptop")

    def api(self, name, payload, args=()):
        return self.client.post(
            reverse(name, args=args),
            data=json.dumps(payload) if payload else "",
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {self.token}",
        )

    def import_statement(self, account=None):
        self.upload(amex_pdf(), filename="amex.pdf", account=account or self.card)
        self.client.post(reverse("jobs:process_now"))
        claim = self.api("jobs:claim", None).json()
        parsed = parse_pages(amex_pages())
        return self.api("jobs:result", build_result(claim, parsed), args=[claim["job"]])

    def test_amex_statement_imports_billed_rows_with_process_dates(self):
        response = self.import_statement()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["outcome"], "imported")
        upload = Upload.objects.get()
        self.assertEqual(upload.status, Upload.Status.IMPORTED)
        self.assertEqual(Transaction.objects.count(), 5)
        self.assertEqual(
            list(
                Transaction.objects.order_by("pk").values_list(
                    "posted_on", "source_transaction_date", "amount_pence"
                )
            )[-1],
            (date(2026, 8, 28), date(2026, 8, 27), 10000),
        )

    def test_amex_statement_assigned_to_current_account_requests_review(self):
        response = self.import_statement(account=self.account)

        self.assertEqual(response.json()["outcome"], "failed")
        self.assertEqual(Upload.objects.get().status, Upload.Status.NEEDS_REVIEW)
        self.assertEqual(Transaction.objects.count(), 0)
