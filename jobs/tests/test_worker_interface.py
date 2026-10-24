"""Behavioral tests for the scoped worker API and job coordination."""

import json
import select
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from django.test import LiveServerTestCase, TestCase, TransactionTestCase
from django.urls import reverse

from jobs.models import Job, JobAttempt, JobResult, WorkerCredential
from ledger.models import Upload
from ledger.tests.fixtures import CSV_TEXT
from ledger.tests.support import UploadSetupMixin

BASE_DIR = Path(__file__).resolve().parents[2]


class WorkerTestCase(UploadSetupMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.credential, self.token = WorkerCredential.issue("test-laptop")

    def api(self, method, name, payload=None, *, args=(), token=None):
        headers = {"HTTP_AUTHORIZATION": f"Bearer {token or self.token}"}
        kwargs = {"content_type": "application/json", **headers}
        if payload is not None:
            kwargs["data"] = json.dumps(payload)
        return getattr(self.client, method)(reverse(name, args=args), **kwargs)

    def claim(self, token=None):
        return self.api("post", "jobs:claim", token=token)

    def release(self):
        response = self.client.post(reverse("jobs:process_now"))
        self.assertEqual(response.status_code, 302)

    def upload_and_release(self, filename="export.txt"):
        self.upload(CSV_TEXT, filename=filename)
        self.release()
        return Upload.objects.get(filename=filename)

    def claim_one(self):
        response = self.claim()
        self.assertEqual(response.status_code, 200)
        return response.json()

    def submit(self, claimed, payload=None, token=None):
        body = payload or {
            "version": 1,
            "attempt": claimed["attempt"],
            "outcome": "unsupported",
            "issues": [{"code": "unsupported_layout", "message": "No layout implemented."}],
        }
        return self.api(
            "post", "jobs:result", body, args=[claimed["job"]], token=token
        )


class CredentialScopeTests(WorkerTestCase):
    def test_worker_token_cannot_use_user_pages(self):
        from django.test import Client

        response = Client().get(
            reverse("ledger:uploads"),
            HTTP_AUTHORIZATION=f"Bearer {self.token}",
        )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(response["Location"].startswith("/login/"))

    def test_api_rejects_missing_wrong_and_revoked_tokens(self):
        self.assertEqual(self.client.post(reverse("jobs:claim")).status_code, 401)
        self.assertEqual(self.claim(token="not-a-token").status_code, 401)

        self.credential.revoked_at = "2026-10-21T00:00:00Z"
        self.credential.save(update_fields=["revoked_at"])
        self.assertEqual(self.claim().status_code, 401)

    def test_source_is_only_readable_by_the_claiming_credential(self):
        self.upload_and_release()
        claimed = self.claim_one()

        ok = self.client.get(
            reverse("jobs:source", args=[claimed["job"]]),
            HTTP_AUTHORIZATION=f"Bearer {self.token}",
        )
        self.assertEqual(ok.status_code, 200)
        self.assertEqual(b"".join(ok.streaming_content), CSV_TEXT)

        _other, other_token = WorkerCredential.issue("another-laptop")
        denied = self.client.get(
            reverse("jobs:source", args=[claimed["job"]]),
            HTTP_AUTHORIZATION=f"Bearer {other_token}",
        )
        self.assertEqual(denied.status_code, 403)


class ReleaseAndClaimTests(WorkerTestCase):
    def test_waiting_job_is_not_claimable_until_released(self):
        self.upload(CSV_TEXT)

        self.assertEqual(self.claim().status_code, 204)

        self.release()
        body = self.claim_one()
        self.assertEqual(body["upload"]["filename"], "statement.pdf")
        self.assertEqual(body["result_version"], 1)
        self.assertEqual(Job.objects.get().status, Job.Status.PROCESSING)

    def test_process_now_releases_all_waiting_jobs_once(self):
        self.upload(CSV_TEXT, filename="one.txt")
        self.upload(CSV_TEXT, filename="two.txt")

        self.release()
        self.release()

        self.assertEqual(
            set(Job.objects.values_list("status", flat=True)), {Job.Status.RELEASED}
        )
        self.assertEqual(Job.objects.count(), 2)
        self.assertEqual(JobAttempt.objects.count(), 0)

    def test_only_one_job_is_active_at_a_time(self):
        self.upload(CSV_TEXT, filename="one.txt")
        self.upload(CSV_TEXT, filename="two.txt")
        self.release()

        first = self.claim_one()
        self.assertEqual(self.claim().status_code, 204)

        self.assertEqual(self.submit(first).status_code, 200)
        second = self.claim_one()
        self.assertNotEqual(second["job"], first["job"])


class RoundTripTests(WorkerTestCase):
    def test_progress_is_recorded_and_visible_on_the_receipt(self):
        upload = self.upload_and_release()
        claimed = self.claim_one()

        response = self.api(
            "post",
            "jobs:progress",
            {"stage": "downloaded", "message": "source fetched"},
            args=[claimed["job"]],
        )
        self.assertEqual(response.status_code, 200)

        detail = self.client.get(
            reverse("ledger:upload_detail", args=[upload.pk])
        )
        self.assertContains(detail, "downloaded")

    def test_unsupported_result_completes_the_job_without_financial_effects(self):
        upload = self.upload_and_release()
        claimed = self.claim_one()

        response = self.submit(claimed)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["outcome"], "unsupported")
        job = Job.objects.get()
        self.assertEqual(job.status, Job.Status.COMPLETED)
        self.assertEqual(upload.__class__.objects.get(pk=upload.pk).status, Upload.Status.UNSUPPORTED)
        self.assertEqual(JobResult.objects.count(), 1)

        detail = self.client.get(
            reverse("ledger:upload_detail", args=[upload.pk])
        )
        self.assertContains(detail, "Completed")
        self.assertContains(detail, "unsupported_layout")

    def test_identical_resubmission_returns_recorded_success(self):
        self.upload_and_release()
        claimed = self.claim_one()

        first = self.submit(claimed)
        second = self.submit(claimed)

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertTrue(second.json()["already_recorded"])
        self.assertEqual(JobResult.objects.count(), 1)
        self.assertEqual(JobAttempt.objects.filter(finished_at__isnull=True).count(), 0)

    def test_conflicting_payload_for_the_same_attempt_is_rejected(self):
        self.upload_and_release()
        claimed = self.claim_one()
        self.submit(claimed)

        conflict = self.submit(
            claimed,
            payload={
                "version": 1,
                "attempt": claimed["attempt"],
                "outcome": "failed",
                "issues": [],
            },
        )

        self.assertEqual(conflict.status_code, 409)
        self.assertEqual(JobResult.objects.count(), 1)

    def test_unknown_version_or_outcome_is_rejected(self):
        self.upload_and_release()
        claimed = self.claim_one()

        bad_version = self.submit(
            claimed,
            payload={"version": 99, "attempt": claimed["attempt"], "outcome": "unsupported"},
        )
        self.assertEqual(bad_version.status_code, 400)

        bad_outcome = self.submit(
            claimed,
            payload={"version": 1, "attempt": claimed["attempt"], "outcome": "invented"},
        )
        self.assertEqual(bad_outcome.status_code, 400)

    def test_result_requires_an_open_attempt_of_this_job(self):
        self.upload_and_release()
        claimed = self.claim_one()

        wrong_attempt = self.submit(
            claimed,
            payload={"version": 1, "attempt": claimed["attempt"] + 99, "outcome": "unsupported"},
        )
        self.assertEqual(wrong_attempt.status_code, 409)


