"""Laptop worker: claim assigned work through the application API and report.

The worker never touches PostgreSQL or shared mounts; it downloads only the
source it was assigned, writes it to a temporary directory, and removes that
directory on completion.
"""

import json
import shutil
import tempfile
import urllib.error
import urllib.request
from pathlib import Path


class WorkerError(Exception):
    """The application rejected or failed a worker request."""


class WorkerClient:
    def __init__(self, base_url: str, token: str, timeout: float = 30.0):
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.timeout = timeout

    def _request(self, method: str, path: str, payload=None, raw: bool = False):
        data = None if payload is None else json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            f"{self.base_url}{path}",
            data=data,
            method=method,
            headers={
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                body = response.read()
                if response.status == 204:
                    return None
                return body if raw else json.loads(body)
        except urllib.error.HTTPError as exc:
            detail = exc.read()[:200].decode("utf-8", "replace")
            raise WorkerError(f"{method} {path} failed: {exc.code} {detail}") from exc

    def claim(self):
        return self._request("POST", "/api/worker/claims/")

    def download_source(self, job_id: int) -> bytes:
        return self._request("GET", f"/api/worker/jobs/{job_id}/source/", raw=True)

    def progress(self, job_id: int, stage: str, message: str = ""):
        return self._request(
            "POST",
            f"/api/worker/jobs/{job_id}/progress/",
            {"stage": stage, "message": message},
        )

    def submit_result(self, job_id: int, payload: dict):
        return self._request(
            "POST", f"/api/worker/jobs/{job_id}/result/", payload
        )


def process_one(client: WorkerClient, work_root: Path | None) -> dict | None:
    """Claim and process one job, cleaning temporary files in all cases."""
    claim = client.claim()
    if claim is None:
        return None

    workdir = Path(tempfile.mkdtemp(dir=work_root) if work_root else tempfile.mkdtemp())
    try:
        source = workdir / "source"
        source.write_bytes(client.download_source(claim["job"]))
        client.progress(claim["job"], "downloaded")
        client.progress(claim["job"], "inspected")

        result = {
            "version": claim["result_version"],
            "attempt": claim["attempt"],
            "outcome": "unsupported",
            "issues": [
                {
                    "code": "unsupported_layout",
                    "message": "No supported statement layout is implemented for this file.",
                }
            ],
            "sections": [],
        }
        submitted = client.submit_result(claim["job"], result)
        return {"job": claim["job"], **submitted}
    finally:
        shutil.rmtree(workdir, ignore_errors=True)
