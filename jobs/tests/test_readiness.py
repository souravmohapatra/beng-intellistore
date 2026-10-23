"""Behavioral tests for application-worker readiness after wake."""

from datetime import datetime, timedelta
from unittest.mock import patch
from zoneinfo import ZoneInfo

from django.db import transaction
from django.test import TestCase, override_settings
from django.urls import reverse

from jobs.controller import ControllerUnavailable
from jobs.models import Job, ProcessingSchedule, WorkerCredential
from jobs.scheduling import start_worker_readiness_window
from ledger.tests.fixtures import CSV_TEXT
from ledger.tests.support import UploadSetupMixin

LONDON = ZoneInfo("Europe/London")


class ControlledController:
    def __init__(self):
        self.wake_requests = 0

    def request_wake(self):
        self.wake_requests += 1


class FailingController:
    def __init__(self):
        self.wake_requests = 0

    def request_wake(self):
        self.wake_requests += 1
        raise ControllerUnavailable("controller down")


class WorkerReadinessTests(UploadSetupMixin, TestCase):
    def setUp(self):
        super().setUp()
        _, self.token = WorkerCredential.issue("readiness-test")
        self.upload(CSV_TEXT, filename="ready.csv")
        self.job = Job.objects.get(upload__filename="ready.csv")
        requested_at = datetime(2026, 10, 22, 21, 0, tzinfo=LONDON)
        self.deadline = requested_at + timedelta(minutes=10)
        self.schedule = ProcessingSchedule.objects.create(
            name="processing",
            readiness_status=ProcessingSchedule.ReadinessStatus.WAKING,
            wake_requested_at=requested_at,
            readiness_deadline=self.deadline,
        )
        self.job.status = Job.Status.RELEASED
        self.job.released_at = requested_at
        self.job.save(update_fields=["status", "released_at"])

    def claim(self):
        return self.client.post(
            reverse("jobs:claim"),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {self.token}",
        )

    def test_readiness_window_starts_once_only_for_released_work(self):
        request_at = self.deadline - timedelta(minutes=10)
        self.schedule.readiness_status = ProcessingSchedule.ReadinessStatus.QUEUED
        self.schedule.save(update_fields=["readiness_status"])
        self.job.status = Job.Status.WAITING
        self.job.save(update_fields=["status"])

        self.assertFalse(start_worker_readiness_window(now=request_at))

        self.job.status = Job.Status.RELEASED
        self.job.available_at = request_at + timedelta(seconds=1)
        self.job.save(update_fields=["status", "available_at"])
        self.assertFalse(start_worker_readiness_window(now=request_at))
        self.job.available_at = None
        self.job.save(update_fields=["available_at"])
        self.assertTrue(start_worker_readiness_window(now=request_at))
        self.assertFalse(
            start_worker_readiness_window(now=request_at + timedelta(seconds=1))
        )

        self.schedule.refresh_from_db()
        self.assertEqual(
            self.schedule.readiness_status,
            ProcessingSchedule.ReadinessStatus.WAKING,
        )
        self.assertEqual(self.schedule.wake_requested_at, request_at)
        self.assertEqual(
            self.schedule.readiness_deadline,
            request_at + timedelta(minutes=10),
        )

    def test_first_authenticated_claim_confirms_worker_readiness(self):
        ready_at = self.deadline - timedelta(seconds=1)
        with patch("django.utils.timezone.now", return_value=ready_at):
            response = self.claim()

        self.assertEqual(response.status_code, 200)
        with patch(
            "django.utils.timezone.now",
            return_value=ready_at + timedelta(minutes=1),
        ):
            repeated_claim = self.claim()

        self.assertEqual(repeated_claim.status_code, 204)
        self.schedule.refresh_from_db()
        self.assertEqual(
            self.schedule.readiness_status,
            ProcessingSchedule.ReadinessStatus.READY,
        )
        self.assertEqual(self.schedule.worker_ready_at, ready_at)

    def test_authenticated_empty_claim_confirms_worker_readiness(self):
        ready_at = self.deadline - timedelta(seconds=1)
        self.job.status = Job.Status.WAITING
        self.job.save(update_fields=["status"])

        with patch("django.utils.timezone.now", return_value=ready_at):
            response = self.claim()

        self.assertEqual(response.status_code, 204)
        self.schedule.refresh_from_db()
        self.assertEqual(
            self.schedule.readiness_status,
            ProcessingSchedule.ReadinessStatus.READY,
        )
        self.assertEqual(self.schedule.worker_ready_at, ready_at)

    def test_claim_after_deadline_marks_unavailable_and_retains_work(self):
        with patch("django.utils.timezone.now", return_value=self.deadline):
            response = self.claim()

        self.assertEqual(response.status_code, 204)
        self.job.refresh_from_db()
        self.schedule.refresh_from_db()
        self.assertEqual(self.job.status, Job.Status.WAITING)
        self.assertEqual(
            self.schedule.readiness_status,
            ProcessingSchedule.ReadinessStatus.UNAVAILABLE,
        )

    def test_process_now_queues_work_after_an_unavailable_batch(self):
        self.schedule.readiness_status = ProcessingSchedule.ReadinessStatus.UNAVAILABLE
        self.schedule.save(update_fields=["readiness_status"])
        self.job.status = Job.Status.WAITING
        self.job.save(update_fields=["status"])
        self.client.force_login(self._user())

        response = self.client.post(reverse("jobs:process_now"))

        self.assertEqual(response.status_code, 302)
        self.job.refresh_from_db()
        self.schedule.refresh_from_db()
        self.assertEqual(self.job.status, Job.Status.RELEASED)
        self.assertEqual(
            self.schedule.readiness_status,
            ProcessingSchedule.ReadinessStatus.QUEUED,
        )

    def test_process_now_starts_a_fresh_batch_after_ready_worker(self):
        self.schedule.readiness_status = ProcessingSchedule.ReadinessStatus.READY
        self.schedule.worker_ready_at = self.deadline - timedelta(minutes=1)
        self.schedule.save(update_fields=["readiness_status", "worker_ready_at"])
        self.job.status = Job.Status.WAITING
        self.job.save(update_fields=["status"])
        self.client.force_login(self._user())

        response = self.client.post(reverse("jobs:process_now"))

        self.assertEqual(response.status_code, 302)
        self.job.refresh_from_db()
        self.schedule.refresh_from_db()
        self.assertEqual(self.job.status, Job.Status.RELEASED)
        self.assertEqual(
            self.schedule.readiness_status,
            ProcessingSchedule.ReadinessStatus.QUEUED,
        )
        self.assertIsNone(self.schedule.worker_ready_at)
        self.assertIsNone(self.schedule.wake_requested_at)
        self.assertIsNone(self.schedule.readiness_deadline)

    def test_process_now_requests_wake_once_for_released_work(self):
        self.schedule.readiness_status = ProcessingSchedule.ReadinessStatus.UNAVAILABLE
        self.schedule.save(update_fields=["readiness_status"])
        self.job.status = Job.Status.WAITING
        self.job.save(update_fields=["status"])
        self.client.force_login(self._user())
        controller = ControlledController()
        request_at = self.deadline - timedelta(minutes=5)

        with (
            override_settings(LAPTOP_CONTROLLER=controller),
            patch("django.utils.timezone.now", return_value=request_at),
            self.captureOnCommitCallbacks(execute=True),
        ):
            first_response = self.client.post(reverse("jobs:process_now"))
            second_response = self.client.post(reverse("jobs:process_now"))

        self.assertEqual(first_response.status_code, 302)
        self.assertEqual(second_response.status_code, 302)
        self.assertEqual(controller.wake_requests, 1)
        self.job.refresh_from_db()
        self.schedule.refresh_from_db()
        self.assertEqual(self.job.status, Job.Status.RELEASED)
        self.assertEqual(
            self.schedule.readiness_status,
            ProcessingSchedule.ReadinessStatus.WAKING,
        )
        self.assertEqual(self.schedule.wake_requested_at, request_at)
        self.assertEqual(
            self.schedule.readiness_deadline,
            request_at + timedelta(minutes=10),
        )

    def test_process_now_recovers_expired_readiness_before_releasing(self):
        self.upload(CSV_TEXT, filename="next.csv")
        next_job = Job.objects.get(upload__filename="next.csv")
        self.client.force_login(self._user())
        controller = ControlledController()
        request_at = self.deadline

        with (
            override_settings(LAPTOP_CONTROLLER=controller),
            patch("django.utils.timezone.now", return_value=request_at),
            self.captureOnCommitCallbacks(execute=True),
        ):
            response = self.client.post(reverse("jobs:process_now"))

        self.assertEqual(response.status_code, 302)
        self.assertEqual(controller.wake_requests, 1)
        self.job.refresh_from_db()
        next_job.refresh_from_db()
        self.schedule.refresh_from_db()
        self.assertEqual(self.job.status, Job.Status.RELEASED)
        self.assertEqual(next_job.status, Job.Status.RELEASED)
        self.assertEqual(
            self.schedule.readiness_status,
            ProcessingSchedule.ReadinessStatus.WAKING,
        )
        self.assertEqual(self.schedule.wake_requested_at, request_at)

    def test_process_now_does_not_wake_when_outer_transaction_rolls_back(self):
        self.schedule.readiness_status = ProcessingSchedule.ReadinessStatus.IDLE
        self.schedule.save(update_fields=["readiness_status"])
        self.job.status = Job.Status.WAITING
        self.job.save(update_fields=["status"])
        self.client.force_login(self._user())
        controller = ControlledController()
        request_at = self.deadline - timedelta(minutes=5)

        with (
            override_settings(LAPTOP_CONTROLLER=controller),
            patch("django.utils.timezone.now", return_value=request_at),
            self.captureOnCommitCallbacks(execute=True),
            transaction.atomic(),
        ):
            response = self.client.post(reverse("jobs:process_now"))
            transaction.set_rollback(True)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(controller.wake_requests, 0)
        self.job.refresh_from_db()
        self.schedule.refresh_from_db()
        self.assertEqual(self.job.status, Job.Status.WAITING)
        self.assertEqual(
            self.schedule.readiness_status,
            ProcessingSchedule.ReadinessStatus.IDLE,
        )

    def test_process_now_does_not_request_wake_for_empty_released_queue(self):
        self.schedule.readiness_status = ProcessingSchedule.ReadinessStatus.IDLE
        self.schedule.save(update_fields=["readiness_status"])
        self.job.status = Job.Status.COMPLETED
        self.job.save(update_fields=["status"])
        self.client.force_login(self._user())
        controller = ControlledController()

        with override_settings(LAPTOP_CONTROLLER=controller):
            response = self.client.post(reverse("jobs:process_now"))

        self.assertEqual(response.status_code, 302)
        self.assertEqual(controller.wake_requests, 0)

    def test_wake_failure_keeps_work_in_the_readiness_window(self):
        self.schedule.readiness_status = ProcessingSchedule.ReadinessStatus.IDLE
        self.schedule.save(update_fields=["readiness_status"])
        self.job.status = Job.Status.WAITING
        self.job.save(update_fields=["status"])
        self.client.force_login(self._user())
        controller = FailingController()
        request_at = self.deadline - timedelta(minutes=5)

        with (
            override_settings(LAPTOP_CONTROLLER=controller),
            patch("django.utils.timezone.now", return_value=request_at),
            self.captureOnCommitCallbacks(execute=True),
        ):
            response = self.client.post(reverse("jobs:process_now"))

        self.assertEqual(response.status_code, 302)
        self.assertEqual(controller.wake_requests, 1)
        self.schedule.refresh_from_db()
        self.assertEqual(
            self.schedule.readiness_status,
            ProcessingSchedule.ReadinessStatus.WAKING,
        )
        self.assertEqual(self.schedule.wake_requested_at, request_at)
        self.job.refresh_from_db()
        self.assertEqual(self.job.status, Job.Status.RELEASED)

    def test_retry_requests_wake_once_after_valid_retry(self):
        self.job.status = Job.Status.FAILED
        self.job.attempts_used = 2
        self.job.last_failure = "worker failed"
        self.job.save(
            update_fields=["status", "attempts_used", "last_failure"]
        )

        self.upload(CSV_TEXT, filename="expired.csv")
        expired_job = Job.objects.get(upload__filename="expired.csv")
        expired_job.status = Job.Status.RELEASED
        expired_job.released_at = self.deadline - timedelta(minutes=10)
        expired_job.save(update_fields=["status", "released_at"])

        self.client.force_login(self._user())
        controller = ControlledController()
        request_at = self.deadline
        url = reverse("jobs:retry", kwargs={"pk": self.job.upload_id})

        with (
            override_settings(LAPTOP_CONTROLLER=controller),
            patch("django.utils.timezone.now", return_value=request_at),
            self.captureOnCommitCallbacks(execute=True),
        ):
            first_response = self.client.post(url)
            second_response = self.client.post(url)

        self.assertEqual(first_response.status_code, 302)
        self.assertEqual(second_response.status_code, 302)
        self.assertEqual(controller.wake_requests, 1)
        expired_job.refresh_from_db()
        self.job.refresh_from_db()
        self.schedule.refresh_from_db()
        self.assertEqual(self.job.status, Job.Status.RELEASED)
        self.assertEqual(self.job.attempts_used, 0)
        self.assertEqual(self.job.available_at, request_at)
        self.assertEqual(expired_job.status, Job.Status.WAITING)
        self.assertEqual(
            self.schedule.readiness_status,
            ProcessingSchedule.ReadinessStatus.WAKING,
        )
        self.assertEqual(self.schedule.wake_requested_at, request_at)
        self.assertEqual(
            self.schedule.readiness_deadline,
            request_at + timedelta(minutes=10),
        )

    def test_upload_list_exposes_unavailable_status_after_deadline(self):
        self.client.force_login(self._user())
        with patch("django.utils.timezone.now", return_value=self.deadline):
            response = self.client.get(reverse("ledger:uploads"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Unavailable")
        self.assertContains(response, "queued for manual retry or the next batch")
        self.job.refresh_from_db()
        self.assertEqual(self.job.status, Job.Status.WAITING)

    def _user(self):
        from django.contrib.auth import get_user_model

        return get_user_model().objects.create_user(
            f"readiness-{self._testMethodName}", password="test-password"
        )
