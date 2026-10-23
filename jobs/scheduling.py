"""Persisted processing-batch readiness transitions."""

import logging
from datetime import timedelta
from typing import Protocol

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from jobs.controller import ControllerError
from jobs.models import Job, ProcessingSchedule


logger = logging.getLogger(__name__)


SCHEDULE_NAME = "processing"
READINESS_WINDOW = timedelta(minutes=10)


class WorkerWakeController(Protocol):
    """Boundary for one controlled wake request; transport/auth stay external."""

    def request_wake(self) -> None: ...


def note_released_work() -> None:
    """Queue a fresh batch after an idle, completed or unavailable batch."""
    with transaction.atomic():
        schedule, _ = ProcessingSchedule.objects.select_for_update().get_or_create(
            name=SCHEDULE_NAME
        )
        if (
            schedule.readiness_status == ProcessingSchedule.ReadinessStatus.READY
            and Job.objects.filter(status=Job.Status.PROCESSING).exists()
        ):
            return
        if schedule.readiness_status not in (
            ProcessingSchedule.ReadinessStatus.IDLE,
            ProcessingSchedule.ReadinessStatus.READY,
            ProcessingSchedule.ReadinessStatus.UNAVAILABLE,
        ):
            return
        schedule.readiness_status = ProcessingSchedule.ReadinessStatus.QUEUED
        schedule.wake_requested_at = None
        schedule.readiness_deadline = None
        schedule.worker_ready_at = None
        schedule.save(
            update_fields=[
                "readiness_status",
                "wake_requested_at",
                "readiness_deadline",
                "worker_ready_at",
            ]
        )


def start_worker_readiness_window(now=None) -> bool:
    """Record one wake attempt when eligible released work is waiting."""
    now = now or timezone.now()
    refresh_worker_readiness(now)
    with transaction.atomic():
        schedule, _ = ProcessingSchedule.objects.select_for_update().get_or_create(
            name=SCHEDULE_NAME
        )
        if schedule.readiness_status not in (
            ProcessingSchedule.ReadinessStatus.IDLE,
            ProcessingSchedule.ReadinessStatus.QUEUED,
        ):
            return False
        eligible_work = Job.objects.filter(status=Job.Status.RELEASED).filter(
            Q(available_at__isnull=True) | Q(available_at__lte=now)
        )
        if not eligible_work.exists():
            return False
        schedule.readiness_status = ProcessingSchedule.ReadinessStatus.WAKING
        schedule.wake_requested_at = now
        schedule.readiness_deadline = now + READINESS_WINDOW
        schedule.worker_ready_at = None
        schedule.save(
            update_fields=[
                "readiness_status",
                "wake_requested_at",
                "readiness_deadline",
                "worker_ready_at",
            ]
        )
        return True


def request_wake_for_released_work(
    controller: WorkerWakeController | None, now=None
) -> bool:
    """Schedule one wake on commit when a controller and eligible work exist."""
    if controller is None or not start_worker_readiness_window(now=now):
        return False

    def request_wake() -> None:
        try:
            controller.request_wake()
        except ControllerError as exc:
            # The readiness window remains WAKING and expires into UNAVAILABLE.
            logger.warning("laptop wake request failed: %s", exc)

    transaction.on_commit(request_wake)
    return True


def refresh_worker_readiness(now=None):
    """Expire a missed readiness deadline and return released jobs to waiting."""
    now = now or timezone.now()
    with transaction.atomic():
        schedule = (
            ProcessingSchedule.objects.select_for_update()
            .filter(name=SCHEDULE_NAME)
            .first()
        )
        if (
            schedule is None
            or schedule.readiness_status != ProcessingSchedule.ReadinessStatus.WAKING
        ):
            return schedule
        if (
            schedule.readiness_deadline is not None
            and schedule.readiness_deadline > now
        ):
            return schedule
        Job.objects.filter(status=Job.Status.RELEASED).update(
            status=Job.Status.WAITING
        )
        schedule.readiness_status = ProcessingSchedule.ReadinessStatus.UNAVAILABLE
        schedule.save(update_fields=["readiness_status"])
        return schedule


def mark_worker_ready(now=None) -> None:
    """Record the first authenticated worker claim as application readiness."""
    now = now or timezone.now()
    with transaction.atomic():
        schedule = (
            ProcessingSchedule.objects.select_for_update()
            .filter(name=SCHEDULE_NAME)
            .first()
        )
        if schedule is None:
            return
        if schedule.readiness_status in (
            ProcessingSchedule.ReadinessStatus.UNAVAILABLE,
            ProcessingSchedule.ReadinessStatus.READY,
        ):
            return
        schedule.readiness_status = ProcessingSchedule.ReadinessStatus.READY
        schedule.worker_ready_at = now
        schedule.save(update_fields=["readiness_status", "worker_ready_at"])
