"""Behavioral tests for posting-period reporting totals."""

from datetime import date

from django.test import TestCase

from ledger.models import Account, AccountKind, BalanceObservation, Transaction, Upload
from reporting.totals import compute_totals


def make_upload(account: Account, filename: str) -> Upload:
    from ledger.models import Original

    original = Original.objects.create(
        sha256=f"{filename:0<64}"[:64],
        byte_size=1,
        content_type="application/pdf",
        stored_path=f"originals/{filename}",
    )
    return Upload.objects.create(original=original, account=account, filename=filename)


def add(account, upload, day, description, transaction_type, amount):
    return Transaction.objects.create(
        account=account,
        upload=upload,
        posted_on=day,
        description=description,
        transaction_type=transaction_type,
        amount_pence=amount,
        balance_pence=None,
        source_page=1,
        source_row=Transaction.objects.filter(upload=upload).count() + 1,
        source_text="fixture",
    )


class TotalsTests(TestCase):
    def setUp(self):
        self.current = Account.objects.create(name="Current", kind=AccountKind.CURRENT)
        self.card = Account.objects.create(name="Card", kind=AccountKind.CARD)
        self.savings = Account.objects.create(name="Savings", kind=AccountKind.SAVINGS)
        self.upload_current = make_upload(self.current, "c")
        self.upload_card = make_upload(self.card, "d")
        self.upload_savings = make_upload(self.savings, "e")

        add(self.current, self.upload_current, date(2026, 8, 1), "SALARY ACME", "Salary", 250000)
        add(self.current, self.upload_current, date(2026, 8, 2), "RENT", "DD", -95000)
        add(self.current, self.upload_current, date(2026, 8, 3), "CASH", "Cash withdrawal", -10000)
        add(self.current, self.upload_current, date(2026, 8, 4), "REFUND", "Refund", 1244)
        add(self.card, self.upload_card, date(2026, 8, 5), "SHOP", "", 5000)
        add(self.card, self.upload_card, date(2026, 8, 6), "DIRECT DEBIT PAYMENT - THANK YOU", "", -5000)
        add(self.savings, self.upload_savings, date(2026, 8, 7), "Gross Interest", "Interest", 10)

    def balances(self):
        BalanceObservation.objects.create(
            account=self.current, upload=self.upload_current, kind="closing",
            observed_on=date(2026, 8, 31), amount_pence=300000,
        )
        BalanceObservation.objects.create(
            account=self.card, upload=self.upload_card, kind="closing",
            observed_on=date(2026, 8, 31), amount_pence=2000,
        )
        BalanceObservation.objects.create(
            account=self.savings, upload=self.upload_savings, kind="closing",
            observed_on=date(2026, 8, 31), amount_pence=25030,
        )

    def test_posting_period_totals_follow_the_agreed_semantics(self):
        report = compute_totals(date(2026, 8, 1), date(2026, 8, 31))

        self.assertEqual(report.spending_pence, 108756)
        self.assertEqual(report.income_pence, 250010)
        self.assertEqual(report.cash_outgoing_pence, 105000)
        self.assertFalse(report.provisional)
        self.assertEqual(report.unclassified, 0)

    # The card-side repayment credit carries no cash movement; a linked
    # current-account payment row is where outgoing is evidenced (ticket 16).

    def test_net_cash_subtracts_card_debt_and_adds_savings(self):
        self.balances()

        report = compute_totals(date(2026, 8, 1), date(2026, 8, 31))

        self.assertEqual(report.net_cash_pence, 300000 + 25030 - 2000)
        self.assertFalse(report.net_cash_provisional)

    def test_missing_balance_evidence_is_visible_not_zero(self):
        report = compute_totals(date(2026, 8, 1), date(2026, 8, 31))

        self.assertTrue(report.net_cash_provisional)
        self.assertEqual(
            sorted(report.missing_balance_accounts), ["Card", "Current", "Savings"]
        )

    def test_unknown_classification_is_excluded_and_marked_provisional(self):
        add(self.current, self.upload_current, date(2026, 8, 9), "To someone", "Others", -500)

        report = compute_totals(date(2026, 8, 1), date(2026, 8, 31))

        self.assertTrue(report.provisional)
        self.assertEqual(report.unclassified, 1)
        self.assertEqual(report.spending_pence, 108756)
        self.assertEqual(report.cash_outgoing_pence, 105000)

    def test_refund_reduces_spending_in_its_own_period(self):
        report = compute_totals(date(2026, 8, 4), date(2026, 8, 4))

        self.assertEqual(report.spending_pence, -1244)
        self.assertEqual(report.income_pence, 0)
        self.assertEqual(report.cash_outgoing_pence, 0)

    def test_unidentified_bank_credit_is_not_income(self):
        add(self.current, self.upload_current, date(2026, 8, 10), "TRANSFER IN", "Bank credit", 5000)

        report = compute_totals(date(2026, 8, 1), date(2026, 8, 31))

        self.assertEqual(report.income_pence, 250010)
        self.assertEqual(report.unclassified, 1)
        self.assertTrue(report.provisional)

    def test_salary_description_identifies_bank_credit_income(self):
        add(self.current, self.upload_current, date(2026, 8, 15), "SALARY BONUS", "Bank credit", 1000)

        report = compute_totals(date(2026, 8, 1), date(2026, 8, 31))

        self.assertEqual(report.income_pence, 251010)
        self.assertEqual(report.unclassified, 0)

    def test_card_credit_without_evidence_is_not_a_refund(self):
        add(self.card, self.upload_card, date(2026, 8, 11), "SOMETHING BACK", "", -700)

        report = compute_totals(date(2026, 8, 1), date(2026, 8, 31))

        self.assertEqual(report.spending_pence, 108756)
        self.assertEqual(report.unclassified, 1)

    def test_transfer_to_an_excluded_product_is_not_spending(self):
        add(
            self.current,
            self.upload_current,
            date(2026, 8, 12),
            "Transfer to Example Digital Assets Europe Ltd",
            "Exchange",
            -2500,
        )

        report = compute_totals(date(2026, 8, 1), date(2026, 8, 31))

        self.assertEqual(report.spending_pence, 108756)
        self.assertEqual(report.cash_outgoing_pence, 105000)
        self.assertEqual(report.unclassified, 1)

    def test_evidenced_currency_conversion_out_and_back(self):
        add(self.current, self.upload_current, date(2026, 8, 13), "Exchanged to USD", "Exchange", -2500)
        add(self.current, self.upload_current, date(2026, 8, 14), "Exchanged to GBP", "Exchange", 1000)

        report = compute_totals(date(2026, 8, 1), date(2026, 8, 31))

        self.assertEqual(report.spending_pence, 108756 + 2500 - 1000)
        self.assertEqual(report.cash_outgoing_pence, 105000 + 2500)
        self.assertEqual(report.unclassified, 0)

    def test_period_excludes_rows_outside_it(self):
        report = compute_totals(date(2026, 8, 2), date(2026, 8, 2))

        self.assertEqual(report.spending_pence, 95000)
        self.assertEqual(report.income_pence, 0)
