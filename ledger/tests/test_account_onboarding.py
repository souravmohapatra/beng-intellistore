"""Account onboarding through authenticated application pages, not admin."""

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse


class AccountOnboardingTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="onboarding", password="synthetic-test-password"
        )
        self.client.force_login(self.user)

    def test_created_account_is_available_and_selected_for_first_upload(self):
        response = self.client.post(
            "/accounts/", {"name": "Household current", "kind": "current"}, follow=True
        )
        self.assertRedirects(response, reverse("ledger:uploads"))
        self.assertContains(response, "Household current")
        self.assertRegex(
            response.content.decode(),
            r'<option value="\d+" selected>Household current</option>',
        )
        accounts = self.client.get("/accounts/")
        self.assertContains(accounts, "Household current")
        self.assertContains(accounts, "Current account")

    def test_duplicate_and_invalid_accounts_leave_existing_account_usable(self):
        self.client.post("/accounts/", {"name": "Existing current", "kind": "current"})
        cases = [
            ({"name": "Existing current", "kind": "card"}, "name"),
            ({"name": "Invalid kind", "kind": "investment"}, "kind"),
            ({"name": "   ", "kind": "current"}, "name"),
        ]
        for payload, field in cases:
            with self.subTest(payload=payload):
                response = self.client.post("/accounts/", payload)
                self.assertEqual(response.status_code, 200)
                self.assertIn(field, response.context["form"].errors)
        accounts = self.client.get("/accounts/")
        self.assertNotContains(accounts, "Invalid kind")
        self.assertContains(accounts, "Current account")
        uploads = self.client.get(reverse("ledger:uploads"))
        self.assertEqual(
            uploads.content.decode().count(">Existing current</option>"), 1
        )

    def test_anonymous_and_cross_site_posts_cannot_create_accounts(self):
        anonymous = Client()
        for method in (anonymous.get, anonymous.post):
            response = method("/accounts/", {"name": "Unwanted", "kind": "current"})
            self.assertEqual(response.status_code, 302)
            self.assertTrue(response.url.startswith("/login/?next="))
        protected = Client(enforce_csrf_checks=True)
        protected.force_login(self.user)
        denied = protected.post(
            "/accounts/", {"name": "Unwanted", "kind": "current"}
        )
        self.assertEqual(denied.status_code, 403)
        self.assertNotContains(self.client.get("/accounts/"), "Unwanted")
