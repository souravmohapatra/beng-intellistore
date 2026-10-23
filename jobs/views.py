"""User-facing job controls."""

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect
from django.utils import timezone
from django.views.decorators.http import require_POST

from jobs.controller import get_laptop_controller
from jobs.models import Job, ProcessingSchedule
from jobs.scheduling import (
    SCHEDULE_NAME,
    note_released_work,
    refresh_worker_readiness,
    request_wake_for_released_work,
)


@login_required
@require_POST
def process_now(request):
    """Release every waiting job; repeated clicks do not interrupt or duplicate."""
    now = timezone.now()
    refresh_worker_readiness(now)
    with transaction.atomic():
        ProcessingSchedule.objects.select_for_update().get_or_create(
            name=SCHEDULE_NAME
        )
        released = Job.objects.filter(status=Job.Status.WAITING).update(
            status=Job.Status.RELEASED, released_at=now
        )
        if released:
            note_released_work()
    request_wake_for_released_work(
        get_laptop_controller(),
        now=now,
    )
    return redirect("ledger:uploads")


@login_required
@require_POST
def retry_job(request, pk):
    """Reset a visibly failed job's attempt budget; safe to click repeatedly."""
    retried = False
    now = timezone.now()
    refresh_worker_readiness(now)
    with transaction.atomic():
        job = get_object_or_404(Job.objects.select_for_update(), upload_id=pk)
        if job.status == Job.Status.FAILED:
            job.status = Job.Status.RELEASED
            job.attempts_used = 0
            job.available_at = now
            job.last_failure = ""
            job.save(
                update_fields=[
                    "status",
                    "attempts_used",
                    "available_at",
                    "last_failure",
                ]
            )
            note_released_work()
            retried = True
    if retried:
        request_wake_for_released_work(
            get_laptop_controller(),
            now=now,
        )
    return redirect("ledger:upload_detail", pk=pk)
