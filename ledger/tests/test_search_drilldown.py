"""Behavioral tests for description search and metric drill-down."""

from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from ledger.models import Account, AccountKind, Transaction
from reporting.tests.test_totals import add, make_upload


class DrilldownTestCase(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="sourav", password="local-dev-password"
        )
        self.client.force_login(self.user)
        self.current = Account.objects.create(name="Current", kind=AccountKind.CURRENT)
        self.card = Account.objects.create(name="Card", kind=AccountKind.CARD)
        self.savings = Account.objects.create(name="Savings", kind=AccountKind.SAVINGS)
        self.upload_current = make_upload(self.current, "current.pdf")
        self.upload_card = make_upload(self.card, "card.pdf")
        self.upload_savings = make_upload(self.savings, "savings.pdf")

        add(self.current, self.upload_current, date(2026, 8, 1), "SALARY ACME", "Salary", 250000)
        add(self.current, self.upload_current, date(2026, 8, 2), "RENT PAYMENT", "DD", -95000)
        add(self.current, self.upload_current, date(2026, 8, 3), "CASH POINT", "Cash withdrawal", -10000)
        add(self.current, self.upload_current, date(2026, 8, 4), "REFUND CORNER STORE", "Refund", 1244)
        add(self.card, self.upload_card, date(2026, 8, 5), "COFFEE MERCHANT", "", 5000)
        add(self.card, self.upload_card, date(2026, 8, 6), "DIRECT DEBIT PAYMENT - THANK YOU", "", -5000)
        add(self.savings, self.upload_savings, date(2026, 8, 7), "Gross Interest", "Interest", 10)
        add(self.current, self.upload_current, date(2026, 8, 8), "To someone", "Others", -500)


class MetricDrilldownTests(DrilldownTestCase):
    def get_metric(self, metric, **params):
        return self.client.get(
            reverse("ledger:metric"),
            {"metric": metric, "start": "2026-08-01", "end": "2026-08-31", **params},
        )

    def test_spending_lists_only_contributing_rows(self):
        page = self.get_metric("spending")

        self.assertContains(page, "RENT PAYMENT")
        self.assertContains(page, "CASH POINT")
        self.assertContains(page, "COFFEE MERCHANT")
        self.assertContains(page, "REFUND CORNER STORE")
        self.assertNotContains(page, "SALARY ACME")
        self.assertNotContains(page, "Gross Interest")
        self.assertNotContains(page, "DIRECT DEBIT PAYMENT")
        self.assertContains(page, "£1,087.56")

    def test_income_lists_only_identified_income(self):
        page = self.get_metric("income")

        self.assertContains(page, "SALARY ACME")
        self.assertContains(page, "Gross Interest")
        self.assertNotContains(page, "RENT PAYMENT")
        self.assertContains(page, "£2,500.10")

    def test_cash_outgoing_excludes_card_purchases(self):
        page = self.get_metric("cash_outgoing")

        self.assertContains(page, "RENT PAYMENT")
        self.assertContains(page, "CASH POINT")
        self.assertNotContains(page, "COFFEE MERCHANT")
        self.assertContains(page, "£1,050.00")

    def test_period_context_is_preserved_on_the_page(self):
        page = self.get_metric("spending")

        self.assertContains(page, "2026-08-01")
        self.assertContains(page, "2026-08-31")
        self.assertContains(page, "start=2026-08-01")

    def test_unclassified_rows_are_explained_as_excluded(self):
        page = self.get_metric("spending")

        self.assertContains(page, "unresolved classification")
        self.assertContains(page, "excluded")

    def test_rows_link_to_authenticated_source_evidence(self):
        page = self.get_metric("spending")

        self.assertContains(
            page, reverse("ledger:upload_original", args=[self.upload_current.pk])
        )

    def test_anonymous_access_is_denied(self):
        self.client.logout()

        response = self.get_metric("spending")

        self.assertEqual(response.status_code, 302)
        self.assertTrue(response["Location"].startswith("/login/"))

    def test_large_result_sets_are_paginated(self):
        upload = make_upload(self.current, "many.pdf")
        for index in range(60):
            add(self.current, upload, date(2026, 8, 10), f"SHOP {index}", "DD", -100)

        first = self.get_metric("spending")
        second = self.get_metric("spending", page=2)

        self.assertEqual(first.content.decode().count("<tr>"), 50 + 1)  # header row
        self.assertContains(first, "Page 1 of 2")
        self.assertContains(second, "Page 2 of 2")

    def test_unknown_metric_is_rejected(self):
        response = self.client.get(reverse("ledger:metric"), {"metric": "invented"})

        self.assertEqual(response.status_code, 400)


class SearchTests(DrilldownTestCase):
    def test_search_matches_original_description_text(self):
        page = self.client.get(reverse("ledger:search"), {"q": "RENT"})

        self.assertContains(page, "RENT PAYMENT")
        self.assertNotContains(page, "COFFEE MERCHANT")

    def test_search_is_case_insensitive_and_partial(self):
        page = self.client.get(reverse("ledger:search"), {"q": "corner"})

        self.assertContains(page, "REFUND CORNER STORE")

    def test_search_does_not_match_category_or_type(self):
        page = self.client.get(reverse("ledger:search"), {"q": "DD"})

        self.assertContains(page, "No transactions match")
        self.assertNotContains(page, "RENT PAYMENT")

    def test_search_can_be_scoped_to_the_selected_period(self):
        page = self.client.get(
            reverse("ledger:search"),
            {"q": "COFFEE", "start": "2026-07-01", "end": "2026-07-31"},
        )

        self.assertContains(page, "No transactions match")

    def test_search_results_reach_source_evidence(self):
        page = self.client.get(reverse("ledger:search"), {"q": "COFFEE"})

        self.assertContains(
            page, reverse("ledger:upload_original", args=[self.upload_card.pk])
        )

    def test_search_requires_login(self):
        self.client.logout()

        response = self.client.get(reverse("ledger:search"), {"q": "RENT"})

        self.assertEqual(response.status_code, 302)
