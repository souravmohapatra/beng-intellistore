"""Behavioral tests for conservative overlap and duplicate handling."""

import json
from datetime import date

from django.test import TestCase
from django.urls import reverse

from interpretation.lloyds_current import parse
from jobs.models import WorkerCredential
from ledger.models import Account, AccountKind, DuplicateMatch, Transaction, Upload
from ledger.tests.statement_fixtures import extract_text, lloyds_current_pages, statement_pdf
from ledger.tests.statement_fixtures import lloyds_current_pdf
from ledger.tests.support import UploadSetupMixin
from reporting.totals import compute_totals
from worker.client import build_result


class PublishMixin(UploadSetupMixin):
    def setUp(self):
        super().setUp()
        self.credential, self.token = WorkerCredential.issue("overlap-laptop")

    def publish(self, pdf, filename, account=None):
        self.upload(pdf, filename=filename, account=account or self.account)
        self.client.post(reverse("jobs:process_now"))
        claim = self.client.post(
            reverse("jobs:claim"),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {self.token}",
        ).json()
        payload = build_result(claim, parse(extract_text(pdf)))
        return self.client.post(
            reverse("jobs:result", args=[claim["job"]]),
            data=json.dumps(payload),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {self.token}",
        )

    def totals(self, start=date(2026, 8, 1), end=date(2026, 8, 31)):
        return compute_totals(start, end)


class IdenticalOriginalTests(PublishMixin, TestCase):
    def test_repeated_identical_bytes_add_one_set_of_effects(self):
        first = self.publish(lloyds_current_pdf(), "lloyds.pdf")
        second = self.publish(lloyds_current_pdf(), "lloyds-copy.pdf")

        self.assertEqual(first.json()["outcome"], "imported")
        self.assertEqual(second.json()["outcome"], "duplicate")
        self.assertEqual(Transaction.objects.count(), 6)
        statuses = list(Upload.objects.order_by("pk").values_list("status", flat=True))
        self.assertEqual(statuses, [Upload.Status.IMPORTED, Upload.Status.DUPLICATE])
        detail = self.client.get(
            reverse("ledger:upload_detail", args=[Upload.objects.latest("pk").pk])
        )
        self.assertContains(detail, "already_imported")

    def test_same_bytes_for_a_different_account_still_imports(self):
        other = Account.objects.create(name="Second Current", kind=AccountKind.CURRENT)
        self.publish(lloyds_current_pdf(), "first.pdf")
        second = self.publish(lloyds_current_pdf(), "second.pdf", account=other)

        self.assertEqual(second.json()["outcome"], "imported")
        self.assertEqual(Transaction.objects.count(), 12)


class OverlapCandidateTests(PublishMixin, TestCase):
    def variant_pdf(self):
        pages = lloyds_current_pages()
        pages[0].append("Statement note")
        return statement_pdf(pages)

    def test_overlapping_rows_are_flagged_and_both_sources_retained(self):
        self.publish(lloyds_current_pdf(), "august.pdf")
        self.publish(self.variant_pdf(), "august-again.pdf")

        self.assertEqual(Transaction.objects.count(), 12)
        flagged = Transaction.objects.filter(needs_review=True)
        self.assertEqual(flagged.count(), 12)
        self.assertEqual(
            set(flagged.values_list("upload__filename", flat=True)),
            {"august.pdf", "august-again.pdf"},
        )
        report = self.totals()
        self.assertTrue(report.provisional)
        self.assertGreater(report.spending_pence, 0)

    def test_identical_rows_within_one_original_are_not_candidates(self):
        from jobs.publication import _flag_overlap_candidates

        self.upload(lloyds_current_pdf(), filename="same.pdf")
        second = Transaction.objects.create(
            account=self.account,
            upload=Upload.objects.latest("pk"),
            posted_on=date(2026, 8, 1),
            description="COFFEE SHOP",
            transaction_type="Card payment",
            amount_pence=-320,
            balance_pence=1000,
            source_page=1,
            source_row=1,
            source_text="x",
        )

        _flag_overlap_candidates([second])

        second.refresh_from_db()
        self.assertFalse(second.needs_review)


