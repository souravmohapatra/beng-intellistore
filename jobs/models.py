"""Job coordination and the scoped worker API.

One upload is one job. Pending work is not eligible merely because a worker is
awake: a job must be explicitly released (Process now, later the nightly batch).
The initial worker runs one job at a time.
"""

import hashlib
import secrets

from django.db import models

from ledger.models import Upload


class WorkerCredential(models.Model):
    """A replaceable machine credential scoped to the worker API."""

    label = models.CharField(max_length=100)
    token_hash = models.CharField(max_length=64, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    revoked_at = models.DateTimeField(null=True, blank=True)

    def __str__(self) -> str:
        return self.label

    @property
    def is_active(self) -> bool:
        return self.revoked_at is None

    @staticmethod
    def hash_token(token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    @classmethod
    def issue(cls, label: str) -> tuple["WorkerCredential", str]:
        """Create a credential and return it with its plaintext token, once."""
        token = secrets.token_urlsafe(32)
        credential = cls.objects.create(label=label, token_hash=cls.hash_token(token))
        return credential, token


class Job(models.Model):
    class Status(models.TextChoices):
        WAITING = "waiting", "Waiting for release"
        RELEASED = "released", "Released"
        PROCESSING = "processing", "Processing"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"

    upload = models.OneToOneField(Upload, on_delete=models.CASCADE, related_name="job")
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.WAITING
    )
    released_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["pk"]

    def __str__(self) -> str:
        return f"job {self.pk} ({self.status})"

    def latest_attempt(self):
        return self.attempts.order_by("-number").first()


class JobAttempt(models.Model):
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name="attempts")
    number = models.PositiveIntegerField()
    credential = models.ForeignKey(
        WorkerCredential, on_delete=models.PROTECT, related_name="attempts"
    )
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["pk"]
        constraints = [
            models.UniqueConstraint(
                fields=["job", "number"], name="unique_attempt_number_per_job"
            )
        ]

    @property
    def is_open(self) -> bool:
        return self.finished_at is None


class JobEvent(models.Model):
    """Sanitized progress markers reported by the worker."""

    attempt = models.ForeignKey(
        JobAttempt, on_delete=models.CASCADE, related_name="events"
    )
    stage = models.CharField(max_length=100)
    message = models.TextField(blank=True)
    recorded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["pk"]


class JobResult(models.Model):
    """A validated result submission, recorded once per attempt."""

    attempt = models.OneToOneField(
        JobAttempt, on_delete=models.CASCADE, related_name="result"
    )
    version = models.PositiveIntegerField()
    outcome = models.CharField(max_length=32)
    payload = models.JSONField()
    payload_sha256 = models.CharField(max_length=64)
    applied_at = models.DateTimeField(auto_now_add=True)


class SourceMapping(models.Model):
    """Confirmed account mapping for one recognised source identity.

    Identities are structural (layout family plus the section set), never
    account numbers. A changed identity must be confirmed again rather than
    silently reusing an earlier savings mapping.
    """

    source_identity = models.CharField(max_length=200, unique=True)
    primary_account = models.ForeignKey(
        "ledger.Account", on_delete=models.PROTECT, related_name="primary_mappings"
    )
    savings_account = models.ForeignKey(
        "ledger.Account",
        on_delete=models.PROTECT,
        related_name="savings_mappings",
        null=True,
        blank=True,
    )
    savings_source_identity = models.CharField(max_length=64, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return self.source_identity


class PublishedSection(models.Model):
    """A committed account section, used to avoid duplicating valid sections.

    Deduplication is per original and section account, so retrying a partially
    published import can add previously failed sections without repeating ones
    that already committed.
    """

    upload = models.ForeignKey(
        "ledger.Upload", on_delete=models.CASCADE, related_name="published_sections"
    )
    name = models.CharField(max_length=64)
    account = models.ForeignKey(
        "ledger.Account", on_delete=models.PROTECT, related_name="published_sections"
    )
    published_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["upload", "name"], name="one_section_record_per_upload"
            )
        ]
