"""Two-process restart check for originals and the nightly schedule cursor.

Each phase runs in its own interpreter, so only the database and data directory
can carry the receipt and schedule state across:

    python scripts/restart_check.py upload   # prints the upload id
    python scripts/restart_check.py verify <id>

This is local evidence through the application's HTTP interface (Django test
client), not a WSGI-server or physical power-loss proof.
"""

import hashlib
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "intellistore.settings")

import django  # noqa: E402

django.setup()

from django.conf import settings  # noqa: E402
from django.contrib.auth import get_user_model  # noqa: E402
from django.core.files.uploadedfile import SimpleUploadedFile  # noqa: E402
from django.test import Client  # noqa: E402
from django.urls import reverse  # noqa: E402

from jobs.management.commands.release_due_jobs import release_due_jobs  # noqa: E402
from jobs.models import Job  # noqa: E402
from ledger.models import Account, AccountKind, Upload  # noqa: E402

# A readable, currently unsupported export; digest and size were established
# outside the application with `shasum -a 256` and `wc -c`.
FIXTURE = b"Date,Description,Amount\n2026-08-01,Coffee,-3.20\n"
FIXTURE_SHA256 = "491997df56edfe6c1f165b29c3c5f899f88ae59feed9fe8fa79a962af634acc2"
FIXTURE_BYTES = 48
USERNAME = "restart-check"
PASSWORD = "local-restart-check-password"
SCHEDULE_TIME = datetime(2026, 10, 22, 21, 0, tzinfo=ZoneInfo("Europe/London"))


def sign_in() -> Client:
    settings.ALLOWED_HOSTS = [*settings.ALLOWED_HOSTS, "testserver"]
    user_model = get_user_model()
    if not user_model.objects.filter(username=USERNAME).exists():
        user_model.objects.create_user(USERNAME, password=PASSWORD)
    client = Client()
    if not client.login(username=USERNAME, password=PASSWORD):
        raise SystemExit("restart check: sign-in failed")
    return client


def upload(client: Client) -> str:
    account, _ = Account.objects.get_or_create(
        name="Restart check", defaults={"kind": AccountKind.CURRENT}
    )
    response = client.post(
        reverse("ledger:uploads"),
        {
            "account": account.pk,
            "file": SimpleUploadedFile(
                "restart.csv", FIXTURE, content_type="text/csv"
            ),
        },
    )
    if response.status_code != 302:
        raise SystemExit(f"restart check: upload failed with {response.status_code}")
    upload_id = str(Upload.objects.latest("pk").pk)
    if release_due_jobs(now=SCHEDULE_TIME) != 1:
        raise SystemExit("restart check: scheduled work was not released")
    return upload_id


def verify(client: Client, upload_id: str) -> None:
    upload = Upload.objects.select_related("original", "account").get(pk=int(upload_id))
    if upload.original.sha256 != FIXTURE_SHA256:
        raise SystemExit("restart check: receipt digest changed")
    if upload.original.byte_size != FIXTURE_BYTES:
        raise SystemExit("restart check: receipt size changed")
    stored = Path(settings.DATA_DIR) / upload.original.stored_path
    if hashlib.sha256(stored.read_bytes()).hexdigest() != FIXTURE_SHA256:
        raise SystemExit("restart check: stored bytes changed")

    response = client.get(reverse("ledger:upload_original", args=[upload.pk]))
    body = b"".join(response.streaming_content)
    if response.status_code != 200 or body != FIXTURE:
        raise SystemExit("restart check: original could not be reopened")

    if release_due_jobs(now=SCHEDULE_TIME + timedelta(minutes=1)) != 0:
        raise SystemExit("restart check: schedule cursor replayed a released batch")
    job = Job.objects.get(upload_id=upload.pk)
    if job.status != Job.Status.RELEASED:
        raise SystemExit("restart check: schedule state did not survive process restart")

    listing = client.get(reverse("ledger:uploads"))
    if "restart.csv" not in listing.content.decode():
        raise SystemExit("restart check: receipt missing from listing")
    print("restart check ok")


def main(argv: list[str]) -> None:
    if len(argv) < 2 or argv[1] not in {"upload", "verify"}:
        raise SystemExit(__doc__)
    client = sign_in()
    if argv[1] == "upload":
        print(upload(client))
    else:
        if len(argv) < 3:
            raise SystemExit("restart check: verify needs an upload id")
        verify(client, argv[2])


if __name__ == "__main__":
    main(sys.argv)
