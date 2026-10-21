"""Behavioral tests for confirmed transfer and repayment links."""

from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase, TransactionTestCase
from django.urls import reverse

from ledger.models import Account, AccountKind, Transaction, TransferLink
from reporting.totals import compute_totals
from reporting.transfers import candidates_for
from reporting.tests.test_totals import add, make_upload


class TransferTestCase(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="sourav", password="local-dev-password"
        )
        self.client.force_login(self.user)
        self.current = Account.objects.create(name="Current", kind=AccountKind.CURRENT)
        self.card = Account.objects.create(name="Card", kind=AccountKind.CARD)
        self.savings = Account.objects.create(name="Savings", kind=AccountKind.SAVINGS)
        self.current_upload = make_upload(self.current, "current.pdf")
        self.card_upload = make_upload(self.card, "card.pdf")
        self.savings_upload = make_upload(self.savings, "savings.pdf")

    def txn(self, account, upload, day, description, transaction_type, amount):
        return add(account, upload, date(2026, 8, day), description, transaction_type, amount)

    def totals(self):
        return compute_totals(date(2026, 8, 1), date(2026, 8, 31))

    def link(self, transaction, peer, kind):
        return self.client.post(
            reverse("ledger:review_detail", args=[transaction.pk]),
            {"action": "link", "peer": peer.pk, "kind": kind},
        )


class CandidateTests(TransferTestCase):
    def setUp(self):
        super().setUp()
        self.payment = self.txn(self.current, self.current_upload, 5, "CARD PAYMENT", "Card payment", -8000)
        self.credit = self.txn(self.card, self.card_upload, 6, "PAYMENT RECEIVED - THANK YOU", "", -8000)
        self.purchase = self.txn(self.card, self.card_upload, 2, "SHOP", "", 8000)

    def test_repayment_candidate_is_surfaced_without_changing_totals(self):
        candidates = candidates_for(self.payment)

        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0]["transaction"], self.credit)
        self.assertEqual(candidates[0]["kind"], "repayment")
        self.assertEqual(self.totals().spending_pence, 16000)
        page = self.client.get(reverse("ledger:review_detail", args=[self.payment.pk]))
        self.assertContains(page, "Possible transfers or repayments")
        self.assertContains(page, "Confirm card repayment")

    def test_equal_amounts_outside_the_candidate_window_are_not_offered(self):
        far = self.txn(self.card, self.card_upload, 25, "PAYMENT RECEIVED - THANK YOU", "", -8000)

        self.assertNotIn(far, [candidate["transaction"] for candidate in candidates_for(self.payment)])

    def test_same_direction_amounts_are_not_candidates(self):
        other = self.txn(self.card, self.card_upload, 5, "REFUND", "", 8000)

        self.assertNotIn(other, [candidate["transaction"] for candidate in candidates_for(self.purchase)])

    def test_multiple_candidates_require_a_choice(self):
        second_credit = self.txn(self.card, self.card_upload, 7, "PAYMENT RECEIVED - THANK YOU", "", -8000)

        peers = [candidate["transaction"] for candidate in candidates_for(self.payment)]

        self.assertIn(self.credit, peers)
        self.assertIn(second_credit, peers)


