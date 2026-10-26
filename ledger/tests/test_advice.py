"""Behavioral tests for local-model advice shown beside unresolved transactions."""

import json

from django.test import TestCase
from django.urls import reverse

from jobs.models import WorkerCredential
from ledger.models import (
    Account,
    AccountKind,
    ClassificationSuggestion,
    Correction,
    Transaction,
    Upload,
)
from ledger.tests.fixtures import text_pdf
from ledger.tests.support import UploadSetupMixin
from worker.client import build_result


class FakeParsed:
    """Minimal parsed result used to exercise worker advice collection."""

    section_name = "lloyds_current"
    account_kind_hint = "current"
    reconciled = True
    issues = []
    savings = None
    balances = []

    def __init__(self):
        from datetime import date

        def make_row(description, transaction_type, amount, balance, number):
            return type(
                "Row",
                (),
                {
                    "posted_on": date(2026, 8, number),
                    "transaction_date": None,
                    "description": description,
                    "transaction_type": transaction_type,
                    "amount_pence": amount,
                    "balance_pence": balance,
                    "page": 1,
                    "row": number,
                    "source_text": description,
                },
            )()

        self.rows = [
            make_row("SHOP", "Card payment", -320, 119680, 1),
            make_row("TO SOMEONE", "Others", -500, 119180, 2),
        ]


class WorkerAdviceTests(TestCase):
    def test_advice_is_collected_only_for_ambiguous_rows(self):
        from worker.advisory import AdvisoryClassification, AdvisorySuggestion, collect_advice

        class FakeClient:
            def __init__(self):
                self.calls = []

            def suggest_classification(self, **kwargs):
                self.calls.append(kwargs)
                return AdvisorySuggestion(
                    version=1,
                    classification=AdvisoryClassification.TRANSFER,
                    confidence=0.8,
                    explanation="Looks like an own-account transfer.",
                    model="fake-model",
                    prompt_version="v1",
                )

        client = FakeClient()
        advices = collect_advice(
            FakeParsed(), client, max_attempts=1, retry_delay_seconds=0
        )

        self.assertEqual(len(client.calls), 1)
        self.assertEqual(client.calls[0]["description"], "TO SOMEONE")
        self.assertEqual(len(advices["lloyds_current"]), 1)
        entry = advices["lloyds_current"][0]
        self.assertEqual(entry["classification"], "transfer")
        self.assertEqual((entry["page"], entry["row"]), (1, 2))

    def test_advice_failure_is_isolated_from_the_result(self):
        from worker.advisory import AdvisoryUnavailableError, collect_advice

        class FailingClient:
            def __init__(self):
                self.calls = 0

            def suggest_classification(self, **kwargs):
                self.calls += 1
                raise AdvisoryUnavailableError("runtime down")

        client = FailingClient()
        advices = collect_advice(
            FakeParsed(), client, max_attempts=2, retry_delay_seconds=0
        )

        self.assertEqual(client.calls, 2)  # bounded, not repeated forever
        self.assertEqual(advices, {"lloyds_current": []})

    def test_unexpected_adapter_exception_cannot_break_the_import(self):
        from worker.advisory import collect_advice

        class BrokenClient:
            def suggest_classification(self, **kwargs):
                raise TypeError("adapter bug")

        advices = collect_advice(
            FakeParsed(), BrokenClient(), max_attempts=2, retry_delay_seconds=0
        )

        self.assertEqual(advices, {"lloyds_current": []})

    def test_logs_do_not_repeat_model_text(self):
        from worker.advisory import AdvisoryFormatError, collect_advice

        class LeakyClient:
            def suggest_classification(self, **kwargs):
                raise AdvisoryFormatError("PRIVATE_MARKER_DESCRIPTION accepted")

        with self.assertLogs("worker.advisory", level="WARNING") as captured:
            collect_advice(
                FakeParsed(), LeakyClient(), max_attempts=1, retry_delay_seconds=0
            )

        output = "\n".join(captured.output)
        self.assertNotIn("PRIVATE_MARKER_DESCRIPTION", output)
        self.assertIn("AdvisoryFormatError", output)

    def test_advice_rows_are_capped_and_renew_the_lease(self):
        from worker.advisory import collect_advice

        class CountingClient:
            def __init__(self):
                self.calls = 0

            def suggest_classification(self, **kwargs):
                self.calls += 1
                raise RuntimeError("unavailable")

        parsed = FakeParsed()
        for row in parsed.rows:
            row.transaction_type = "Others"
        progress = []
        client = CountingClient()

        collect_advice(
            parsed,
            client,
            max_attempts=1,
            retry_delay_seconds=0,
            max_rows=1,
            on_progress=lambda: progress.append(True),
        )

        self.assertEqual(client.calls, 1)
        self.assertEqual(len(progress), 1)

    def test_lost_lease_during_advice_propagates(self):
        from worker.advisory import collect_advice

        class Client:
            def suggest_classification(self, **kwargs):
                raise AssertionError("should not be called")

        def lose_lease():
            raise RuntimeError("lease lost")

        with self.assertRaisesRegex(RuntimeError, "lease lost"):
            collect_advice(FakeParsed(), Client(), on_progress=lose_lease)

    def test_process_advice_requests_reports_unexpected_adapter_errors(self):
        from worker.client import process_advice_requests

        class FakeWorker:
            def __init__(self):
                self.submitted = None
                self.claims = 1

            def claim_advice(self):
                if self.claims == 0:
                    return None
                self.claims -= 1
                return {
                    "request": 9,
                    "claim_token": "token-9",
                    "transaction": {
                        "description": "X",
                        "amount_pence": -1,
                        "account_kind": "current",
                    },
                }

            def submit_advice(self, request_id, payload):
                self.submitted = (request_id, payload)
                return {"status": "failed"}

        class BrokenInference:
            def suggest_classification(self, **kwargs):
                raise TypeError("adapter bug")

        worker = FakeWorker()
        results = list(process_advice_requests(worker, BrokenInference()))

        self.assertEqual(results, [{"advice_request": 9, "status": "failed"}])
        self.assertEqual(worker.submitted[0], 9)
        self.assertEqual(worker.submitted[1]["outcome"], "failed")
        self.assertEqual(worker.submitted[1]["failure"], "TypeError")



