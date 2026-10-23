"""Application-owned keep-awake leases, separate from job ownership."""

import logging
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from jobs.controller import (
    ControllerError,
    ControllerRejected,
    MAX_LEASE_LIFETIME,
    get_laptop_controller,
)
from jobs.models import JobAttempt, KeepAwakeLease


logger = logging.getLogger(__name__)


def begin_keep_awake(attempt: JobAttempt, controller=None):
    """Create one bounded controller lease for an attempt that just started."""
    controller = controller if controller is not None else get_laptop_controller()
    if controller is None:
        return None
    existing = KeepAwakeLease.objects.filter(attempt=attempt).first()
    if existing is not None:
        return existing
    try:
        lease = controller.create_lease(settings.WORKER_KEEP_AWAKE_SECONDS)
    except ControllerError as exc:
        logger.warning("keep-awake lease creation failed: %s", exc)
        return None
    return KeepAwakeLease.objects.create(
        attempt=attempt,
        lease_id=lease.lease_id,
        created_at=lease.created_at,
        expires_at=lease.expires_at,
        ceiling_at=lease.created_at + MAX_LEASE_LIFETIME,
    )


def begin_keep_awake_for_attempt(attempt_id: int, controller=None):
    """Start a lease from a commit callback using a fresh attempt instance."""
    try:
        attempt = JobAttempt.objects.filter(pk=attempt_id).first()
        if attempt is None:
            return None
        return begin_keep_awake(attempt, controller=controller)
    except Exception as exc:
        # Sleep inhibition is auxiliary; it must not turn a committed claim into
        # an error response that leaves the worker without its assignment.
        logger.warning("keep-awake lease start failed: %s", exc)
        return None


def renew_keep_awake(attempt: JobAttempt, controller=None, now=None):
    """Extend only near expiry, never beyond the controller's eight-hour cap.

    The row lock serializes concurrent heartbeat/progress requests across
    Gunicorn workers so an additive extension is applied once.
    """
    controller = controller if controller is not None else get_laptop_controller()
    if controller is None:
        return None
    with transaction.atomic():
        lease = (
            KeepAwakeLease.objects.select_for_update()
            .filter(attempt=attempt, released_at__isnull=True)
            .first()
        )
        if lease is None:
            return None
        now = now or timezone.now()
        renew_before = timedelta(
            seconds=settings.WORKER_KEEP_AWAKE_RENEW_BEFORE_SECONDS
        )
        if lease.expires_at - now > renew_before:
            return lease
        if lease.expires_at >= lease.ceiling_at or lease.ceiling_at <= now:
            _record_failure(lease, "keep-awake lease reached its eight-hour ceiling")
            return lease
        if lease.expires_at <= now:
            _record_failure(lease, "keep-awake lease expired before renewal")
            return lease

        available = int((lease.ceiling_at - now).total_seconds())
        extension = min(settings.WORKER_KEEP_AWAKE_EXTENSION_SECONDS, available)
        if extension <= 0:
            _record_failure(lease, "keep-awake lease reached its eight-hour ceiling")
            return lease
        try:
            extended = controller.extend_lease(lease.lease_id, extension)
        except ControllerRejected as exc:
            if exc.status == 404:
                _record_failure(
                    lease,
                    "keep-awake lease no longer exists",
                    now=now,
                    inactive=True,
                )
            else:
                _record_failure(lease, "keep-awake lease renewal was rejected")
            return lease
        except ControllerError:
            _record_failure(lease, "keep-awake lease renewal is unavailable")
            return lease

        lease.expires_at = extended.expires_at
        lease.last_extended_at = now
        lease.failure = ""
        lease.save(update_fields=["expires_at", "last_extended_at", "failure"])
        return lease


def end_keep_awake(attempt: JobAttempt, controller=None, now=None):
    """Release only this application's lease; never force sleep."""
    controller = controller if controller is not None else get_laptop_controller()
    if controller is None:
        return None
    with transaction.atomic():
        lease = (
            KeepAwakeLease.objects.select_for_update()
            .filter(attempt=attempt, released_at__isnull=True)
            .first()
        )
        if lease is None:
            return None
        now = now or timezone.now()
        try:
            released = controller.release_lease(lease.lease_id)
        except ControllerRejected as exc:
            if exc.status == 404:
                _record_failure(
                    lease,
                    "keep-awake lease expired before release",
                    now=now,
                    inactive=True,
                )
            else:
                _record_failure(lease, "keep-awake lease release was rejected")
            return lease
        except ControllerError:
            _record_failure(lease, "keep-awake lease release is unavailable")
            return lease

        if released != lease.lease_id:
            _record_failure(lease, "controller released an unexpected lease identity")
            return lease
        lease.released_at = now
        lease.failure = ""
        lease.save(update_fields=["released_at", "failure"])
        return lease


def end_keep_awake_for_attempt(attempt_id: int, controller=None):
    """Resolve an attempt by ID so commit callbacks do not hold stale state."""
    try:
        attempt = JobAttempt.objects.filter(pk=attempt_id).first()
        if attempt is None:
            return None
        return end_keep_awake(attempt, controller=controller)
    except Exception as exc:
        # The controller lease expires on its own if cleanup cannot run.
        logger.warning("keep-awake lease cleanup failed: %s", exc)
        return None


def _record_failure(
    lease: KeepAwakeLease, message: str, now=None, *, inactive=False
) -> None:
    lease.failure = message
    fields = ["failure"]
    if inactive:
        lease.released_at = now or timezone.now()
        fields.append("released_at")
    lease.save(update_fields=fields)