class WorkerProcessTests(UploadSetupMixin, LiveServerTestCase):
    def test_worker_claims_downloads_returns_outcome_and_cleans_temp_files(self):
        self.upload(CSV_TEXT, filename="export.txt")
        upload = Upload.objects.get(filename="export.txt")
        self.client.post(reverse("jobs:process_now"))
        _credential, token = WorkerCredential.issue("laptop-process")
        work_root = Path(tempfile.mkdtemp())
        self.addCleanup(lambda: __import__("shutil").rmtree(work_root, ignore_errors=True))

        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "worker",
                "--base-url",
                self.live_server_url,
                f"--token={token}",
                "--work-root",
                str(work_root),
            ],
            cwd=BASE_DIR,
            capture_output=True,
            text=True,
            timeout=90,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("unsupported", completed.stdout)
        job = Job.objects.get(upload=upload)
        self.assertEqual(job.status, Job.Status.COMPLETED)
        self.assertEqual(list(work_root.iterdir()), [])


    def test_worker_drains_all_released_jobs_then_exits(self):
        self.upload(CSV_TEXT, filename="first-drain.txt")
        self.upload(CSV_TEXT, filename="second-drain.txt")
        uploads = list(
            Upload.objects.filter(
                filename__in=["first-drain.txt", "second-drain.txt"]
            ).order_by("filename")
        )
        self.client.post(reverse("jobs:process_now"))
        _credential, token = WorkerCredential.issue("laptop-drain")
        work_root = Path(tempfile.mkdtemp())
        self.addCleanup(
            lambda: __import__("shutil").rmtree(work_root, ignore_errors=True)
        )

        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "worker",
                "--base-url",
                self.live_server_url,
                f"--token={token}",
                "--work-root",
                str(work_root),
            ],
            cwd=BASE_DIR,
            capture_output=True,
            text=True,
            timeout=90,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        results = [
            json.loads(line)
            for line in completed.stdout.splitlines()
            if line.startswith("{")
        ]
        self.assertEqual(len(results), 2)
        self.assertEqual(
            {result["job"] for result in results},
            {upload.job.pk for upload in uploads},
        )
        self.assertFalse(
            Job.objects.filter(
                pk__in=[upload.job.pk for upload in uploads]
            ).exclude(status=Job.Status.COMPLETED).exists()
        )
        self.assertEqual(list(work_root.iterdir()), [])

    def test_polling_worker_processes_jobs_released_after_it_becomes_idle(self):
        self.upload(CSV_TEXT, filename="later-release.txt")
        job = Job.objects.get(upload__filename="later-release.txt")
        _, token = WorkerCredential.issue("polling-laptop")
        with tempfile.TemporaryDirectory() as work_root:
            process = subprocess.Popen(
                [
                    sys.executable, "-m", "worker",
                    "--base-url", self.live_server_url,
                    f"--token={token}", "--work-root", work_root,
                    "--poll-interval", "0.1",
                ],
                cwd=BASE_DIR, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                text=True,
            )
            try:
                self.assertTrue(select.select([process.stdout], [], [], 15)[0])
                first_line = process.stdout.readline().strip()
                self.assertEqual(first_line, "no work")
                job.refresh_from_db()
                self.assertEqual(job.status, Job.Status.WAITING)
                self.client.post(reverse("jobs:process_now"))
                deadline = time.monotonic() + 15
                while True:
                    remaining = deadline - time.monotonic()
                    self.assertGreater(remaining, 0, "worker never processed the release")
                    self.assertTrue(
                        select.select([process.stdout], [], [], remaining)[0]
                    )
                    line = process.stdout.readline().strip()
                    if line != "no work":
                        result = json.loads(line)
                        break
                self.assertEqual(result["job"], job.pk)
                self.assertEqual(result["outcome"], "unsupported")
                job.refresh_from_db()
                self.assertEqual(job.status, Job.Status.COMPLETED)
                self.assertEqual(list(Path(work_root).iterdir()), [])
            finally:
                process.terminate()
                process.communicate(timeout=10)


class ConcurrentClaimTests(UploadSetupMixin, TransactionTestCase):
    """Two workers racing must not activate two jobs."""

    def setUp(self):
        super().setUp()
        self.credential, self.token = WorkerCredential.issue("racing-laptop")

    def test_simultaneous_claims_activate_exactly_one_job(self):
        from threading import Barrier, Thread

        from django.db import connections
        from django.test import Client

        self.upload(CSV_TEXT, filename="one.txt")
        self.upload(CSV_TEXT, filename="two.txt")
        self.client.post(reverse("jobs:process_now"))

        barrier = Barrier(2)
        statuses = []

        def claim_once():
            try:
                barrier.wait(timeout=10)
                response = Client().post(
                    reverse("jobs:claim"),
                    content_type="application/json",
                    HTTP_AUTHORIZATION=f"Bearer {self.token}",
                )
                statuses.append(response.status_code)
            finally:
                connections.close_all()

        threads = [Thread(target=claim_once) for _ in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=20)

        self.assertEqual(sorted(statuses), [200, 204])
        self.assertEqual(Job.objects.filter(status=Job.Status.PROCESSING).count(), 1)
        self.assertEqual(JobAttempt.objects.filter(finished_at__isnull=True).count(), 1)
