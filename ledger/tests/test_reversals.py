"""Behavioral tests for refunds, fee waivers, returns and FX boundaries."""

from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from ledger.models import Account, AccountKind, ReversalLink, Transaction
from reporting.reversals import candidates_for
from reporting.totals import compute_totals
from reporting.tests.test_totals import add, make_upload


class ReversalTestCase(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="sourav", password="local-dev-password"
        )
        self.client.force_login(self.user)
        self.account = Account.objects.create(name="Current", kind=AccountKind.CURRENT)
        self.upload = make_upload(self.account, "current.pdf")

    def txn(self, month, day, description, transaction_type, amount):
        return add(self.account, self.upload, date(2026, month, day), description, transaction_type, amount)

    def totals(self, month):
        start = date(2026, month, 1)
        end = date(2026, month + 1, 1) - __import__("datetime").timedelta(days=1)
        return compute_totals(start, end)

    def confirm(self, transaction, peer):
        return self.client.post(
            reverse("ledger:review_detail", args=[transaction.pk]),
            {"action": "reverse", "peer": peer.pk},
        )


class FeeWaiverTests(ReversalTestCase):
    def setUp(self):
        super().setUp()
        self.fee = self.txn(7, 10, "ACCOUNT FEE", "Fee", -500)
        self.waiver = self.txn(8, 5, "FEE WAIVER", "Other", 500)

    def test_unconfirmed_waiver_is_not_income_and_totals_are_provisional(self):
        august = self.totals(8)

        self.assertEqual(august.income_pence, 0)
        self.assertEqual(august.spending_pence, 0)
        self.assertEqual(august.unclassified, 1)
        self.assertTrue(august.provisional)

    def test_confirmed_waiver_reverses_spending_in_its_period(self):
        self.assertEqual(self.totals(7).spending_pence, 500)

        self.confirm(self.fee, self.waiver)

        july = self.totals(7)
        august = self.totals(8)
        self.assertEqual(july.spending_pence, 500)
        self.assertEqual(july.cash_outgoing_pence, 500)
        self.assertEqual(august.spending_pence, -500)
        self.assertEqual(august.income_pence, 0)
        self.assertEqual(august.cash_outgoing_pence, 0)  # gross outgoing not netted

    def test_candidate_is_offered_from_either_side(self):
        self.assertIn(
            self.fee, [candidate["transaction"] for candidate in candidates_for(self.waiver)]
        )
        self.assertIn(
            self.waiver, [candidate["transaction"] for candidate in candidates_for(self.fee)]
        )

    def test_pairing_without_reversal_wording_is_not_offered(self):
        plain = self.txn(8, 6, "SOMETHING ELSE", "Other", 500)

        self.assertNotIn(
            plain, [candidate["transaction"] for candidate in candidates_for(self.waiver)]
        )

    def test_target_cannot_be_reversed_twice(self):
        self.confirm(self.fee, self.waiver)
        second = self.txn(8, 7, "FEE WAIVER AGAIN", "Other", 500)

        response = self.confirm(self.fee, second)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(ReversalLink.objects.count(), 1)


class FeeTokenTests(ReversalTestCase):
    def test_coffee_is_not_a_fee(self):
        self.txn(8, 4, "COFFEE WALLET TRANSFER", "Other", -300)

        august = self.totals(8)

        self.assertEqual(august.spending_pence, 0)
        self.assertEqual(august.cash_outgoing_pence, 0)
        self.assertEqual(august.unclassified, 1)
        self.assertTrue(august.provisional)

    def test_explicit_fee_type_is_spending_even_without_the_word(self):
        self.txn(8, 4, "MONTHLY CHARGE", "Fee", -300)

        august = self.totals(8)

        self.assertEqual(august.spending_pence, 300)
        self.assertEqual(august.cash_outgoing_pence, 300)


class ReturnedPaymentTests(ReversalTestCase):
    def test_returned_payment_reverses_spending_but_preserves_gross_outgoing(self):
        payment = self.txn(7, 10, "CARD PAYMENT", "Card payment", -2000)
        returned = self.txn(8, 5, "RETURNED PAYMENT", "Other", 2000)

        self.confirm(payment, returned)

        july = self.totals(7)
        august = self.totals(8)
        self.assertEqual(july.spending_pence, 2000)
        self.assertEqual(july.cash_outgoing_pence, 2000)
        self.assertEqual(august.spending_pence, -2000)
        self.assertEqual(august.income_pence, 0)
        self.assertEqual(august.cash_outgoing_pence, 0)

    def test_unmatched_return_stays_provisional_without_income(self):
        self.txn(8, 9, "RETURNED PAYMENT", "Other", 2000)

        august = self.totals(8)

        self.assertEqual(august.income_pence, 0)
        self.assertEqual(august.unclassified, 1)
        self.assertTrue(august.provisional)


class FxBoundaryTests(ReversalTestCase):
    def test_conversion_out_and_back_use_their_own_posting_periods(self):
        self.txn(7, 15, "Exchanged to USD", "Exchange", -2500)
        self.txn(8, 5, "Exchanged to GBP", "Exchange", 1000)

        july = self.totals(7)
        august = self.totals(8)
        self.assertEqual(july.spending_pence, 2500)
        self.assertEqual(july.cash_outgoing_pence, 2500)
        self.assertEqual(august.spending_pence, -1000)
        self.assertEqual(august.income_pence, 0)
        self.assertEqual(august.cash_outgoing_pence, 0)

    def test_cash_withdrawal_is_spending_and_outgoing_without_a_cash_ledger(self):
        self.txn(8, 3, "CASH POINT", "Cash withdrawal", -4000)

        august = self.totals(8)
        self.assertEqual(august.spending_pence, 4000)
        self.assertEqual(august.cash_outgoing_pence, 4000)
        self.assertEqual(Transaction.objects.count(), 1)
