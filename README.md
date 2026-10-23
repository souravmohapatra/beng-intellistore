# Beng Statement Intelligence

Private statement import and financial dashboard for Sourav. Scope, reporting
semantics and acceptance criteria are in the
[HLD](beng-document-intelligence-hld.md) and the
[first-release specification](.scratch/initial-release/spec.md). Domain
vocabulary is in [GLOSSARY.md](GLOSSARY.md).

## Local development (Mac)

Selected test runtime: Docker Desktop on the Mac, with PostgreSQL in Compose.
The development database listens on loopback port 55432 only and keeps its data
in the `beng-intellistore` Compose volume, so existing local PostgreSQL services
and private data are untouched.

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
docker compose up -d --wait      # development database, port 55432
.venv/bin/python manage.py migrate
.venv/bin/python manage.py createsuperuser
.venv/bin/python manage.py runserver
```

Then open <http://127.0.0.1:8000/>. The overview requires sign-in; there is no
self-service registration. Define named accounts in the Django admin
(`/admin/`) with kinds current, card or savings.

Accepted originals are stored under `var/` (`INTELLISTORE_DATA_DIR` overrides).
Intake checks content, not extensions: PDFs (max 100 pages) and UTF-8 text/CSV up
to 20 MiB are preserved; damaged, password-protected or image-only PDFs are
rejected with a specific reason. The four supplied statement families are
implemented for Lloyds Current, Lloyds Credit, Amex Credit, and Revolut personal
GBP plus savings GBP, with deterministic interpretation and reconciliation.
Other readable layouts are preserved as **Unsupported** rather than claiming
an import.

Stop the database with `docker compose down`. This keeps the development volume.
`docker compose down --volumes` **destroys** the development database and is only
for deliberately discarding it.

## Worker

Accepting an upload creates a waiting job. Waiting work is not claimable just
because a worker is running. Release it with **Process now**, or run
`python manage.py release_due_jobs` at 21:00 Europe/London. The readiness state
uses the first authenticated worker claim as proof of readiness; claim requests
and the Uploads page reconcile an expired ten-minute window and return
released jobs to waiting.

The mini-PC systemd timer and Docker stack are prepared locally but not installed
on the host. The app can use the existing private laptop controller by setting
`LAPTOP_CONTROLLER_URL` to an address reachable from its container. There is no
separate controller credential: the client reads the controller page's rotating
action token, sends it as `X-CSRF-Token`, and does not log or store it beyond
memory. An empty URL disables wake and keep-awake calls; released work then
remains queued.

Keep-awake leases are separate from job ownership. The app creates one bounded
lease per worker attempt, extends it only near expiry by a short amount, stops at
the controller's eight-hour creation ceiling, and releases only its own lease
when the result commits or a stale attempt is reaped. Defaults are 20 minutes,
renew when 5 minutes remain, and extend by 10 minutes; `P-06` calibration on the
target laptop remains open. Actual wake/lease lifecycle evidence and the laptop
worker service remain open under ticket 21.

The worker drains every eligible released job and then exits, allowing normal
laptop power management to sleep. The following native command is for local
development only; the production laptop worker container/service remains open
under ticket 21.

```bash
.venv/bin/python manage.py provision_worker --label laptop   # prints the token once
WORKER_TOKEN=<token> .venv/bin/python -m worker \
    --base-url http://127.0.0.1:8000 --work-root /tmp/worker
