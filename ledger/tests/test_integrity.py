"""Behavioral tests for preserving corrections across repeated processing."""

import json

from django.test import TestCase
from django.urls import reverse

from interpretation.lloyds_current import parse
from jobs.models import WorkerCredential
from ledger.models import Correction, Transaction, Upload
from ledger.tests.statement_fixtures import extract_text, lloyds_current_pdf
from ledger.tests.support import UploadSetupMixin
from worker.client import build_result


class CorrectionDurabilityTests(UploadSetupMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.credential, self.token = WorkerCredential.issue("integrity-laptop")
        self.pdf = lloyds_current_pdf()

    def import_upload(self, filename):
        self.upload(self.pdf, filename=filename)
        receipt = Upload.objects.get(filename=filename)
        self.client.post(reverse("jobs:process_now"))
        claim = self.client.post(
            reverse("jobs:claim"),
            data=json.dumps(None),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {self.token}",
        ).json()
        payload = build_result(claim, parse(extract_text(self.pdf)))
        response = self.client.post(
            reverse("jobs:result", args=[claim["job"]]),
            data=json.dumps(payload),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {self.token}",
        )
        return receipt, response

    def test_confirmed_correction_survives_reimport_of_the_same_original(self):
        _receipt, first = self.import_upload("first.pdf")
        self.assertEqual(first.status_code, 200)
        coffee = Transaction.objects.get(description="COFFEE SHOP")
        response = self.client.post(
            reverse("ledger:review_detail", args=[coffee.pk]),
            {"action": "correct", "classification": "transfer", "note": "Own transfer"},
        )
        self.assertEqual(response.status_code, 302)
        correction_count = Correction.objects.count()
        count_before = Transaction.objects.count()

        _second_receipt, second = self.import_upload("second.pdf")

        self.assertEqual(second.status_code, 200)
        self.assertEqual(second.json()["outcome"], "duplicate")
        self.assertEqual(Transaction.objects.count(), count_before)
        coffee.refresh_from_db()
        self.assertEqual(coffee.corrections.count(), correction_count)
        self.assertEqual(
            list(coffee.corrections.values_list("classification", "reverted_at")),
            [("transfer", None)],
        )
