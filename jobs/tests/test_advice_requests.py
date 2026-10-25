"""Behavioral tests for independent advice requests and bounded retry."""

import json
from datetime import date, timedelta

from django.test import TestCase
from django.utils import timezone
from django.urls import reverse

from jobs.models import AdviceRequest, WorkerCredential
from ledger.models import (
    ClassificationSuggestion,
    Correction,
    Transaction,
    Upload,
)
from ledger.tests.fixtures import text_pdf
from ledger.tests.support import UploadSetupMixin


class AdviceRequestTests(UploadSetupMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.upload(text_pdf(), filename="advice.pdf")
        self.receipt = Upload.objects.get(filename="advice.pdf")
        self.transaction = Transaction.objects.create(
            account=self.account,
            upload=self.receipt,
            posted_on=date(2026, 8, 9),
            description="TO SOMEONE",
            transaction_type="Others",
            amount_pence=-500,
            balance_pence=None,
            source_page=1,
            source_row=1,
            source_text="09 Aug 26; Description TO SOMEONE; Type Others; Money Out 5.00",
            needs_review=True,
        )
        self.credential, self.token = WorkerCredential.issue("advice-worker")

    def api(self, name, payload=None, args=(), token=None):
        return self.client.post(
            reverse(name, args=args),
            data=json.dumps(payload),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token or self.token}",
        )

    def request_advice(self):
        return self.client.post(
            reverse("ledger:review_detail", args=[self.transaction.pk]),
            {"action": "request_advice"},
        )

    def suggestion(self, classification="transfer"):
        return {
            "version": 1,
            "classification": classification,
            "confidence": 0.8,
            "explanation": "Likely an own-account transfer.",
            "model": "fake-model",
            "prompt_version": "v1",
        }

    def test_only_unresolved_rows_can_request_advice(self):
        resolved = Transaction.objects.create(
            account=self.account,
            upload=self.receipt,
            posted_on=date(2026, 8, 10),
            description="COFFEE",
            transaction_type="Card payment",
            amount_pence=-320,
            balance_pence=None,
            source_page=1,
            source_row=2,
            source_text="COFFEE",
        )
        response = self.client.post(
            reverse("ledger:review_detail", args=[resolved.pk]),
            {"action": "request_advice"},
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(AdviceRequest.objects.count(), 0)

    def test_request_is_visible_and_claim_exposes_only_needed_fields(self):
        self.request_advice()
        request_row = AdviceRequest.objects.get()
        self.assertEqual(request_row.status, AdviceRequest.Status.PENDING)
        review = self.client.get(
            reverse("ledger:review_detail", args=[self.transaction.pk])
        )
        self.assertContains(review, "Waiting for the laptop")

        claimed = self.api("jobs:claim_advice")
        self.assertEqual(claimed.status_code, 200)
        body = claimed.json()
        self.assertEqual(body["request"], request_row.pk)
        self.assertEqual(body["transaction"]["description"], "TO SOMEONE")
        self.assertEqual(body["transaction"]["amount_pence"], -500)
        self.assertEqual(body["transaction"]["account_kind"], "current")
        request_row.refresh_from_db()
        self.assertEqual(request_row.status, AdviceRequest.Status.PROCESSING)
        self.assertEqual(request_row.attempts_used, 1)

    def test_valid_suggestion_completes_without_touching_financial_facts(self):
        self.request_advice()
        claimed = self.api("jobs:claim_advice").json()
        before = (
            self.transaction.amount_pence,
            self.transaction.posted_on,
            self.transaction.description,
        )

        response = self.api(
            "jobs:advice_result",
            {
                "claim_token": claimed["claim_token"],
                "outcome": "suggested",
                "suggestion": self.suggestion(),
            },
            args=[claimed["request"]],
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(AdviceRequest.objects.get().status, AdviceRequest.Status.COMPLETED)
        self.assertEqual(ClassificationSuggestion.objects.count(), 1)
        self.assertEqual(Correction.objects.count(), 0)
        self.transaction.refresh_from_db()
        self.assertEqual(
            (
                self.transaction.amount_pence,
                self.transaction.posted_on,
                self.transaction.description,
            ),
            before,
        )

    def test_malformed_suggestion_does_not_complete_the_request(self):
        for classification in ("loan", [], {}, None):
            with self.subTest(classification=classification):
                self.request_advice()
                claimed = self.api("jobs:claim_advice").json()

                response = self.api(
                    "jobs:advice_result",
                    {
                        "claim_token": claimed["claim_token"],
                        "outcome": "suggested",
                        "suggestion": self.suggestion(classification),
                    },
                    args=[claimed["request"]],
                )

                self.assertEqual(response.status_code, 400)
                self.assertEqual(ClassificationSuggestion.objects.count(), 0)
                request_row = AdviceRequest.objects.get()
                self.assertEqual(request_row.status, AdviceRequest.Status.PENDING)
                request_row.delete()

    def test_failure_is_visible_then_manual_retry_succeeds_without_reimport(self):
        self.request_advice()
        first = self.api("jobs:claim_advice").json()
        failed = self.api(
            "jobs:advice_result",
            {
                "claim_token": first["claim_token"],
                "outcome": "failed",
                "failure": "AdvisoryUnavailableError",
            },
            args=[first["request"]],
        )
        self.assertEqual(failed.status_code, 200)

        review = self.client.get(
            reverse("ledger:review_detail", args=[self.transaction.pk])
        )
        self.assertContains(review, "AdvisoryUnavailableError")

        retry = self.request_advice()
        self.assertEqual(retry.status_code, 302)
        self.assertEqual(AdviceRequest.objects.get().status, AdviceRequest.Status.PENDING)

        second = self.api("jobs:claim_advice").json()
        done = self.api(
            "jobs:advice_result",
            {
                "claim_token": second["claim_token"],
                "outcome": "suggested",
                "suggestion": self.suggestion(),
            },
            args=[second["request"]],
        )
        self.assertEqual(done.status_code, 200)
        self.assertEqual(Transaction.objects.count(), 1)  # no re-import
        self.assertEqual(ClassificationSuggestion.objects.count(), 1)

    def test_attempt_budget_is_bounded(self):
        self.request_advice()
        for _ in range(3):
            claimed = self.api("jobs:claim_advice")
            if claimed.status_code == 204:
                break
            body = claimed.json()
            self.api(
                "jobs:advice_result",
                {
                    "claim_token": body["claim_token"],
                    "outcome": "failed",
                    "failure": "AdvisoryUnavailableError",
                },
                args=[body["request"]],
            )
        request_row = AdviceRequest.objects.get()
        self.assertEqual(request_row.status, AdviceRequest.Status.FAILED)
        self.assertEqual(
            self.api("jobs:claim_advice").status_code, 204
        )
        review = self.client.get(
            reverse("ledger:review_detail", args=[self.transaction.pk])
        )
        self.assertContains(review, "Request advice again")

    def test_stale_processing_request_is_reclaimed(self):
        self.request_advice()
        first = self.api("jobs:claim_advice").json()
        AdviceRequest.objects.update(lease_expires_at=timezone.now() - timedelta(hours=1))

        second = self.api("jobs:claim_advice")
        self.assertEqual(second.status_code, 200)
        self.assertEqual(second.json()["request"], first["request"])
        self.assertEqual(AdviceRequest.objects.get().attempts_used, 2)

    def test_dismissed_suggestion_allows_another_request(self):
        self.request_advice()
        claimed = self.api("jobs:claim_advice").json()
        self.api(
            "jobs:advice_result",
            {
                "claim_token": claimed["claim_token"],
                "outcome": "suggested",
                "suggestion": self.suggestion(),
            },
            args=[claimed["request"]],
        )
        suggestion_row = ClassificationSuggestion.objects.get()
        self.client.post(
            reverse("ledger:review_detail", args=[self.transaction.pk]),
            {"action": "dismiss_advice", "suggestion": suggestion_row.pk},
        )

        response = self.request_advice()

        self.assertEqual(response.status_code, 302)
        self.assertEqual(AdviceRequest.objects.get().status, AdviceRequest.Status.PENDING)

    def test_reclaimed_claim_fences_the_stale_worker(self):
        self.request_advice()
        stale = self.api("jobs:claim_advice").json()
        AdviceRequest.objects.update(lease_expires_at=timezone.now() - timedelta(hours=1))

        # A different worker reclaims after expiry, receiving its own token.
        fresh = self.api("jobs:claim_advice").json()
        self.assertNotEqual(stale["claim_token"], fresh["claim_token"])

        rejected = self.api(
            "jobs:advice_result",
            {
                "claim_token": stale["claim_token"],
                "outcome": "suggested",
                "suggestion": self.suggestion(),
            },
            args=[stale["request"]],
        )
        self.assertEqual(rejected.status_code, 409)
        self.assertEqual(ClassificationSuggestion.objects.count(), 0)
        self.assertEqual(
            AdviceRequest.objects.get().status, AdviceRequest.Status.PROCESSING
        )

        accepted = self.api(
            "jobs:advice_result",
            {
                "claim_token": fresh["claim_token"],
                "outcome": "suggested",
                "suggestion": self.suggestion(),
            },
            args=[fresh["request"]],
        )
        self.assertEqual(accepted.status_code, 200)
        self.assertEqual(ClassificationSuggestion.objects.count(), 1)

    def test_a_different_worker_credential_cannot_submit(self):
        self.request_advice()
        claimed = self.api("jobs:claim_advice").json()
        _other_credential, other_token = WorkerCredential.issue("other-worker")

        rejected = self.api(
            "jobs:advice_result",
            {
                "claim_token": claimed["claim_token"],
                "outcome": "suggested",
                "suggestion": self.suggestion(),
            },
            args=[claimed["request"]],
            token=other_token,
        )

        self.assertEqual(rejected.status_code, 409)
        self.assertEqual(ClassificationSuggestion.objects.count(), 0)
        self.assertEqual(
            AdviceRequest.objects.get().status, AdviceRequest.Status.PROCESSING
        )

    def test_expired_lease_cannot_submit_even_with_the_right_token(self):
        self.request_advice()
        claimed = self.api("jobs:claim_advice").json()
        AdviceRequest.objects.update(lease_expires_at=timezone.now() - timedelta(seconds=1))

        rejected = self.api(
            "jobs:advice_result",
            {
                "claim_token": claimed["claim_token"],
                "outcome": "suggested",
                "suggestion": self.suggestion(),
            },
            args=[claimed["request"]],
        )

        self.assertEqual(rejected.status_code, 409)
        self.assertEqual(ClassificationSuggestion.objects.count(), 0)

    def test_advice_result_requires_a_claim_token(self):
        self.request_advice()
        claimed = self.api("jobs:claim_advice").json()

        rejected = self.api(
            "jobs:advice_result",
            {"outcome": "suggested", "suggestion": self.suggestion()},
            args=[claimed["request"]],
        )

        self.assertEqual(rejected.status_code, 400)
        self.assertEqual(ClassificationSuggestion.objects.count(), 0)