```

The worker credential is replaceable and scoped to claims, its assigned source,
progress and result submission; it cannot sign in as the user or reach the
database. The worker downloads only its assigned original into a temporary
directory and removes it when done.

## Mini-PC deployment configuration

`compose.production.yaml` defines the app, PostgreSQL, and one-off `release-jobs`
service in one Compose project, so the nightly command uses the app's database.
The app binds only to loopback and stores originals in the required existing
`INTELLISTORE_HOST_DATA_DIR`; the Postgres named volume stays on the selected
Docker daemon's local storage. The Compose project name is fixed as
`beng-intellistore-production`.

The timer in `deploy/systemd/intellistore-release.timer` runs daily at 21:00
Europe/London with one persistent catch-up after downtime. Its service requires
an explicit `DOCKER_HOST` and absolute `INTELLISTORE_COMPOSE_DIR`; it cannot fall
back to the Docker CLI's default daemon. `runtime.env` must also provide
`DJANGO_SECRET_KEY`, `DJANGO_ALLOWED_HOSTS`, `POSTGRES_PASSWORD`, and
`INTELLISTORE_HOST_DATA_DIR`. Set `LAPTOP_CONTROLLER_URL` to a private controller
address reachable from both the app and `release-jobs` containers; `127.0.0.1`
inside a container is the container itself. `APP_UID`/`APP_GID` default to
`1000:1000`; set them to match the existing local originals directory owner.
Keep the host file root-owned with mode 0600; do not commit secrets. The unit
runs as root by default, so its selected Docker endpoint grants
host-root-equivalent control.
For manual Compose commands, export the runtime variables and pass the same file
with `--env-file`.

Before enabling the timer, select and verify the mini-PC Docker daemon, confirm
the local data path and permissions, and obtain approval for deployment and any
migration affecting existing data. The following commands are a runbook only;
replace the angle-bracket values and execute on the mini-PC after approval:

```bash
sudo docker --host=<selected-mini-PC-endpoint> compose \
  --env-file /etc/beng-intellistore/runtime.env \
  --project-directory=<absolute-checkout-path> \
  -f <absolute-checkout-path>/compose.production.yaml config --quiet
sudo docker --host=<selected-mini-PC-endpoint> compose \
  --env-file /etc/beng-intellistore/runtime.env \
  --project-directory=<absolute-checkout-path> \
  -f <absolute-checkout-path>/compose.production.yaml build app release-jobs
# Run only after approval for the target database migration:
sudo docker --host=<selected-mini-PC-endpoint> compose \
  --env-file /etc/beng-intellistore/runtime.env \
  --project-directory=<absolute-checkout-path> \
  -f <absolute-checkout-path>/compose.production.yaml run --rm release-jobs migrate
sudo docker --host=<selected-mini-PC-endpoint> compose \
  --env-file /etc/beng-intellistore/runtime.env \
  --project-directory=<absolute-checkout-path> \
  -f <absolute-checkout-path>/compose.production.yaml up -d --wait app
sudo install -m 0644 deploy/systemd/intellistore-release.service /etc/systemd/system/
sudo install -m 0644 deploy/systemd/intellistore-release.timer /etc/systemd/system/
sudo systemd-analyze verify /etc/systemd/system/intellistore-release.service \
  /etc/systemd/system/intellistore-release.timer
sudo systemctl daemon-reload
sudo systemctl enable --now intellistore-release.timer
```

Host clock, daemon endpoint, HTTPS proxy, NAS backup, controller wake
integration, worker drain, and actual-host acceptance remain open. No host
configuration was installed or enabled.

## Checks

`./scripts/smoke.sh` creates its own venv, installs the pins, and runs the
checks against a per-invocation Compose project, loopback port, and temporary
data directory. It runs migrations, the test suite and a two-process restart
check, then removes only its own resources:

```bash
./scripts/smoke.sh              # isolated; removes its database and data after
./scripts/smoke.sh --keep       # prints the project, port and data directory it left
```

Pinned Python dependencies live in `requirements.txt`; `compose.yaml` and
`compose.production.yaml` pin PostgreSQL images. Verified on 2026-10-22:
- Python 3.14.7 (Homebrew and `python:3.14.7-slim-bookworm`)
- Django 6.1.2
- psycopg 3.2.13
- Gunicorn 23.0.0
- WhiteNoise 6.9.0
- PostgreSQL 17.11 (alpine image)
- Docker Desktop 4.96.0 (server 29.9.1) / Compose v5.6.0
