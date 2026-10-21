"""Behavioral tests for the private account overview."""

from django.test import TestCase
from django.urls import reverse

from ledger.models import Account, AccountKind


class PrivateAccessTests(TestCase):
    """The overview is private and there is no self-service registration."""

    def test_anonymous_visitor_is_sent_to_the_login_page(self):
        response = self.client.get(reverse("ledger:overview"))

        self.assertRedirects(response, "/login/?next=/")

    def test_login_page_is_reachable_without_a_session(self):
        response = self.client.get(reverse("login"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'name="username"')
        self.assertContains(response, 'name="password"')

    def test_no_self_service_registration_route_exists(self):
        for path in ("/register/", "/accounts/signup/", "/signup/"):
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 404)


class AccountOverviewTests(TestCase):
    """Signed-in users see named accounts, with honest unknown balances."""

    def setUp(self):
        self.accounts = [
            Account.objects.create(name="Lloyds Current", kind=AccountKind.CURRENT),
            Account.objects.create(name="Lloyds Credit", kind=AccountKind.CARD),
            Account.objects.create(name="Revolut Savings", kind=AccountKind.SAVINGS),
        ]
        self.user = self._create_user()
        self.client.force_login(self.user)

    @staticmethod
    def _create_user():
        from django.contrib.auth import get_user_model

        return get_user_model().objects.create_user(
            username="sourav", password="not-a-real-password"
        )

    def test_overview_lists_each_named_account_with_its_kind(self):
        response = self.client.get(reverse("ledger:overview"))

        self.assertEqual(response.status_code, 200)
        expected = {
            "Lloyds Current": "Current account",
            "Lloyds Credit": "Credit card",
            "Revolut Savings": "Savings",
        }
        for name, kind_label in expected.items():
            with self.subTest(account=name):
                self.assertContains(response, name)
                self.assertContains(response, kind_label)

    def test_accounts_without_balance_evidence_report_unknown_not_zero(self):
        response = self.client.get(reverse("ledger:overview"))

        content = response.content.decode()
        self.assertEqual(content.count("Balance unknown"), 3)
        self.assertNotIn("£0.00", content)

    def test_empty_overview_does_not_fabricate_zero_totals(self):
        Account.objects.all().delete()

        response = self.client.get(reverse("ledger:overview"))

        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertContains(response, "No named accounts yet")
        self.assertNotIn("£0.00", content)