class DuplicateDecisionTests(PublishMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.upload(b"a", filename="a.pdf")
        self.upload_a = Upload.objects.latest("pk")
        self.upload(b"b", filename="b.pdf")
        self.upload_b = Upload.objects.latest("pk")
        self.first = self._txn(self.upload_a, -500)
        self.second = self._txn(self.upload_b, -500)

    def _txn(self, upload, amount):
        return Transaction.objects.create(
            account=self.account,
            upload=upload,
            posted_on=date(2026, 8, 9),
            description="SAME SHOP",
            transaction_type="DD",
            amount_pence=amount,
            balance_pence=None,
            source_page=1,
            source_row=1,
            source_text="x",
            needs_review=True,
        )

    def test_confirmed_duplicate_suppresses_one_effect_and_keeps_both_rows(self):
        page = self.client.get(reverse("ledger:review_detail", args=[self.second.pk]))
        self.assertContains(page, "Possible overlap")
        self.assertContains(page, "a.pdf")

        self.client.post(
            reverse("ledger:review_detail", args=[self.second.pk]),
            {"action": "duplicate", "peer": self.first.pk},
        )

        self.assertEqual(DuplicateMatch.objects.count(), 1)
        self.assertTrue(Transaction.objects.filter(pk=self.first.pk).exists())
        self.assertTrue(Transaction.objects.filter(pk=self.second.pk).exists())
        report = self.totals()
        self.assertEqual(report.spending_pence, 500)
        self.assertFalse(report.provisional)

    def test_keep_both_clears_review_and_counts_both(self):
        self.client.post(
            reverse("ledger:review_detail", args=[self.second.pk]),
            {"action": "keep_both"},
        )

        self.assertEqual(DuplicateMatch.objects.count(), 0)
        self.assertFalse(Transaction.objects.get(pk=self.second.pk).needs_review)
        self.assertEqual(self.totals().spending_pence, 1000)

    def test_reciprocal_confirmations_cannot_erase_all_effects(self):
        self.client.post(
            reverse("ledger:review_detail", args=[self.second.pk]),
            {"action": "duplicate", "peer": self.first.pk},
        )

        response = self.client.post(
            reverse("ledger:review_detail", args=[self.first.pk]),
            {"action": "duplicate", "peer": self.second.pk},
        )

        self.assertEqual(response.status_code, 400)
        self.assertContains(response, "canonical row", status_code=400)
        self.assertEqual(DuplicateMatch.objects.count(), 1)
        self.assertEqual(self.totals().spending_pence, 500)

    def test_a_suppressed_row_cannot_become_the_canonical_target(self):
        third_upload = self.upload_b
        self.client.post(
            reverse("ledger:review_detail", args=[self.second.pk]),
            {"action": "duplicate", "peer": self.first.pk},
        )
        third = Transaction.objects.create(
            account=self.account,
            upload=third_upload,
            posted_on=self.second.posted_on,
            description=self.second.description,
            transaction_type="DD",
            amount_pence=self.second.amount_pence,
            balance_pence=None,
            source_page=1,
            source_row=2,
            source_text="x",
            needs_review=True,
        )

        response = self.client.post(
            reverse("ledger:review_detail", args=[third.pk]),
            {"action": "duplicate", "peer": self.second.pk},
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(DuplicateMatch.objects.count(), 1)

    def test_duplicate_action_rejects_non_matching_peers(self):
        other = Transaction.objects.create(
            account=self.account,
            upload=self.upload_b,
            posted_on=date(2026, 8, 10),
            description="DIFFERENT",
            transaction_type="DD",
            amount_pence=-500,
            balance_pence=None,
            source_page=1,
            source_row=2,
            source_text="x",
        )

        self.client.post(
            reverse("ledger:review_detail", args=[self.second.pk]),
            {"action": "duplicate", "peer": other.pk},
        )

        self.assertEqual(DuplicateMatch.objects.count(), 0)
