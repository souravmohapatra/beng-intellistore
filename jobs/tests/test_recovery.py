"""Behavioral tests for lease expiry, retries and recovery status."""

import json
import shutil
import tempfile
from datetime import timedelta
from pathlib import Path

from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from jobs.models import Job, JobAttempt, WorkerCredential
from ledger.models import Upload
from ledger.tests.fixtures import CSV_TEXT
from ledger.tests.support import UploadSetupMixin
from worker.client import cleanup_stale


class RecoveryTestCase(UploadSetupMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.credential, self.token = WorkerCredential.issue("recovery-laptop")

    def api(self, name, args=(), payload=None):
        return self.client.post(
            reverse(name, args=args),
            data=json.dumps(payload) if payload is not None else "",
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {self.token}",
        )

    def release(self):
        self.client.post(reverse("jobs:process_now"))

    def claim(self):
        return self.api("jobs:claim")

    def expire_lease(self):
        JobAttempt.objects.filter(finished_at__isnull=True).update(
            lease_expires_at=timezone.now() - timedelta(seconds=1)
        )

    def job(self):
        return Job.objects.get()


class LeaseTests(RecoveryTestCase):
    def test_claim_sets_a_lease_and_progress_renews_it(self):
        self.upload(CSV_TEXT)
        self.release()
        claim = self.claim().json()
        attempt = JobAttempt.objects.get(pk=claim["attempt"])
        original_expiry = attempt.lease_expires_at

        response = self.api(
            "jobs:progress", args=[claim["job"]], payload={"stage": "downloaded"}
        )

        self.assertEqual(response.status_code, 200)
        attempt.refresh_from_db()
        self.assertGreaterEqual(attempt.lease_expires_at, original_expiry)
        self.assertIsNotNone(attempt.heartbeat_at)

    def test_heartbeat_renews_the_lease(self):
        self.upload(CSV_TEXT)
        self.release()
        claim = self.claim().json()
        attempt = JobAttempt.objects.get(pk=claim["attempt"])
        attempt.lease_expires_at = timezone.now() + timedelta(seconds=1)
        attempt.save(update_fields=["lease_expires_at"])

        response = self.api("jobs:heartbeat", args=[claim["job"]])

        self.assertEqual(response.status_code, 200)
        attempt.refresh_from_db()
        self.assertGreater(attempt.lease_expires_at, timezone.now())

    def test_lost_lease_is_reported_to_the_worker(self):
        self.upload(CSV_TEXT)
        self.release()
        claim = self.claim().json()
        self.expire_lease()

        self.assertEqual(self.api("jobs:heartbeat", args=[claim["job"]]).status_code, 409)
        self.assertEqual(self.api("jobs:progress", args=[claim["job"]]).status_code, 409)


class ExpiryRetryTests(RecoveryTestCase):
    @override_settings(WORKER_RETRY_DELAYS=(0, 0))
    def test_expired_attempt_is_retried_and_counted(self):
        self.upload(CSV_TEXT)
        self.release()
        first = self.claim().json()
        self.expire_lease()

        second = self.claim().json()

        self.assertEqual(second["job"], first["job"])
        self.assertEqual(second["attempts_remaining"], 1)
        self.assertEqual(JobAttempt.objects.get(pk=first["attempt"]).outcome, "expired")
        self.assertEqual(self.job().attempts_used, 2)

    @override_settings(WORKER_RETRY_DELAYS=(60, 120))
    def test_retry_waits_for_the_backoff_delay(self):
        self.upload(CSV_TEXT)
        self.release()
        self.claim()
        self.expire_lease()

        self.assertEqual(self.claim().status_code, 204)
        job = self.job()
        self.assertIsNotNone(job.available_at)
        self.assertGreater(job.available_at, timezone.now())

    @override_settings(WORKER_RETRY_DELAYS=(0, 0))
    def test_three_expired_attempts_fail_visibly_and_manual_retry_recovers(self):
        self.upload(CSV_TEXT)
        self.release()
        for _ in range(3):
            self.claim()
            self.expire_lease()

        self.assertEqual(self.claim().status_code, 204)
        job = self.job()
        self.assertEqual(job.status, Job.Status.FAILED)
        self.assertEqual(job.attempts_used, 3)
        self.assertTrue(job.last_failure)
        detail = self.client.get(reverse("ledger:upload_detail", args=[job.upload_id]))
        self.assertContains(detail, "Retry processing")
        self.assertContains(detail, "3 attempt(s) used")

        retry = self.client.post(reverse("jobs:retry", args=[job.upload_id]))

        self.assertEqual(retry.status_code, 302)
        job.refresh_from_db()
        self.assertEqual(job.status, Job.Status.RELEASED)
        self.assertEqual(job.attempts_used, 0)
        self.assertEqual(self.claim().status_code, 200)

    @override_settings(WORKER_RETRY_DELAYS=(0, 0))
    def test_a_failed_upload_does_not_block_other_uploads(self):
        self.upload(CSV_TEXT, filename="first.txt")
        self.upload(CSV_TEXT, filename="second.txt")
        self.release()
        for _ in range(4):
            self.claim()
            self.expire_lease()

        self.assertEqual(
            Job.objects.filter(status=Job.Status.FAILED).count(), 1
        )
        claim = self.claim()
        self.assertEqual(claim.status_code, 200)
        self.assertEqual(claim.json()["upload"]["filename"], "second.txt")

    def test_manual_retry_is_ignored_for_jobs_that_are_not_failed(self):
        self.upload(CSV_TEXT)
        job = self.job()

        self.client.post(reverse("jobs:retry", args=[job.upload_id]))

        job.refresh_from_db()
        self.assertEqual(job.status, Job.Status.WAITING)


class WorkerCleanupTests(TestCase):
    def test_stale_temporary_directories_are_removed(self):
        root = Path(tempfile.mkdtemp())
        self.addCleanup(lambda: shutil.rmtree(root, ignore_errors=True))
        stale = root / "stale"
        recent = root / "recent"
        stale.mkdir()
        recent.mkdir()
        import os

        os.utime(stale, (1, 1))

        removed = cleanup_stale(root, older_than_seconds=3600)

        self.assertEqual(removed, [stale])
        self.assertFalse(stale.exists())
        self.assertTrue(recent.exists())