class AdvicePublicationTests(UploadSetupMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.credential, self.token = WorkerCredential.issue("advice-laptop")
        self.upload(text_pdf(), filename="advice.pdf")
        self.upload_record = Upload.objects.get(filename="advice.pdf")
        self.client.post(reverse("jobs:process_now"))
        response = self.client.post(
            reverse("jobs:claim"),
            data=json.dumps(None),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {self.token}",
        )
        self.claim_data = response.json()

    def payload(self, suggestions):
        return {
            "version": 1,
            "attempt": self.claim_data["attempt"],
            "outcome": "imported",
            "issues": [],
            "sections": [
                {
                    "name": "lloyds_current",
                    "account_role": "primary",
                    "status": "ok",
                    "account_kind_hint": "current",
                    "issues": [],
                    "transactions": [
                        {
                            "posted_on": "2026-08-01",
                            "source_transaction_date": None,
                            "description": "SHOP",
                            "transaction_type": "Card payment",
                            "amount_pence": -320,
                            "balance_pence": 119680,
                            "page": 1,
                            "row": 1,
                            "source_text": "SHOP",
                        },
                        {
                            "posted_on": "2026-08-02",
                            "source_transaction_date": None,
                            "description": "TO SOMEONE",
                            "transaction_type": "Others",
                            "amount_pence": -500,
                            "balance_pence": 119180,
                            "page": 1,
                            "row": 2,
                            "source_text": "TO SOMEONE",
                        },
                        {
                            "posted_on": "2026-08-03",
                            "source_transaction_date": None,
                            "description": "SALARY",
                            "transaction_type": "Salary",
                            "amount_pence": 250000,
                            "balance_pence": 369180,
                            "page": 1,
                            "row": 3,
                            "source_text": "SALARY",
                        },
                    ],
                    "balances": [
                        {
                            "kind": "opening",
                            "observed_on": "2026-07-31",
                            "amount_pence": 120000,
                        },
                        {
                            "kind": "closing",
                            "observed_on": "2026-08-31",
                            "amount_pence": 369180,
                        },
                    ],
                    "suggestions": suggestions,
                    "stated_totals": {
                        "money_in_pence": 250000,
                        "money_out_pence": 820,
                    },
                }
            ],
        }

    def submit(self, payload):
        return self.client.post(
            reverse("jobs:result", args=[self.claim_data["job"]]),
            data=json.dumps(payload),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {self.token}",
        )

    def suggestion(self, row, classification="transfer", **overrides):
        entry = {
            "page": 1,
            "row": row,
            "version": 1,
            "classification": classification,
            "confidence": 0.8,
            "explanation": "Likely an own-account transfer.",
            "model": "fake-model",
            "prompt_version": "v1",
        }
        entry.update(overrides)
        return entry

    def test_advice_is_kept_separate_and_only_for_unresolved_rows(self):
        response = self.submit(
            self.payload(
                [
                    self.suggestion(2),
                    # Deterministic evidence already classifies row 1: advice ignored.
                    self.suggestion(1, classification="spending"),
                ]
            )
        )

        self.assertEqual(response.status_code, 200)
        suggestions = list(ClassificationSuggestion.objects.all())
        self.assertEqual(len(suggestions), 1)
        self.assertEqual(suggestions[0].transaction.source_row, 2)
        self.assertEqual(suggestions[0].classification, "transfer")
        self.assertEqual(Correction.objects.count(), 0)

        unresolved = Transaction.objects.get(source_row=2)
        review = self.client.get(reverse("ledger:review_detail", args=[unresolved.pk]))
        self.assertContains(review, "Local suggestion")
        self.assertContains(review, "Likely an own-account transfer.")
        self.assertContains(review, "fake-model")

    def test_malformed_advice_is_dropped_without_failing_the_import(self):
        response = self.submit(
            self.payload(
                [
                    self.suggestion(2, classification="loan"),
                    self.suggestion(2, confidence=3.0),
                    "not-a-dict",
                    {**self.suggestion(2), "row": 99},
                    self.suggestion(2, explanation=""),
                    self.suggestion(2, classification=[]),
                    self.suggestion(2, classification={}),
                    self.suggestion(2, classification=None),
                ]
            )
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["outcome"], "imported")
        self.assertEqual(ClassificationSuggestion.objects.count(), 0)

    def test_non_list_advice_field_does_not_reject_financial_facts(self):
        response = self.submit(self.payload({"unexpected": True}))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["outcome"], "imported")
        self.assertEqual(ClassificationSuggestion.objects.count(), 0)
        self.assertEqual(Transaction.objects.count(), 3)

    def test_advice_never_changes_totals_until_explicitly_confirmed(self):
        self.submit(self.payload([self.suggestion(2)]))

        dashboard = self.client.get("/?month=2026-08")
        self.assertContains(dashboard, "Provisional: 1")

        unresolved = Transaction.objects.get(source_row=2)
        suggestion = ClassificationSuggestion.objects.get()
        response = self.client.post(
            reverse("ledger:review_detail", args=[unresolved.pk]),
            {"action": "accept_advice", "suggestion": suggestion.pk},
        )

        self.assertEqual(response.status_code, 302)
        suggestion.refresh_from_db()
        self.assertIsNotNone(suggestion.accepted_at)
        correction = Correction.objects.get()
        self.assertEqual(correction.classification, "transfer")
        self.assertIn("Accepted local suggestion", correction.note)
        dashboard = self.client.get("/?month=2026-08")
        self.assertNotContains(dashboard, "Provisional: 1")

    def test_stale_advice_cannot_override_a_newer_manual_correction(self):
        self.submit(self.payload([self.suggestion(2)]))
        unresolved = Transaction.objects.get(source_row=2)
        suggestion = ClassificationSuggestion.objects.get()

        manual = self.client.post(
            reverse("ledger:review_detail", args=[unresolved.pk]),
            {"action": "correct", "classification": "unknown", "note": "manual decision"},
        )
        self.assertEqual(manual.status_code, 302)

        stale = self.client.post(
            reverse("ledger:review_detail", args=[unresolved.pk]),
            {"action": "accept_advice", "suggestion": suggestion.pk},
        )

        self.assertEqual(stale.status_code, 400)
        self.assertContains(
            stale,
            "A correction was confirmed after this suggestion",
            status_code=400,
        )
        active = Correction.objects.filter(
            transaction=unresolved, reverted_at__isnull=True
        )
        self.assertEqual(active.count(), 1)
        self.assertEqual(active.get().note, "manual decision")
        suggestion.refresh_from_db()
        self.assertIsNone(suggestion.accepted_at)

    def test_dismissing_advice_has_no_financial_effect(self):
        self.submit(self.payload([self.suggestion(2)]))
        unresolved = Transaction.objects.get(source_row=2)
        suggestion = ClassificationSuggestion.objects.get()

        response = self.client.post(
            reverse("ledger:review_detail", args=[unresolved.pk]),
            {"action": "dismiss_advice", "suggestion": suggestion.pk},
        )

        self.assertEqual(response.status_code, 302)
        suggestion.refresh_from_db()
        self.assertIsNotNone(suggestion.dismissed_at)
        self.assertEqual(Correction.objects.count(), 0)
        review = self.client.get(reverse("ledger:review_detail", args=[unresolved.pk]))
        self.assertNotContains(review, "Local suggestion")
