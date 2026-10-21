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
to 20 MiB are preserved; damaged, password-protected or image-only PDFs give a
specific rejection. No statement layout is implemented yet, so receipts currently
show **Unsupported** rather than claiming an import.

Stop the database with `docker compose down`. This keeps the development volume.
`docker compose down --volumes` **destroys** the development database and is only
for deliberately discarding it.

## Worker

Accepting an upload creates a waiting job. Waiting work is not claimable just
because a worker is running: release it with **Process now** (or the later
nightly batch). One job is processed at a time.

```bash
.venv/bin/python manage.py provision_worker --label laptop   # prints the token once
WORKER_TOKEN=<token> .venv/bin/python -m worker \
    --base-url http://127.0.0.1:8000 --work-root /tmp/worker
```

The worker credential is replaceable and scoped to claims, its assigned source,
progress and result submission; it cannot sign in as the user or reach the
database. The worker downloads only its assigned original into a temporary
directory and removes it when done.

## Checks

`./scripts/smoke.sh` creates its own venv, installs the pins, and runs the
checks against a per-invocation Compose project, loopback port, and temporary
data directory. It runs migrations, the test suite and a two-process restart
check, then removes only its own resources:

```bash
./scripts/smoke.sh              # isolated; removes its database and data after
./scripts/smoke.sh --keep       # prints the project, port and data directory it left
```

Pinned dependencies live in `requirements.txt`; `compose.yaml` pins the
PostgreSQL image. Verified on 2026-10-21:

- Python 3.14.7 (Homebrew)
- Django 6.1.2
- psycopg 3.2.13
- PostgreSQL 17.11 (alpine image)
- Docker Desktop 4.96.0 (server 29.9.1) / Compose v5.6.0