class RepaymentTests(TransferTestCase):
    def setUp(self):
        super().setUp()
        self.purchase = self.txn(self.card, self.card_upload, 2, "SHOP", "", 8000)
        self.payment = self.txn(self.current, self.current_upload, 5, "CARD PAYMENT", "Card payment", -8000)
        self.credit = self.txn(self.card, self.card_upload, 6, "PAYMENT RECEIVED - THANK YOU", "", -8000)

    def test_confirmed_repayment_counts_spending_once_and_outgoing_once(self):
        self.assertEqual(self.totals().spending_pence, 16000)
        self.assertEqual(self.totals().cash_outgoing_pence, 8000)

        self.link(self.payment, self.credit, "repayment")

        after = self.totals()
        self.assertEqual(after.spending_pence, 8000)
        self.assertEqual(after.cash_outgoing_pence, 8000)
        self.assertEqual(after.income_pence, 0)

    def test_both_entries_and_sources_remain_traceable(self):
        self.link(self.payment, self.credit, "repayment")

        self.assertEqual(Transaction.objects.count(), 3)
        self.assertEqual(TransferLink.objects.get().kind, "repayment")
        self.assertTrue(Transaction.objects.filter(pk=self.payment.pk).exists())
        self.assertTrue(Transaction.objects.filter(pk=self.credit.pk).exists())

    def test_kind_must_match_the_candidate(self):
        response = self.link(self.payment, self.credit, "transfer")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(TransferLink.objects.count(), 0)

    def test_a_linked_row_cannot_be_linked_twice(self):
        self.link(self.payment, self.credit, "repayment")
        extra = self.txn(self.card, self.card_upload, 7, "PAYMENT RECEIVED - THANK YOU", "", -8000)

        response = self.link(self.payment, extra, "repayment")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(TransferLink.objects.count(), 1)


class OwnTransferTests(TransferTestCase):
    def test_confirmed_transfer_has_no_spending_income_or_outgoing(self):
        out = self.txn(self.current, self.current_upload, 10, "TO SAVINGS", "Card payment", -5000)
        into = self.txn(self.savings, self.savings_upload, 11, "FROM CURRENT", "Interest", 5000)

        self.assertEqual(self.totals().spending_pence, 5000)
        self.link(out, into, "transfer")

        after = self.totals()
        self.assertEqual(after.spending_pence, 0)
        self.assertEqual(after.income_pence, 0)
        self.assertEqual(after.cash_outgoing_pence, 0)
        self.assertEqual(Transaction.objects.count(), 2)

    def test_unconfirmed_transfer_keeps_machine_effects(self):
        self.txn(self.current, self.current_upload, 10, "TO SAVINGS", "Card payment", -5000)
        self.txn(self.savings, self.savings_upload, 11, "FROM CURRENT", "Interest", 5000)

        totals = self.totals()
        self.assertEqual(totals.spending_pence, 5000)
        self.assertEqual(totals.income_pence, 5000)
        self.assertEqual(TransferLink.objects.count(), 0)


class ConcurrentLinkTests(TransactionTestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="sourav", password="local-dev-password"
        )
        self.current = Account.objects.create(name="Current", kind=AccountKind.CURRENT)
        self.card = Account.objects.create(name="Card", kind=AccountKind.CARD)
        self.current_upload = make_upload(self.current, "current.pdf")
        self.card_upload = make_upload(self.card, "card.pdf")
        self.payment = add(
            self.current, self.current_upload, date(2026, 8, 5),
            "CARD PAYMENT", "Card payment", -8000,
        )
        self.credit_one = add(
            self.card, self.card_upload, date(2026, 8, 6),
            "PAYMENT RECEIVED - THANK YOU", "", -8000,
        )
        self.credit_two = add(
            self.card, self.card_upload, date(2026, 8, 7),
            "PAYMENT RECEIVED - THANK YOU", "", -8000,
        )

    def test_overlapping_confirmations_cannot_link_one_entry_twice(self):
        from threading import Barrier, Thread

        from django.db import connections
        from django.test import Client

        barrier = Barrier(2)
        statuses = []

        def confirm(transaction_id, peer_id):
            try:
                barrier.wait(timeout=10)
                client = Client(SERVER_NAME="localhost")
                client.force_login(self.user)
                response = client.post(
                    reverse("ledger:review_detail", args=[transaction_id]),
                    {"action": "link", "peer": peer_id, "kind": "repayment"},
                )
                statuses.append(response.status_code)
            finally:
                connections.close_all()

        threads = [
            Thread(target=confirm, args=(self.payment.pk, self.credit_one.pk)),
            Thread(target=confirm, args=(self.credit_two.pk, self.payment.pk)),
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=20)

        self.assertEqual(sorted(statuses), [302, 400])
        self.assertEqual(TransferLink.objects.count(), 1)
        link = TransferLink.objects.get()
        self.assertIn(self.payment.pk, [link.transaction_a_id, link.transaction_b_id])
