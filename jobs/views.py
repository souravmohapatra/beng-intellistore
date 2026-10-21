"""User-facing job controls."""

from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from django.utils import timezone
from django.views.decorators.http import require_POST

from jobs.models import Job


@login_required
@require_POST
def process_now(request):
    """Release every waiting job; repeated clicks do not interrupt or duplicate."""
    Job.objects.filter(status=Job.Status.WAITING).update(
        status=Job.Status.RELEASED, released_at=timezone.now()
    )
    return redirect("ledger:uploads")
