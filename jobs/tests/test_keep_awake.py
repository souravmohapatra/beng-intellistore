"""Behavioral tests for application-owned keep-awake leases."""

import json
import threading
import time
from datetime import datetime, timedelta
from unittest.mock import patch
from zoneinfo import ZoneInfo

from django.db import connections, transaction
from django.test import TestCase, TransactionTestCase, override_settings
from django.urls import reverse

from jobs.controller import (
    ControllerLease,
    ControllerRejected,
    ControllerUnavailable,
)
from jobs.keep_awake import renew_keep_awake
from jobs.models import Job, JobAttempt, KeepAwakeLease, WorkerCredential
from ledger.tests.fixtures import CSV_TEXT
from ledger.tests.support import UploadSetupMixin


LONDON = ZoneInfo("Europe/London")
NOW = datetime(2026, 10, 22, 21, 0, tzinfo=LONDON)
CEILING = timedelta(hours=8)


class RecordingController:
    """Records app-owned lease actions; never talks to a real controller."""

    def __init__(self):
        self.created = []
        self.extended = []
        self.released = []
        self.create_error = None
        self.extend_error = None
        self.release_error = None
        self.created_at = NOW
        self.expires_at = NOW
        self.ceiling_at = NOW + CEILING
        self.next_lease = "lease-one"

    def request_wake(self):
        return None

    def create_lease(self, seconds):
        if self.create_error is not None:
            raise self.create_error
        self.created.append(seconds)
        self.expires_at = self.created_at + timedelta(seconds=seconds)
        self.ceiling_at = self.created_at + CEILING
        return ControllerLease(self.next_lease, self.created_at, self.expires_at)

    def extend_lease(self, lease_id, seconds):
        if self.extend_error is not None:
            raise self.extend_error
        self.extended.append((lease_id, seconds))
        self.expires_at = min(
            self.expires_at + timedelta(seconds=seconds), self.ceiling_at
        )
        return ControllerLease(lease_id, self.created_at, self.expires_at)

    def release_lease(self, lease_id):
        if self.release_error is not None:
            raise self.release_error
        self.released.append(lease_id)
        return lease_id


class SlowExtendController(RecordingController):
    def extend_lease(self, lease_id, seconds):
        time.sleep(0.1)
        return super().extend_lease(lease_id, seconds)


class ConcurrentRenewalTests(UploadSetupMixin, TransactionTestCase):
    def setUp(self):
        super().setUp()
        self.credential, _ = WorkerCredential.issue("concurrent-renewal")
        self.upload(CSV_TEXT, filename="concurrent-renewal.csv")
        job = Job.objects.get(upload__filename="concurrent-renewal.csv")
        job.status = Job.Status.PROCESSING
        job.attempts_used = 1
        job.save(update_fields=["status", "attempts_used"])
        self.attempt = JobAttempt.objects.create(
            job=job,
            number=1,
            credential=self.credential,
            lease_expires_at=NOW + timedelta(hours=1),
        )
        KeepAwakeLease.objects.create(
            attempt=self.attempt,
            lease_id="lease-one",
            created_at=NOW,
            expires_at=NOW + timedelta(seconds=1200),
            ceiling_at=NOW + CEILING,
        )

    def test_parallel_renewals_apply_one_extension(self):
        controller = SlowExtendController()
        controller.expires_at = NOW + timedelta(seconds=1200)
        renew_at = NOW + timedelta(seconds=901)
        barrier = threading.Barrier(2)
        errors = []

        def renew():
            try:
                barrier.wait(timeout=2)
                renew_keep_awake(self.attempt, controller=controller, now=renew_at)
            except Exception as exc:  # pragma: no cover - surfaced below
                errors.append(exc)
            finally:
                connections.close_all()

        threads = [threading.Thread(target=renew) for _ in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=5)

        self.assertFalse(errors)
        self.assertEqual(controller.extended, [("lease-one", 600)])
        lease = KeepAwakeLease.objects.get(attempt=self.attempt)
        self.assertEqual(lease.expires_at, NOW + timedelta(seconds=1800))
        self.assertEqual(lease.failure, "")


