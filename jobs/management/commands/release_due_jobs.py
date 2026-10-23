"""Release waiting jobs once for each due Europe/London schedule slot."""

from datetime import time, timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from jobs.controller import get_laptop_controller
from jobs.models import Job, ProcessingSchedule
from jobs.scheduling import (
    SCHEDULE_NAME,
    note_released_work,
    refresh_worker_readiness,
    request_wake_for_released_work,
)


RELEASE_TIME = time(21, 0)


def release_due_jobs(now=None) -> int:
    """Release waiting jobs for the latest due nightly slot, at most once."""
    now = now or timezone.now()
    refresh_worker_readiness(now)
    local_now = timezone.localtime(now)
    before_release = local_now.time() < RELEASE_TIME
    due_date = (
        local_now.date() - timedelta(days=1)
        if before_release
        else local_now.date()
    )
    released = 0

    with transaction.atomic():
        schedule, created = (
            ProcessingSchedule.objects.select_for_update().get_or_create(
                name=SCHEDULE_NAME
            )
        )
        if created and before_release:
            schedule.last_released_for = due_date
            schedule.save(update_fields=["last_released_for"])
        elif (
            schedule.last_released_for is None
            or schedule.last_released_for < due_date
        ):
            schedule.last_released_for = due_date
            schedule.save(update_fields=["last_released_for"])
            released = Job.objects.filter(status=Job.Status.WAITING).update(
                status=Job.Status.RELEASED,
                released_at=now,
            )
            if released:
                note_released_work()

    request_wake_for_released_work(
        get_laptop_controller(),
        now=now,
    )
    return released


class Command(BaseCommand):
    help = "Release waiting processing jobs at 21:00 Europe/London."

    def handle(self, *args, **options):
        released = release_due_jobs()
        self.stdout.write(f"Released {released} waiting upload(s).")
