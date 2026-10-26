"""Behavioral tests for Amex interpretation and publication."""

import json
from datetime import date

from django.test import TestCase
from django.urls import reverse

from interpretation.amex import parse_pages
from jobs.models import WorkerCredential
from ledger.models import Account, AccountKind, Transaction, Upload
from ledger.tests.statement_fixtures import (
    amex_pages,
    amex_pdf,
    extract_positioned_token_pages,
    positioned_statement_pdf,
)
from ledger.tests.support import UploadSetupMixin
from worker.client import build_result


def amex_summary_pages() -> list[list[tuple[float, float, str]]]:
    """Sanitized Amex statement in the account-summary-box layout.

    The cover reads the whole box across one arithmetic line: previous closing
    balance - new credits + new debits = closing balance. Transaction rows keep
    the two-date, process-date-reported shape; the annual page must be ignored.
    Amounts are synthetic and internally consistent: 500.00 - 200.00 + 350.00 =
    650.00, with the 350.00 of debits split across two rows and the 200.00
    credit on a repayment row marked ``CR``.
    """
    cover = [
        (14.4, 749.3, "Statement of Account Page 1 of 2"),
        (14.4, 695.8, "Prepared for Membership Number Date"),
        (14.4, 685.0, "TEST CARDHOLDER xxxx-xxxxxx-99999 10 / 09 / 26"),
        (65.3, 642.0, "Previous Closing Balance"),
        (197.0, 642.0, "New Credits"),
        (295.4, 642.0, "New Debits"),
        (379.0, 642.0, "Closing Balance"),
        (97.4, 623.8, "£"),
        (103.4, 623.8, "500.00"),
        (143.3, 623.8, "-"),
        (193.4, 623.8, "£"),
        (199.4, 623.8, "200.00"),
        (235.2, 623.8, "+"),
        (288.0, 623.8, "£"),
        (294.0, 623.8, "350.00"),
        (333.4, 623.8, "="),
        (382.3, 623.8, "£"),
        (388.3, 623.8, "650.00"),
    ]

    def row(y: float, day: str, description: str, amount: str, credit: bool = False):
        tokens = [
            (14.4, y, "Aug"),
            (32.6, y, day),
            (57.6, y, "Aug"),
            (75.8, y, day),
            (100.8, y, description),
            (504.2, y - 0.7, amount),
        ]
        if credit:
            tokens.append((518.9, y - 13.0, "CR"))
        return tokens

    table = [
        (14.4, 529.2, "Transaction"),
        (57.6, 529.2, "Process"),
        (14.4, 521.3, "Date"),
        (57.6, 521.3, "Date"),
        (100.8, 521.3, "Transaction Details"),
        (504.2, 519.6, "Amount £"),
    ]
    table += row(502.6, "22", "PAYMENT RECEIVED - THANK YOU", "200.00", credit=True)
    table += row(471.1, "11", "SHOP ONE LONDON", "150.00")
    table += row(451.9, "15", "CAFE TWO LONDON", "200.00")

    annual = [
        (14.4, 792.7, "Annual Credit Card Statement"),
        (14.4, 611.5, "For the period: 20 August 2025 to 10 September 2026"),
        (36.0, 566.9, "Total Spending £ 999.00"),
        (36.0, 534.5, "Total Amount Repaid (1) £ 300.00 CR"),
        (36.0, 475.7, "Purchases Transactions (2) £ 999.00"),
    ]
    return [cover, table, annual]


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

    def test_process_date_before_purchase_is_rejected(self):
        pages = amex_pages()
        pages[1] = [
            (x, y, "26" if (x, y, text) == (75.8, 413.5, "28") else text)
            for x, y, text in pages[1]
        ]

        result = parse_pages(pages)

        self.assertFalse(result.reconciled)
        self.assertIn("implausible_dates", [issue.code for issue in result.issues])

    def test_a_reference_date_cannot_become_the_statement_date(self):
        pages = amex_pages()
        pages[0] = [
            (x, y, text)
            for x, y, text in pages[0]
            if not (text in {"10", "/", "09", "26"} and y == 716.4)
        ]
        pages[1].append((100.8, 400.0, "REFERENCE 01/10/27"))

        result = parse_pages(pages)

        self.assertFalse(result.reconciled)
        self.assertIn("missing_statement_date", [issue.code for issue in result.issues])

    def test_contradictory_balance_anchors_are_reported(self):
        pages = amex_pages()
        pages[0].append((14.4, 610.0, "New Balance"))
        pages[0].append((400.0, 610.0, "£"))
        pages[0].append((415.0, 610.0, "900.00"))

        result = parse_pages(pages)

        self.assertFalse(result.reconciled)
        self.assertIn("contradictory_balance_anchor", [issue.code for issue in result.issues])

    def test_description_continuation_is_kept(self):
        pages = amex_pages()
        pages[1].append((100.8, 460.0, "ORDER REFERENCE ABC123"))

        result = parse_pages(pages)

        self.assertTrue(result.reconciled, [issue.message for issue in result.issues])
        self.assertIn("ORDER REFERENCE ABC123", result.rows[1].description)

    def test_credit_marker_is_found_across_a_continuation_line(self):
        pages = amex_pages()
        pages[1] = [
            (x, y, "100.00" if (x, y, text) == (504.2, 502.6, "100.00") else text)
            for x, y, text in pages[1]
        ]
        pages[1].append((100.8, 495.0, "PAYMENT REFERENCE XYZ"))

        result = parse_pages(pages)

        self.assertEqual(result.rows[0].amount_pence, -10000)
        self.assertIn("PAYMENT REFERENCE XYZ", result.rows[0].description)

    def test_pdf_tokens_reconstruct_the_same_rows(self):
        from_pdf = parse_pages(extract_positioned_token_pages(amex_pdf()))

        self.assertTrue(from_pdf.reconciled)
        self.assertEqual(len(from_pdf.rows), 5)
        self.assertEqual(from_pdf.rows[-1].posted_on, date(2026, 8, 28))

    def test_account_summary_box_supplies_balances_and_credit_total(self):
        result = parse_pages(amex_summary_pages())

        self.assertTrue(result.reconciled, [issue.message for issue in result.issues])
        self.assertEqual(
            (
                result.opening_pence,
                result.closing_pence,
                result.payments_and_credits_pence,
                result.debits_pence,
                result.stated_debits_pence,
            ),
            (50000, 65000, 20000, 35000, 35000),
        )

    def test_account_summary_rows_keep_dates_signs_and_amounts(self):
        result = parse_pages(amex_summary_pages())

        self.assertEqual(len(result.rows), 3)
        self.assertEqual(
            [(row.posted_on, row.amount_pence) for row in result.rows],
            [
                (date(2026, 8, 22), -20000),
                (date(2026, 8, 11), 15000),
                (date(2026, 8, 15), 20000),
            ],
        )

    def test_annual_summary_page_in_summary_layout_is_excluded(self):
        result = parse_pages(amex_summary_pages())

        descriptions = [row.description for row in result.rows]
        self.assertNotIn("Total Amount Repaid (1) £ 300.00 CR", descriptions)
        self.assertEqual(len(result.rows), 3)
        self.assertEqual([anchor.kind for anchor in result.balances], ["opening", "closing"])

    def test_missing_account_summary_still_reports_missing_anchors(self):
        pages = amex_summary_pages()
        pages[0] = [token for token in pages[0] if token[1] != 623.8]

        result = parse_pages(pages)

        self.assertFalse(result.reconciled)
        codes = {issue.code for issue in result.issues}
        self.assertIn("missing_opening_balance", codes)
        self.assertIn("missing_closing_balance", codes)
        self.assertIn("missing_payments_summary", codes)

    def test_summary_box_debit_total_must_match_the_transaction_rows(self):
        pages = amex_summary_pages()
        pages[0] = [
            (x, y, "351.00") if (x, y, text) == (294.0, 623.8, "350.00") else (x, y, text)
            for x, y, text in pages[0]
        ]

        result = parse_pages(pages)

        self.assertFalse(result.reconciled)
        self.assertIn("debit_totals_mismatch", [issue.code for issue in result.issues])
        self.assertEqual(result.stated_debits_pence, 35100)
        self.assertEqual(result.debits_pence, 35000)

    def test_a_repeated_different_summary_debit_total_is_contradictory(self):
        pages = amex_summary_pages()
        pages[0] += [
            (97.4, 600.0, "£"),
            (103.4, 600.0, "500.00"),
            (143.3, 600.0, "-"),
            (193.4, 600.0, "£"),
            (199.4, 600.0, "200.00"),
            (235.2, 600.0, "+"),
            (288.0, 600.0, "£"),
            (294.0, 600.0, "350.01"),
            (333.4, 600.0, "="),
            (382.3, 600.0, "£"),
            (388.3, 600.0, "650.00"),
        ]

        result = parse_pages(pages)

        self.assertFalse(result.reconciled)
        self.assertIn("contradictory_debit_summary", [issue.code for issue in result.issues])

    def test_summary_layout_pdf_tokens_reconstruct_the_same_result(self):
        from_pdf = parse_pages(
            extract_positioned_token_pages(positioned_statement_pdf(amex_summary_pages()))
        )

        self.assertTrue(from_pdf.reconciled, [issue.message for issue in from_pdf.issues])
        self.assertEqual(len(from_pdf.rows), 3)
        self.assertEqual(
            (from_pdf.opening_pence, from_pdf.closing_pence), (50000, 65000)
        )


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
