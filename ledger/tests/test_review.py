"""Behavioral tests for review, corrections and history-preserving revert."""

from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from ledger.models import Account, AccountKind, Correction, Transaction
from reporting.totals import compute_totals
from reporting.tests.test_totals import add, make_upload


class ReviewTestCase(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="sourav", password="local-dev-password"
        )
        self.client.force_login(self.user)
        self.account = Account.objects.create(name="Current", kind=AccountKind.CURRENT)
        self.upload = make_upload(self.account, "current.pdf")
        add(self.account, self.upload, date(2026, 8, 1), "SALARY ACME", "Salary", 250000)
        self.unclear = add(
            self.account, self.upload, date(2026, 8, 9), "To someone", "Others", -500
        )

    def totals(self):
        return compute_totals(date(2026, 8, 1), date(2026, 8, 31))

    def correct(self, classification, note=""):
        return self.client.post(
            reverse("ledger:review_detail", args=[self.unclear.pk]),
            {"action": "correct", "classification": classification, "note": note},
        )

    def revert(self):
        return self.client.post(
            reverse("ledger:review_detail", args=[self.unclear.pk]),
            {"action": "revert"},
        )


class ReviewListTests(ReviewTestCase):
    def test_unresolved_transaction_is_listed_for_review(self):
        page = self.client.get(reverse("ledger:review"))

        self.assertContains(page, "To someone")
        self.assertContains(page, "Unresolved")
        self.assertContains(page, reverse("ledger:review_detail", args=[self.unclear.pk]))

    def test_review_requires_login(self):
        self.client.logout()

        self.assertEqual(self.client.get(reverse("ledger:review")).status_code, 302)
        self.assertEqual(
            self.client.get(
                reverse("ledger:review_detail", args=[self.unclear.pk])
            ).status_code,
            302,
        )


class CorrectionTests(ReviewTestCase):
    def test_detail_shows_source_evidence_and_effects(self):
        page = self.client.get(reverse("ledger:review_detail", args=[self.unclear.pk]))

        self.assertContains(page, "page 1, row 2")
        self.assertContains(page, "To someone")
        self.assertContains(page, "-£5.00")
        self.assertContains(page, "Unresolved")
        self.assertContains(page, "spending £5.00")
        self.assertContains(page, "Not applicable to this source")

    def test_get_does_not_create_a_correction(self):
        self.client.get(reverse("ledger:review_detail", args=[self.unclear.pk]))

        self.assertEqual(Correction.objects.count(), 0)

    def test_confirmed_spending_correction_updates_totals(self):
        before = self.totals()
        self.assertEqual(before.unclassified, 1)

        self.correct("spending", "cash to a friend")

        after = self.totals()
        self.assertEqual(after.spending_pence, before.spending_pence + 500)
        self.assertEqual(after.cash_outgoing_pence, before.cash_outgoing_pence + 500)
        self.assertEqual(after.unclassified, 0)
        correction = Correction.objects.get()
        self.assertEqual(correction.classification, "spending")
        self.assertEqual(correction.note, "cash to a friend")

    def test_income_correction_on_an_inflow_does_not_become_spending(self):
        incoming = add(
            self.account, self.upload, date(2026, 8, 12), "Transfer in", "Bank credit", 10000
        )

        self.client.post(
            reverse("ledger:review_detail", args=[incoming.pk]),
            {"action": "correct", "classification": "income"},
        )

        after = self.totals()
        self.assertEqual(after.income_pence, 260000)
        self.assertEqual(after.spending_pence, 0)

    def test_outgoing_cannot_be_confirmed_as_income(self):
        response = self.correct("income")

        self.assertEqual(response.status_code, 400)
        self.assertContains(response, "signed direction", status_code=400)
        self.assertEqual(Correction.objects.count(), 0)
        self.assertEqual(self.totals().unclassified, 1)

    def test_outgoing_cannot_be_confirmed_as_a_refund(self):
        response = self.correct("refund")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(Correction.objects.count(), 0)

    def test_card_credit_cannot_be_confirmed_as_income_but_can_be_a_refund(self):
        card = Account.objects.create(name="Card", kind=AccountKind.CARD)
        card_upload = make_upload(card, "card.pdf")
        credit = add(card, card_upload, date(2026, 8, 13), "SOMETHING BACK", "", -700)
        url = reverse("ledger:review_detail", args=[credit.pk])

        rejected = self.client.post(
            url, {"action": "correct", "classification": "income"}
        )
        self.assertEqual(rejected.status_code, 400)

        accepted = self.client.post(
            url, {"action": "correct", "classification": "refund"}
        )
        self.assertEqual(accepted.status_code, 302)
        self.assertEqual(Correction.objects.get().classification, "refund")

    def test_transfer_correction_has_no_reporting_effect(self):
        self.correct("transfer")

        after = self.totals()
        self.assertEqual(after.spending_pence, 0)
        self.assertEqual(after.income_pence, 250000)
        self.assertEqual(after.cash_outgoing_pence, 0)

    def test_revert_restores_source_derived_value_and_keeps_history(self):
        self.correct("spending")
        self.assertGreater(self.totals().spending_pence, 0)

        self.revert()

        after = self.totals()
        self.assertEqual(after.spending_pence, 0)
        self.assertEqual(after.unclassified, 1)
        correction = Correction.objects.get()
        self.assertIsNotNone(correction.reverted_at)

    def test_a_new_correction_supersedes_the_previous_one(self):
        self.correct("spending")
        self.correct("transfer")

        self.assertEqual(Correction.objects.count(), 2)
        active = Correction.objects.get(reverted_at__isnull=True)
        self.assertEqual(active.classification, "transfer")
        after = self.totals()
        self.assertEqual(after.spending_pence, 0)
        self.assertEqual(after.income_pence, 250000)

    def test_invalid_classification_is_ignored(self):
        self.client.post(
            reverse("ledger:review_detail", args=[self.unclear.pk]),
            {"action": "correct", "classification": "invented"},
        )

        self.assertEqual(Correction.objects.count(), 0)

    def test_source_values_are_never_overwritten(self):
        self.correct("spending")

        self.unclear.refresh_from_db()
        self.assertEqual(self.unclear.description, "To someone")
        self.assertEqual(self.unclear.amount_pence, -500)
        self.assertEqual(self.unclear.transaction_type, "Others")
