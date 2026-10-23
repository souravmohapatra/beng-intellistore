"""Behavioral tests for the nightly processing schedule."""

from datetime import datetime, timedelta
from unittest.mock import patch
from zoneinfo import ZoneInfo

from django.core.management import call_command
from django.test import TestCase, override_settings

from jobs.models import Job, ProcessingSchedule
from ledger.tests.fixtures import CSV_TEXT
from ledger.tests.support import UploadSetupMixin


LONDON = ZoneInfo("Europe/London")


class ControlledController:
    def __init__(self):
        self.wake_requests = 0

    def request_wake(self):
        self.wake_requests += 1


class NightlyReleaseTests(UploadSetupMixin, TestCase):
    def release_at(
        self, hour, minute, day=22, month=10, controller=None
    ):
        now = datetime(2026, month, day, hour, minute, tzinfo=LONDON)
        with (
            override_settings(LAPTOP_CONTROLLER=controller),
            patch("django.utils.timezone.now", return_value=now),
            self.captureOnCommitCallbacks(execute=True),
        ):
            call_command("release_due_jobs", stdout=None)

    def test_waiting_work_releases_once_at_2100_london_time(self):
        controller = ControlledController()
        self.upload(CSV_TEXT, filename="first.csv")
        first_job = Job.objects.get(upload__filename="first.csv")

        self.release_at(20, 59, controller=controller)

        first_job.refresh_from_db()
        self.assertEqual(first_job.status, Job.Status.WAITING)
        self.assertEqual(controller.wake_requests, 0)

        self.release_at(21, 0, controller=controller)

        first_job.refresh_from_db()
        self.assertEqual(first_job.status, Job.Status.RELEASED)
        released_at = first_job.released_at
        self.assertEqual(controller.wake_requests, 1)
        schedule = ProcessingSchedule.objects.get(name="processing")
        self.assertEqual(
            schedule.readiness_status,
            ProcessingSchedule.ReadinessStatus.WAKING,
        )

        self.upload(CSV_TEXT, filename="second.csv")
        second_job = Job.objects.get(upload__filename="second.csv")
        self.release_at(21, 1, controller=controller)

        first_job.refresh_from_db()
        second_job.refresh_from_db()
        self.assertEqual(first_job.released_at, released_at)
        self.assertEqual(second_job.status, Job.Status.WAITING)
        self.assertEqual(controller.wake_requests, 1)

    def test_empty_due_queue_does_not_request_wake(self):
        controller = ControlledController()

        self.release_at(21, 0, controller=controller)

        self.assertEqual(controller.wake_requests, 0)

    def test_expired_readiness_is_released_with_the_next_nightly_batch(self):
        now = datetime(2026, 10, 22, 21, 0, tzinfo=LONDON)
        previous_request_at = now - timedelta(minutes=11)
        self.upload(CSV_TEXT, filename="previous.csv")
        previous_job = Job.objects.get(upload__filename="previous.csv")
        self.upload(CSV_TEXT, filename="current.csv")
        current_job = Job.objects.get(upload__filename="current.csv")
        previous_job.status = Job.Status.RELEASED
        previous_job.released_at = previous_request_at
        previous_job.save(update_fields=["status", "released_at"])
        ProcessingSchedule.objects.create(
            name="processing",
            last_released_for=now.date() - timedelta(days=1),
            readiness_status=ProcessingSchedule.ReadinessStatus.WAKING,
            wake_requested_at=previous_request_at,
            readiness_deadline=now - timedelta(minutes=1),
        )
        controller = ControlledController()

        self.release_at(21, 0, controller=controller)

        previous_job.refresh_from_db()
        current_job.refresh_from_db()
        schedule = ProcessingSchedule.objects.get(name="processing")
        self.assertEqual(previous_job.status, Job.Status.RELEASED)
        self.assertEqual(current_job.status, Job.Status.RELEASED)
        self.assertEqual(controller.wake_requests, 1)
        self.assertEqual(
            schedule.readiness_status,
            ProcessingSchedule.ReadinessStatus.WAKING,
        )
        self.assertEqual(schedule.wake_requested_at, now)

    def test_missed_days_catch_up_once_before_the_next_nightly_slot(self):
        self.upload(CSV_TEXT, filename="first.csv")
        first_job = Job.objects.get(upload__filename="first.csv")
        self.release_at(21, 0, day=20)
        first_job.refresh_from_db()
        self.assertEqual(first_job.status, Job.Status.RELEASED)

        self.upload(CSV_TEXT, filename="catch-up.csv")
        catch_up_job = Job.objects.get(upload__filename="catch-up.csv")
        self.release_at(10, 0, day=23)
        catch_up_job.refresh_from_db()
        self.assertEqual(catch_up_job.status, Job.Status.RELEASED)

        self.upload(CSV_TEXT, filename="next-night.csv")
        next_night_job = Job.objects.get(upload__filename="next-night.csv")
        self.release_at(20, 59, day=23)
        next_night_job.refresh_from_db()
        self.assertEqual(next_night_job.status, Job.Status.WAITING)

        self.release_at(21, 0, day=23)
        next_night_job.refresh_from_db()
        self.assertEqual(next_night_job.status, Job.Status.RELEASED)

    def test_release_time_remains_local_across_spring_dst_change(self):
        self.upload(CSV_TEXT, filename="dst.csv")
        job = Job.objects.get(upload__filename="dst.csv")

        self.release_at(20, 59, day=29, month=3)
        job.refresh_from_db()
        self.assertEqual(job.status, Job.Status.WAITING)

        self.release_at(21, 0, day=29, month=3)
        job.refresh_from_db()
        self.assertEqual(job.status, Job.Status.RELEASED)