class KeepAwakeTests(UploadSetupMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.controller = RecordingController()
        self.credential, self.token = WorkerCredential.issue("keep-awake-test")
        self.upload(CSV_TEXT, filename="keep-awake.csv")
        self.job = Job.objects.get(upload__filename="keep-awake.csv")

    def api(self, method, name, payload=None, *, args=()):
        kwargs = {
            "content_type": "application/json",
            "HTTP_AUTHORIZATION": f"Bearer {self.token}",
        }
        if payload is not None:
            kwargs["data"] = json.dumps(payload)
        return getattr(self.client, method)(reverse(name, args=args), **kwargs)

    def claim(self, at=NOW, lease_seconds=3600):
        self.job.status = Job.Status.RELEASED
        self.job.released_at = at
        self.job.save(update_fields=["status", "released_at"])
        with (
            override_settings(
                LAPTOP_CONTROLLER=self.controller,
                WORKER_LEASE_SECONDS=lease_seconds,
            ),
            patch("django.utils.timezone.now", return_value=at),
            self.captureOnCommitCallbacks(execute=True),
        ):
            response = self.api("post", "jobs:claim")
        self.assertEqual(response.status_code, 200)
        return response.json()

    def active_lease(self):
        return KeepAwakeLease.objects.get(attempt__job=self.job)

    def test_claim_creates_one_bounded_lease_for_the_attempt(self):
        claimed = self.claim()

        lease = self.active_lease()
        self.assertEqual(self.controller.created, [1200])
        self.assertEqual(lease.lease_id, "lease-one")
        self.assertEqual(lease.attempt_id, claimed["attempt"])
        self.assertEqual(lease.created_at, NOW)
        self.assertEqual(lease.expires_at, NOW + timedelta(seconds=1200))
        self.assertEqual(lease.ceiling_at, NOW + CEILING)
        self.assertIsNone(lease.released_at)

    def test_progress_extends_only_when_the_lease_is_near_expiry(self):
        claimed = self.claim()

        with (
            override_settings(LAPTOP_CONTROLLER=self.controller),
            patch("django.utils.timezone.now", return_value=NOW + timedelta(seconds=899)),
        ):
            response = self.api(
                "post",
                "jobs:progress",
                {"stage": "parsing"},
                args=[claimed["job"]],
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.controller.extended, [])

        extended_at = NOW + timedelta(seconds=901)
        with (
            override_settings(LAPTOP_CONTROLLER=self.controller),
            patch("django.utils.timezone.now", return_value=extended_at),
        ):
            response = self.api(
                "post",
                "jobs:progress",
                {"stage": "validating"},
                args=[claimed["job"]],
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.controller.extended, [("lease-one", 600)])
        lease = self.active_lease()
        self.assertEqual(
            lease.expires_at, NOW + timedelta(seconds=1800)
        )
        self.assertIsNotNone(lease.last_extended_at)

    def test_duplicate_renewal_requests_do_not_accumulate_extension(self):
        claimed = self.claim()
        renew_at = NOW + timedelta(seconds=901)

        with (
            override_settings(LAPTOP_CONTROLLER=self.controller),
            patch("django.utils.timezone.now", return_value=renew_at),
        ):
            for stage in ("parsing", "validating"):
                response = self.api(
                    "post",
                    "jobs:progress",
                    {"stage": stage},
                    args=[claimed["job"]],
                )
                self.assertEqual(response.status_code, 200)

        self.assertEqual(self.controller.extended, [("lease-one", 600)])

    def test_heartbeat_also_renews_the_application_lease(self):
        claimed = self.claim()

        with (
            override_settings(LAPTOP_CONTROLLER=self.controller),
            patch("django.utils.timezone.now", return_value=NOW + timedelta(seconds=901)),
        ):
            response = self.api(
                "post", "jobs:heartbeat", args=[claimed["job"]]
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.controller.extended, [("lease-one", 600)])

    def test_renewal_is_capped_by_the_eight_hour_creation_ceiling(self):
        claimed = self.claim()
        lease = self.active_lease()
        self.controller.expires_at = NOW + CEILING - timedelta(seconds=50)
        lease.expires_at = NOW + CEILING - timedelta(seconds=50)
        lease.save(update_fields=["expires_at"])
        attempt = JobAttempt.objects.get(pk=claimed["attempt"])

        with (
            override_settings(LAPTOP_CONTROLLER=self.controller),
            patch(
                "django.utils.timezone.now",
                return_value=NOW + CEILING - timedelta(seconds=100),
            ),
        ):
            renew_keep_awake(attempt)

        self.assertEqual(self.controller.extended, [("lease-one", 100)])

        with (
            override_settings(LAPTOP_CONTROLLER=self.controller),
            patch(
                "django.utils.timezone.now",
                return_value=NOW + CEILING + timedelta(seconds=1),
            ),
        ):
            renew_keep_awake(attempt)

        self.assertEqual(self.controller.extended, [("lease-one", 100)])
        lease.refresh_from_db()
        self.assertIn("eight-hour", lease.failure)

    def test_completed_result_releases_only_the_application_lease(self):
        claimed = self.claim()
        payload = {
            "version": 1,
            "attempt": claimed["attempt"],
            "outcome": "unsupported",
            "issues": [
                {"code": "unsupported_layout", "message": "No layout implemented."}
            ],
        }

        with (
            override_settings(LAPTOP_CONTROLLER=self.controller),
            patch("django.utils.timezone.now", return_value=NOW + timedelta(minutes=1)),
            self.captureOnCommitCallbacks(execute=True),
        ):
            response = self.api(
                "post", "jobs:result", payload, args=[claimed["job"]]
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.controller.released, ["lease-one"])
        lease = self.active_lease()
        self.assertIsNotNone(lease.released_at)
        self.assertEqual(lease.failure, "")

    def test_claim_rollback_does_not_create_a_kept_awake_lease(self):
        self.job.status = Job.Status.RELEASED
        self.job.released_at = NOW
        self.job.save(update_fields=["status", "released_at"])

        with (
            override_settings(
                LAPTOP_CONTROLLER=self.controller,
                WORKER_LEASE_SECONDS=3600,
            ),
            patch("django.utils.timezone.now", return_value=NOW),
            self.captureOnCommitCallbacks(execute=True),
            transaction.atomic(),
        ):
            response = self.api("post", "jobs:claim")
            self.assertEqual(response.status_code, 200)
            transaction.set_rollback(True)

        self.assertEqual(self.controller.created, [])
        self.assertFalse(KeepAwakeLease.objects.exists())

    def test_result_rollback_does_not_release_the_kept_awake_lease(self):
        claimed = self.claim()
        payload = {
            "version": 1,
            "attempt": claimed["attempt"],
            "outcome": "unsupported",
            "issues": [
                {"code": "unsupported_layout", "message": "No layout implemented."}
            ],
        }

        with (
            override_settings(LAPTOP_CONTROLLER=self.controller),
            patch("django.utils.timezone.now", return_value=NOW + timedelta(minutes=1)),
            self.captureOnCommitCallbacks(execute=True),
            transaction.atomic(),
        ):
            response = self.api(
                "post", "jobs:result", payload, args=[claimed["job"]]
            )
            self.assertEqual(response.status_code, 200)
            transaction.set_rollback(True)

        self.assertEqual(self.controller.released, [])
        lease = self.active_lease()
        self.assertIsNone(lease.released_at)

    def test_controller_failure_does_not_block_claim(self):
        self.controller.create_error = ControllerUnavailable("controller down")

        claimed = self.claim()

        self.assertEqual(claimed["job"], self.job.pk)
        self.job.refresh_from_db()
        self.assertEqual(self.job.status, Job.Status.PROCESSING)
        self.assertFalse(KeepAwakeLease.objects.exists())

    def test_expired_attempt_releases_its_lease_after_commit(self):
        self.claim(lease_seconds=120)
        lease_id = self.active_lease().lease_id

        with (
            override_settings(
                LAPTOP_CONTROLLER=self.controller,
                WORKER_MAX_ATTEMPTS=1,
            ),
            patch(
                "django.utils.timezone.now",
                return_value=NOW + timedelta(seconds=121),
            ),
            self.captureOnCommitCallbacks(execute=True),
        ):
            response = self.api("post", "jobs:claim")

        self.assertEqual(response.status_code, 204)
        self.assertEqual(self.controller.released, [lease_id])
        self.job.refresh_from_db()
        self.assertEqual(self.job.status, Job.Status.FAILED)
        self.assertIsNotNone(KeepAwakeLease.objects.get().released_at)

    def test_missing_lease_is_marked_inactive_on_renewal(self):
        claimed = self.claim()
        lease = self.active_lease()
        self.controller.extend_error = ControllerRejected("lease missing", 404)

        with (
            override_settings(LAPTOP_CONTROLLER=self.controller),
            patch("django.utils.timezone.now", return_value=NOW + timedelta(seconds=901)),
        ):
            response = self.api(
                "post",
                "jobs:progress",
                {"stage": "parsing"},
                args=[claimed["job"]],
            )

        self.assertEqual(response.status_code, 200)
        lease.refresh_from_db()
        self.assertIsNotNone(lease.released_at)
        self.assertIn("no longer exists", lease.failure)

    def test_release_failure_keeps_the_lease_record_bounded(self):
        claimed = self.claim()
        self.controller.release_error = ControllerUnavailable("controller down")
        payload = {
            "version": 1,
            "attempt": claimed["attempt"],
            "outcome": "unsupported",
            "issues": [
                {"code": "unsupported_layout", "message": "No layout implemented."}
            ],
        }

        with (
            override_settings(LAPTOP_CONTROLLER=self.controller),
            patch("django.utils.timezone.now", return_value=NOW + timedelta(minutes=1)),
            self.captureOnCommitCallbacks(execute=True),
        ):
            response = self.api(
                "post", "jobs:result", payload, args=[claimed["job"]]
            )

        self.assertEqual(response.status_code, 200)
        lease = self.active_lease()
        self.assertIsNone(lease.released_at)
        self.assertIn("release", lease.failure)
