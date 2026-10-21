# Beng Statement Intelligence

Private statement import and financial dashboard for Sourav. Scope, reporting
semantics and acceptance criteria are in the
[HLD](beng-document-intelligence-hld.md) and the
[first-release specification](.scratch/initial-release/spec.md). Domain
vocabulary is in [GLOSSARY.md](GLOSSARY.md).

## Local development (Mac)

Selected test runtime: Docker Desktop on the Mac, with PostgreSQL in Compose.
The database listens on loopback port 55432 only and keeps its data in a
project-scoped volume, so existing local PostgreSQL services and private data
are untouched.

```bash
./scripts/smoke.sh --keep     # create venv, install pins, start PostgreSQL, run tests
.venv/bin/python manage.py migrate
.venv/bin/python manage.py createsuperuser
.venv/bin/python manage.py runserver
```

Then open <http://127.0.0.1:8000/>. The overview requires sign-in; there is no
self-service registration. Define named accounts in the Django admin
(`/admin/`) with kinds current, card or savings.

Stop the isolated database with `docker compose down --volumes`.

Pinned dependencies live in `requirements.txt`; `compose.yaml` pins the
PostgreSQL image. Peer versions:

- Python 3.14 (Homebrew)
- Django 6.1.2
- psycopg 3.2.13
- PostgreSQL 17.11 (alpine image)
- Docker Desktop 29.9.1 / Compose v5.6.0
