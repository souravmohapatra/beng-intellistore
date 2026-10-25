"""Scoped worker API: claims, assigned source, progress, results.

Authentication is a replaceable bearer credential. These endpoints grant no
user session, no database access and no access to unrelated originals.
"""

import hashlib
import json
import uuid
from datetime import timedelta
from functools import wraps
from pathlib import Path

from django.conf import settings
from django.db import connection, transaction
from django.db.models import Max, Q
from django.http import FileResponse, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from jobs.keep_awake import (
    begin_keep_awake_for_attempt,
    end_keep_awake_for_attempt,
    renew_keep_awake,
)
from jobs.models import (
    AdviceRequest,
    Job,
    JobAttempt,
    JobEvent,
    JobResult,
    WorkerCredential,
)
from jobs.publication import advisory_fields, apply_result, validate_result_payload
from jobs.scheduling import mark_worker_ready, refresh_worker_readiness
from ledger.models import ClassificationSuggestion, Upload

MAX_BODY_BYTES = 1024 * 1024
CLAIM_LOCK_KEY = 0x1A2B3C
RESULT_VERSION = 1
ALLOWED_OUTCOMES = {"unsupported", "failed", "imported"}  # partial is server-derived only
MAX_STAGE_LENGTH = 100
MAX_MESSAGE_LENGTH = 500


class ApiError(Exception):
    def __init__(self, message, status=400):
        super().__init__(message)
        self.message = message
        self.status = status


def worker_required(view):
    @wraps(view)
    def wrapper(request, *args, **kwargs):
        header = request.headers.get("Authorization", "")
        if not header.startswith("Bearer "):
            return JsonResponse({"error": "unauthorized"}, status=401)
        token = header[len("Bearer ") :].strip()
        credential = WorkerCredential.objects.filter(
            token_hash=WorkerCredential.hash_token(token), revoked_at__isnull=True
        ).first()
        if credential is None:
            return JsonResponse({"error": "unauthorized"}, status=401)
        request.worker = credential
        return view(request, *args, **kwargs)

    return wrapper


