"""Behavioral tests for Lloyds Credit interpretation and publication."""

import json
from datetime import date

from django.test import TestCase
from django.urls import reverse

from interpretation.lloyds_credit import parse
from jobs.models import WorkerCredential
from ledger.models import Account, AccountKind, BalanceObservation, Transaction, Upload
from ledger.tests.statement_fixtures import (
    extract_text,
    lloyds_credit_pdf,
    lloyds_credit_text,
    lloyds_credit_year_boundary_pages,
)
from ledger.tests.support import UploadSetupMixin
from worker.client import build_result

CREDITS_ACCOUNT = AccountKind.CARD


def text_with(*replacements: tuple[str, str]) -> str:
    text = lloyds_credit_text()
    for old, new in replacements:
        assert old in text, old
        text = text.replace(old, new, 1)
    return text


class CreditParsingTests(TestCase):
    def test_rows_use_the_date_entered_and_keep_the_purchase_date(self):
        result = parse(lloyds_credit_text())

        self.assertTrue(result.recognised)
        self.assertTrue(result.reconciled, [issue.message for issue in result.issues])
        self.assertEqual(
            [
                (row.posted_on, row.transaction_date, row.description, row.amount_pence)
                for row in result.rows
            ],
            [
                (date(2026, 7, 30), date(2026, 7, 30), "DIRECT DEBIT PAYMENT - THANK YOU", -40000),
                (date(2026, 7, 6), date(2026, 7, 3), "COFFEE HOUSE GB", 2100),
                (date(2026, 7, 6), date(2026, 7, 4), "SUPERMARKET LONDON GB", 3350),
                (date(2026, 7, 6), date(2026, 7, 4), "NON-STERLING PURCHASE FEE", 75),
                (date(2026, 7, 20), date(2026, 7, 17), "CAFE STOCKHOLM SE", 12000),
                (date(2026, 7, 22), date(2026, 7, 21), "RESTAURANT STOCKHOLM SE", 6400),
                (date(2026, 8, 3), date(2026, 8, 2), "ELECTRONICS LONDON GB", 62075),
            ],
        )
        self.assertEqual((result.opening_pence, result.closing_pence), (40000, 86000))
        self.assertEqual((result.credits_pence, result.debits_pence), (40000, 86000))

    def test_fx_continuations_are_annotations_not_extra_rows(self):
        result = parse(lloyds_credit_text())

        self.assertEqual(len(result.rows), 7)
        self.assertNotIn("SEK", [row.description for row in result.rows])

    def test_payment_due_text_does_not_become_a_payment(self):
        result = parse(lloyds_credit_text())

        self.assertNotIn(
            "01 September 2026", [row.description for row in result.rows]
        )
        self.assertEqual(
            [row for row in result.rows if row.amount_pence < 0][0].description,
            "DIRECT DEBIT PAYMENT - THANK YOU",
        )

    def test_year_is_inferred_across_a_year_boundary(self):
        pages = lloyds_credit_year_boundary_pages()
        result = parse("\f".join("\n".join(page) for page in pages))

        self.assertTrue(result.reconciled, [issue.message for issue in result.issues])
        self.assertEqual(
            [(row.transaction_date, row.posted_on) for row in result.rows],
            [(date(2026, 12, 30), date(2026, 12, 31)), (date(2027, 1, 2), date(2027, 1, 4))],
        )

    def test_missing_statement_date_makes_year_context_ambiguous(self):
        result = parse(text_with(("07 September 2026\n", "")))

        self.assertFalse(result.reconciled)
        self.assertIn("missing_statement_date", [issue.code for issue in result.issues])

    def test_debt_equation_failure_is_reported(self):
        result = parse(text_with(("New balance              860.00", "New balance              840.00")))

        self.assertFalse(result.reconciled)
        self.assertIn("closing_balance_mismatch", [issue.code for issue in result.issues])

    def test_pdf_extraction_reaches_the_same_rows(self):
        from_pdf = parse(extract_text(lloyds_credit_pdf()))

        self.assertEqual(len(from_pdf.rows), 7)
        self.assertTrue(from_pdf.reconciled)


class CreditPublicationTests(UploadSetupMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.card = Account.objects.create(name="Lloyds Credit", kind=CREDITS_ACCOUNT)
        self.credential, self.token = WorkerCredential.issue("credit-laptop")

    def api(self, name, payload, args=()):
        return self.client.post(
            reverse(name, args=args),
            data=json.dumps(payload) if payload else "",
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {self.token}",
        )

    def import_statement(self, account=None):
        self.upload(lloyds_credit_pdf(), filename="lloyds-credit.pdf", account=account or self.card)
        self.client.post(reverse("jobs:process_now"))
        claim = self.api("jobs:claim", None).json()
        parsed = parse(extract_text(lloyds_credit_pdf()))
        return self.api("jobs:result", build_result(claim, parsed), args=[claim["job"]])

    def test_card_statement_imports_debt_movements_and_keeps_both_dates(self):
        response = self.import_statement()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["outcome"], "imported")
        upload = Upload.objects.get()
        self.assertEqual(upload.status, Upload.Status.IMPORTED)
        self.assertEqual(Transaction.objects.count(), 7)
        self.assertEqual(
            list(
                Transaction.objects.order_by("posted_on", "pk").values_list(
                    "posted_on", "source_transaction_date", "amount_pence"
                )
            )[:2],
            [
                (date(2026, 7, 6), date(2026, 7, 3), 2100),
                (date(2026, 7, 6), date(2026, 7, 4), 3350),
            ],
        )
        self.assertEqual(
            list(
                BalanceObservation.objects.order_by("kind").values_list(
                    "kind", "amount_pence", "observed_on"
                )
            ),
            [("closing", 86000, date(2026, 9, 7)), ("opening", 40000, None)],
        )
        page = self.client.get(reverse("ledger:account_transactions", args=[self.card.pk]))
        self.assertContains(page, "NON-STERLING PURCHASE FEE")
        self.assertContains(page, "For credit cards")
        self.assertContains(page, "(date unknown)")

    def test_card_statement_assigned_to_a_current_account_requests_review(self):
        response = self.import_statement(account=self.account)

        self.assertEqual(response.json()["outcome"], "failed")
        self.assertEqual(Upload.objects.get().status, Upload.Status.NEEDS_REVIEW)
        self.assertEqual(Transaction.objects.count(), 0)
