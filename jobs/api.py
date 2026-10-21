"""Scoped worker API: claims, assigned source, progress, results.

Authentication is a replaceable bearer credential. These endpoints grant no
user session, no database access and no access to unrelated originals.
"""

import hashlib
import json
from functools import wraps

from django.db import connection, transaction
from django.db.models import Max
from django.http import FileResponse, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST
from django.conf import settings
from pathlib import Path

from jobs.models import Job, JobAttempt, JobEvent, JobResult, WorkerCredential
from jobs.publication import apply_result, validate_result_payload
from ledger.models import Upload

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
    if publication.rejected:
        return "failed"
    if publication.deferred:
        return "partial"
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
        if Job.objects.select_for_update().filter(status=Job.Status.PROCESSING).exists():
            return HttpResponse(status=204)

        job = (
            Job.objects.select_for_update()
            .filter(status=Job.Status.RELEASED)
            .order_by("released_at", "pk")
            .first()
        )
        if job is None:
            return HttpResponse(status=204)

        job.status = Job.Status.PROCESSING
        job.save(update_fields=["status"])

        highest = job.attempts.aggregate(highest=Max("number"))["highest"] or 0
        attempt = JobAttempt.objects.create(
            job=job, number=highest + 1, credential=request.worker
        )

    return JsonResponse(
        {
            "job": job.pk,
            "attempt": attempt.pk,
            "result_version": RESULT_VERSION,
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
            return JsonResponse({"error": "attempt does not belong to this job"}, status=409)

        recorded = JobResult.objects.filter(attempt=attempt).first()
        if recorded is not None:
            if recorded.payload_sha256 == payload_hash:
                return JsonResponse(
                    {
                        "outcome": recorded.outcome,
                        "job": job.pk,
                        "already_recorded": True,
                    }
                )
            return JsonResponse({"error": "conflicting payload"}, status=409)

        if not attempt.is_open:
            return JsonResponse({"error": "no open attempt for this job"}, status=409)

        if body.get("version") != RESULT_VERSION:
            return JsonResponse({"error": "unsupported result version"}, status=400)
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
        attempt.save(update_fields=["finished_at"])
        job.status = Job.Status.COMPLETED
        job.save(update_fields=["status"])
        if upload_status != job.upload.status:
            job.upload.status = upload_status
            job.upload.save(update_fields=["status"])

    return JsonResponse(
        {"outcome": effective_outcome, "job": job.pk, "already_recorded": False}
    )