def _json_body(request) -> dict:
    if len(request.body) > MAX_BODY_BYTES:
        raise ApiError("payload too large", status=413)
    try:
        body = json.loads(request.body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ApiError("invalid json") from exc
    if not isinstance(body, dict):
        raise ApiError("payload must be an object")
    return body


def _effective_outcome(outcome: str, publication) -> str:
    """Record what publication achieved, not what the worker claimed."""
    if outcome != "imported":
        return outcome
    if publication.committed and (publication.rejected or publication.deferred):
        return "partial"
    if publication.status == Upload.Status.DUPLICATE:
        return "duplicate"
    if publication.rejected or publication.deferred:
        return "failed"
    if publication.status != Upload.Status.IMPORTED:
        return "failed"
    return "imported"


def _error(exc: ApiError) -> JsonResponse:
    return JsonResponse({"error": exc.message}, status=exc.status)


def _open_attempt(job: Job, credential: WorkerCredential) -> JobAttempt:
    attempt = job.attempts.filter(credential=credential, finished_at__isnull=True).first()
    if attempt is None:
        claimed_elsewhere = job.attempts.filter(finished_at__isnull=True).exists()
        raise ApiError(
            "job is claimed by another worker" if claimed_elsewhere else "job is not claimed",
            status=403 if claimed_elsewhere else 409,
        )
    return attempt


def _lease_deadline():
    return timezone.now() + timedelta(seconds=settings.WORKER_LEASE_SECONDS)


def _retry_delay(attempts_used: int) -> int:
    delays = settings.WORKER_RETRY_DELAYS or (0,)
    index = max(0, min(attempts_used - 1, len(delays) - 1))
    return delays[index]


def _expire_stale_attempts():
    """Reap attempts whose lease lapsed; requeue or fail their jobs."""
    now = timezone.now()
    stale = list(
        JobAttempt.objects.select_for_update().filter(
            finished_at__isnull=True, lease_expires_at__lt=now
        )
    )
    for attempt in stale:
        attempt.finished_at = now
        attempt.outcome = "expired"
        attempt.save(update_fields=["finished_at", "outcome"])
        transaction.on_commit(
            lambda attempt_id=attempt.pk: end_keep_awake_for_attempt(attempt_id)
        )
        job = Job.objects.select_for_update().get(pk=attempt.job_id)
        if job.status != Job.Status.PROCESSING:
            continue
        if job.attempts_used >= settings.WORKER_MAX_ATTEMPTS:
            job.status = Job.Status.FAILED
            job.last_failure = "Worker lease expired after the final attempt."
        else:
            job.status = Job.Status.RELEASED
            job.available_at = now + timedelta(seconds=_retry_delay(job.attempts_used))
        job.save(update_fields=["status", "available_at", "last_failure"])


def _renew_attempt(attempt: JobAttempt) -> bool:
    now = timezone.now()
    if attempt.lease_expires_at is None or attempt.lease_expires_at < now:
        return False
    attempt.heartbeat_at = now
    attempt.lease_expires_at = _lease_deadline()
    attempt.save(update_fields=["heartbeat_at", "lease_expires_at"])
    return True


def _serialize_claims():
    """Serialize claim decisions; row locks alone miss the empty-PROCESSING case."""
    if connection.vendor == "postgresql":
        with connection.cursor() as cursor:
            cursor.execute("SELECT pg_advisory_xact_lock(%s)", [CLAIM_LOCK_KEY])


@csrf_exempt
@require_POST
@worker_required
def claim(request):
    """Claim the next released job, if no other job is active."""
    with transaction.atomic():
        _serialize_claims()
        _expire_stale_attempts()
        now = timezone.now()
        refresh_worker_readiness(now)
        mark_worker_ready(now)
        if Job.objects.select_for_update().filter(status=Job.Status.PROCESSING).exists():
            return HttpResponse(status=204)

        job = (
            Job.objects.select_for_update()
            .filter(status=Job.Status.RELEASED)
            .filter(Q(available_at__isnull=True) | Q(available_at__lte=now))
            .order_by("released_at", "pk")
            .first()
        )
        if job is None:
            return HttpResponse(status=204)

        if job.attempts_used >= settings.WORKER_MAX_ATTEMPTS:
            job.status = Job.Status.FAILED
            job.last_failure = "Attempt budget exhausted."
            job.save(update_fields=["status", "last_failure"])
            return HttpResponse(status=204)

        job.attempts_used += 1
        job.status = Job.Status.PROCESSING
        job.available_at = None
        job.save(update_fields=["status", "attempts_used", "available_at"])

        highest = job.attempts.aggregate(highest=Max("number"))["highest"] or 0
        attempt = JobAttempt.objects.create(
            job=job,
            number=highest + 1,
            credential=request.worker,
            lease_expires_at=_lease_deadline(),
        )
        transaction.on_commit(
            lambda attempt_id=attempt.pk: begin_keep_awake_for_attempt(attempt_id)
        )
    return JsonResponse(
        {
            "job": job.pk,
            "attempt": attempt.pk,
            "result_version": RESULT_VERSION,
            "lease_expires_at": attempt.lease_expires_at.isoformat(),
            "attempts_remaining": max(
                0, settings.WORKER_MAX_ATTEMPTS - job.attempts_used
            ),
            "source_url": f"/api/worker/jobs/{job.pk}/source/",
            "upload": {
                "id": job.upload_id,
                "filename": job.upload.filename,
                "account": job.upload.account.name,
                "content_type": job.upload.original.content_type,
            },
        }
    )


@csrf_exempt
@require_POST
@worker_required
def heartbeat(request, job_id):
    job = get_object_or_404(Job, pk=job_id)
    try:
        attempt = _open_attempt(job, request.worker)
    except ApiError as exc:
        return _error(exc)
    if not _renew_attempt(attempt):
        return JsonResponse({"error": "lease lost"}, status=409)
    renew_keep_awake(attempt)
    return JsonResponse({"lease_expires_at": attempt.lease_expires_at.isoformat()})


@csrf_exempt
@require_GET
@worker_required
def source(request, job_id):
    job = get_object_or_404(Job.objects.select_related("upload__original"), pk=job_id)
    try:
        _open_attempt(job, request.worker)
    except ApiError as exc:
        return _error(exc)

    original = job.upload.original
    path = Path(settings.DATA_DIR) / original.stored_path
    try:
        handle = open(path, "rb")
    except OSError:
        return JsonResponse({"error": "source unavailable"}, status=410)
    return FileResponse(
        handle, content_type=original.content_type, as_attachment=True
    )


@csrf_exempt
@require_POST
@worker_required
def progress(request, job_id):
    job = get_object_or_404(Job, pk=job_id)
    try:
        attempt = _open_attempt(job, request.worker)
        if not _renew_attempt(attempt):
            return JsonResponse({"error": "lease lost"}, status=409)
        body = _json_body(request)
    except ApiError as exc:
        return _error(exc)

    stage = str(body.get("stage", "")).strip()
    if not stage:
        return JsonResponse({"error": "stage is required"}, status=400)
    JobEvent.objects.create(
        attempt=attempt,
        stage=stage[:MAX_STAGE_LENGTH],
        message=str(body.get("message", ""))[:MAX_MESSAGE_LENGTH],
    )
    renew_keep_awake(attempt)
    return JsonResponse({"ok": True})


@csrf_exempt
@require_POST
@worker_required
def result(request, job_id):
    job = get_object_or_404(Job, pk=job_id)
    try:
        body = _json_body(request)
    except ApiError as exc:
        return _error(exc)

    canonical = json.dumps(body, sort_keys=True, separators=(",", ":"))
    payload_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    completed_attempt_id = None
    response_body = None

    with transaction.atomic():
        attempt = (
            JobAttempt.objects.select_for_update()
            .filter(
                pk=body.get("attempt"),
                job=job,
                credential=request.worker,
            )
            .first()
        )
        if attempt is None:
            return JsonResponse(
                {"error": "attempt does not belong to this job"}, status=409
            )

        recorded = JobResult.objects.filter(attempt=attempt).first()
        if recorded is not None:
            if recorded.payload_sha256 == payload_hash:
                completed_attempt_id = attempt.pk
                response_body = {
                    "outcome": recorded.outcome,
                    "job": job.pk,
                    "already_recorded": True,
                }
            else:
                return JsonResponse({"error": "conflicting payload"}, status=409)
        else:
            if not attempt.is_open:
                return JsonResponse(
                    {"error": "no open attempt for this job"}, status=409
                )
            if (
                attempt.lease_expires_at is not None
                and attempt.lease_expires_at < timezone.now()
            ):
                return JsonResponse({"error": "lease lost"}, status=409)

            if body.get("version") != RESULT_VERSION:
                return JsonResponse(
                    {"error": "unsupported result version"}, status=400
                )
            outcome = body.get("outcome")
            if outcome not in ALLOWED_OUTCOMES:
                return JsonResponse({"error": "unsupported outcome"}, status=400)
            try:
                validate_result_payload(body)
            except ValueError as exc:
                return JsonResponse({"error": str(exc)}, status=400)

            publication = apply_result(job, body)
            upload_status = publication.status
            effective_outcome = _effective_outcome(outcome, publication)
            JobResult.objects.create(
                attempt=attempt,
                version=RESULT_VERSION,
                outcome=effective_outcome,
                payload=body,
                payload_sha256=payload_hash,
            )
            attempt.finished_at = timezone.now()
            attempt.outcome = effective_outcome
            attempt.save(update_fields=["finished_at", "outcome"])
            job.status = Job.Status.COMPLETED
            job.save(update_fields=["status"])
            if upload_status != job.upload.status:
                job.upload.status = upload_status
                job.upload.save(update_fields=["status"])
            completed_attempt_id = attempt.pk
            response_body = {
                "outcome": effective_outcome,
                "job": job.pk,
                "already_recorded": False,
            }

    if completed_attempt_id is not None:
        transaction.on_commit(
            lambda attempt_id=completed_attempt_id: end_keep_awake_for_attempt(
                attempt_id
            )
        )
    return JsonResponse(response_body)


ADVICE_CLAIM_LOCK_KEY = 0x1A2B3D


@csrf_exempt
@require_POST
@worker_required
def claim_advice(request):
    """Claim one pending or stale advice request, independent of imports."""
    with transaction.atomic():
        if connection.vendor == "postgresql":
            with connection.cursor() as cursor:
                cursor.execute("SELECT pg_advisory_xact_lock(%s)", [ADVICE_CLAIM_LOCK_KEY])
        now = timezone.now()
        if AdviceRequest.objects.select_for_update().filter(
            status=AdviceRequest.Status.PROCESSING, lease_expires_at__gte=now
        ).exists():
            return HttpResponse(status=204)
        advice_request = (
            AdviceRequest.objects.select_for_update()
            .select_related("transaction__account")
            .filter(
                Q(status=AdviceRequest.Status.PENDING)
                | Q(
                    status=AdviceRequest.Status.PROCESSING,
                    lease_expires_at__lt=now,
                )
            )
            .order_by("created_at", "pk")
            .first()
        )
        if advice_request is None:
            return HttpResponse(status=204)
        if advice_request.attempts_used >= settings.WORKER_MAX_ATTEMPTS:
            advice_request.status = AdviceRequest.Status.FAILED
            advice_request.last_failure = "Advice attempt budget exhausted."
            advice_request.claimed_at = None
            advice_request.claimed_by = None
            advice_request.claim_token = None
            advice_request.lease_expires_at = None
            advice_request.save(
                update_fields=[
                    "status",
                    "last_failure",
                    "claimed_at",
                    "claimed_by",
                    "claim_token",
                    "lease_expires_at",
                    "updated_at",
                ]
            )
            return HttpResponse(status=204)

        advice_request.attempts_used += 1
        advice_request.status = AdviceRequest.Status.PROCESSING
        advice_request.claimed_at = now
        advice_request.claimed_by = request.worker
        advice_request.claim_token = uuid.uuid4()
        advice_request.lease_expires_at = _lease_deadline()
        advice_request.save(
            update_fields=[
                "status",
                "attempts_used",
                "claimed_at",
                "claimed_by",
                "claim_token",
                "lease_expires_at",
                "updated_at",
            ]
        )
        transaction_row = advice_request.transaction

    return JsonResponse(
        {
            "request": advice_request.pk,
            "claim_token": str(advice_request.claim_token),
            "lease_expires_at": advice_request.lease_expires_at.isoformat(),
            "attempts_remaining": max(
                0, settings.WORKER_MAX_ATTEMPTS - advice_request.attempts_used
            ),
            "transaction": {
                "id": transaction_row.pk,
                "description": transaction_row.description,
                "amount_pence": transaction_row.amount_pence,
                "account_kind": transaction_row.account.kind,
            },
        }
    )


def _release_advice_claim(advice_request, *, failed=False, failure=""):
    """Clear fencing fields and either retry or stop after the attempt budget."""
    advice_request.claimed_at = None
    advice_request.claimed_by = None
    advice_request.claim_token = None
    advice_request.lease_expires_at = None
    if failed:
        advice_request.last_failure = failure[:500]
        if advice_request.attempts_used >= settings.WORKER_MAX_ATTEMPTS:
            advice_request.status = AdviceRequest.Status.FAILED
        else:
            advice_request.status = AdviceRequest.Status.PENDING
    advice_request.save(
        update_fields=[
            "status",
            "last_failure",
            "claimed_at",
            "claimed_by",
            "claim_token",
            "lease_expires_at",
            "updated_at",
        ]
    )


@csrf_exempt
@require_POST
@worker_required
def advice_result(request, pk):
    """Accept validated advice, an abstention, or a bounded failure.

    The claim is fenced by credential, unguessable token and lease: a worker
    whose lease lapsed and was reclaimed cannot complete the newer claim.
    """
    try:
        body = _json_body(request)
    except ApiError as exc:
        return _error(exc)
    outcome = body.get("outcome")
    if outcome not in {"suggested", "abstained", "failed"}:
        return JsonResponse({"error": "unsupported advice outcome"}, status=400)
    raw_token = body.get("claim_token")
    try:
        claim_token = uuid.UUID(str(raw_token))
    except (TypeError, ValueError):
        return JsonResponse({"error": "claim token is required"}, status=400)

    with transaction.atomic():
        advice_request = (
            AdviceRequest.objects.select_for_update()
            .select_related("transaction")
            .filter(
                pk=pk,
                status=AdviceRequest.Status.PROCESSING,
                claim_token=claim_token,
                claimed_by=request.worker,
            )
            .first()
        )
        if advice_request is None:
            return JsonResponse(
                {"error": "advice claim does not match an open attempt"}, status=409
            )
        if (
            advice_request.lease_expires_at is None
            or advice_request.lease_expires_at < timezone.now()
        ):
            return JsonResponse({"error": "advice lease lost"}, status=409)

        if outcome == "failed":
            _release_advice_claim(
                advice_request,
                failed=True,
                failure=str(body.get("failure") or "Advice unavailable."),
            )
            return JsonResponse({"status": advice_request.status})

        if outcome == "abstained":
            advice_request.status = AdviceRequest.Status.COMPLETED
            advice_request.last_failure = ""
            _release_advice_claim(advice_request)
            return JsonResponse({"status": advice_request.status})

        try:
            fields = advisory_fields(body.get("suggestion"))
        except ValueError as exc:
            _release_advice_claim(
                advice_request, failed=True, failure=f"Invalid advice: {exc}"
            )
            return JsonResponse({"error": str(exc)}, status=400)

        ClassificationSuggestion.objects.create(
            transaction=advice_request.transaction, **fields
        )
        advice_request.status = AdviceRequest.Status.COMPLETED
        advice_request.last_failure = ""
        _release_advice_claim(advice_request)
    return JsonResponse({"status": advice_request.status})
