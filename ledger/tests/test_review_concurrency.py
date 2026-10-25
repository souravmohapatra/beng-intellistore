"""Concurrent review decisions must leave exactly one active correction."""

from datetime import date
from threading import Barrier, Thread

from django.contrib.auth import get_user_model
from django.db import connections
from django.test import Client, TransactionTestCase
from django.urls import reverse

from ledger.models import Correction, Transaction, Upload
from ledger.tests.fixtures import text_pdf
from ledger.tests.support import UploadSetupMixin


class ConcurrentCorrectionTests(UploadSetupMixin, TransactionTestCase):
    def setUp(self):
        super().setUp()
        self.upload(text_pdf(), filename="concurrent.pdf")
        receipt = Upload.objects.get(filename="concurrent.pdf")
        self.transaction = Transaction.objects.create(
            account=self.account,
            upload=receipt,
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

    def test_two_simultaneous_corrections_leave_one_active_decision(self):
        barrier = Barrier(2)
        statuses = []

        def submit(classification):
            try:
                client = Client()
                client.force_login(
                    get_user_model().objects.get(username="sourav")
                )
                barrier.wait(timeout=10)
                response = client.post(
                    reverse("ledger:review_detail", args=[self.transaction.pk]),
                    {
                        "action": "correct",
                        "classification": classification,
                        "note": f"concurrent {classification}",
                    },
                )
                statuses.append(response.status_code)
            finally:
                connections.close_all()

        threads = [Thread(target=submit, args=(value,)) for value in ("spending", "transfer")]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=20)

        self.assertEqual(sorted(statuses), [302, 302])
        corrections = Correction.objects.filter(transaction=self.transaction)
        self.assertEqual(corrections.count(), 2)
        self.assertEqual(corrections.filter(reverted_at__isnull=True).count(), 1)
