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

## LAN deployment: two setup scripts

Copy this checkout at the same revision to each host, then run the mini-PC script
first and the laptop script second. Run from a normal terminal with `sudo`; the
scripts prompt before packages, deployment/migrations and service activation.
They do not deploy anything until you run and approve them.

The setup commit is local until you authorize a push. From the Mac, copy only
committed files into a **new revision-specific directory** on each host (wake the
laptop yourself if SSH is unavailable):

```bash
revision=$(git rev-parse --short HEAD)
for host in beng-mini-pc beng-laptop; do
  git archive HEAD | ssh "$host" \
    "umask 077; mkdir -p ~/intellistore-$revision; tar --keep-old-files -x -C ~/intellistore-$revision"
done
```

This does not copy `.agent/`, untracked statements or your local environment.
It refuses to overwrite files in an existing destination. On each host,
`cd ~/intellistore-<revision>` before the commands below.

```bash
# On beng-mini-pc, from the checkout:
sudo ./beng-mini-pc-setup.sh

# Copy this credential privately to the laptop script's hidden prompt.
# Do not paste the token into chat, Git, a shell command argument, or a ticket.
sudo cat /etc/beng-intellistore/laptop-worker.token

# On beng-laptop, from a checkout of the SAME revision:
sudo ./beng-laptop-setup.sh
```

The mini-PC wizard verifies the selected Docker endpoint and local filesystem,
sets data permissions, generates secrets, builds/migrates the isolated project,
creates your login and a scoped worker token, and installs the application
service plus 21:00 Europe/London release timer. The laptop wizard checks Docker
(offering Ubuntu packages only if absent), builds the worker container, checks
app connectivity, and installs its startup service. It does not need GPU/Ollama
or shared access to the database/originals.

### Verified host defaults

- Mini-PC LAN address: `192.168.68.55`; unused TCP port at inspection: **8017**.
  Setup rechecks before binding. Only that LAN address is published, not
  `0.0.0.0`; no firewall, reverse proxy or router settings are changed.
- Base: `/mnt/media/intelli-store`, local ext4, owned by `beng` (`1000:1000`).
  About 257 GiB was free during inspection. Data is not placed on NAS or in
  the Docker daemon's smaller root-filesystem storage.
- Controller: `http://192.168.68.55:8787`, the same controller embedded by the
  homepage at port 3000. Setup checks it from the app container with GET only.
  The existing action token is fetched in memory; no controller API key is needed.
- Selected socket: `unix:///var/run/docker.sock`. During inspection it served
  the snap Docker daemon. Scripts print/verify the selected endpoint and never
  change the global Docker context or replace an existing daemon.
- Laptop SSH was unreachable during preparation. Its script checks actual local
  prerequisites when you run it; current laptop installation is not claimed.

The mini-PC's Docker snap currently has **no removable-media connection**.
Unix ownership alone is insufficient for `/mnt/media`: the wizard asks before
granting the [documented Docker snap media permission](https://github.com/canonical/docker-snap#usage):

```bash
sudo snap connect docker:removable-media
```

That grants the Docker snap access to `/mnt` and `/media`; it does not change
Unix ownership or move Docker's data root. Docker snap also documents an
AppArmor restriction on `no-new-privileges=true`. The scripts select
`INTELLISTORE_NO_NEW_PRIVILEGES=false` for that daemon (matching existing
mini-PC containers), true elsewhere, and warn before deployment. The app and
worker remain non-root, read-only and without Linux capabilities.

The browser URL is `http://192.168.68.55:8017/`. The mini-PC script asks for the
Pi-hole DNS name to include in Django's allowed hosts. DNS only maps the address:
`http://<your-dns-name>:8017/` still needs the port. This first deployment is
trusted-LAN HTTP: login passwords, worker tokens and statements are unencrypted
on the network. Do not port-forward it to the Internet. TLS/VPN work is deferred,
not silently provided by DNS.

### Permissions and persistent data

| Host path | Owner / mode | Purpose |
| --- | --- | --- |
| `/mnt/media/intelli-store` | `1000:1000`, `0750` | Dedicated base; no recursive permission changes |
| `/mnt/media/intelli-store/data` | `1000:1000`, `0700` | App-owned originals; mounted at `/data` |
| `/mnt/media/intelli-store/postgres` | Initially root `0700`; PostgreSQL entrypoint assigns `70:70` | Dedicated PostgreSQL data; do not chown to the app user |
| `/etc/beng-intellistore` | root, `0700`; files `0600` | Mini-PC runtime secrets and worker token |
| `/etc/beng-intellistore-worker` | root, `0700`; files `0600` | Laptop URL and scoped worker credential |

For a **new, empty** deployment, the permissions portion can also be done by hand:

```bash
sudo chmod 0750 /mnt/media/intelli-store
sudo install -d -o 1000 -g 1000 -m 0700 /mnt/media/intelli-store/data
# New database directory only; do not reset ownership on an existing database:
sudo install -d -o root -g root -m 0700 /mnt/media/intelli-store/postgres
```

The scripts preserve existing secrets and data on re-run and do not delete
volumes, wipe directories, or migrate a previous named database volume into these
bind paths. They refuse an ambiguous existing database/configuration instead of
silently creating a second empty database.

### Runtime configuration

The scripts write root-only `runtime.env` files **outside the checkout**. Defaults
are shown in prompts; generated secrets are not printed.

| Mini-PC setting | Value / source |
| --- | --- |
| `DOCKER_HOST`, `INTELLISTORE_COMPOSE_DIR` | Explicit local socket and checkout; used by systemd too |
| `INTELLISTORE_HOST_DATA_DIR`, `INTELLISTORE_HOST_DATABASE_DIR` | `data/` and `postgres/` under your base |
| `INTELLISTORE_BIND_ADDRESS`, `INTELLISTORE_HTTP_PORT` | `192.168.68.55`, `8017` |
| `DJANGO_ALLOWED_HOSTS` | LAN IP, optional Pi-hole name, localhost and loopback; no scheme/port |
| `DJANGO_SECRET_KEY`, `POSTGRES_PASSWORD` | Random values generated once locally; preserve on re-run |
| `LAPTOP_CONTROLLER_URL` | `http://192.168.68.55:8787` |
| `APP_UID`, `APP_GID` | `1000`, `1000` for the observed `beng` owner |
| `INTELLISTORE_NO_NEW_PRIVILEGES` | False for the detected snap daemon; true otherwise (compatibility noted above) |

The laptop's runtime stores `INTELLISTORE_APP_URL` (default
`http://192.168.68.55:8017`), the token copied from the mini-PC, the explicit Docker
socket/checkout, and `WORKER_POLL_SECONDS` (30). With polling enabled, the worker
drains released jobs, waits while idle, and checks again while awake; suspension
pauses it and normal resume continues polling. It has no automatic sleep/wake
policy and no mini-PC database/controller credentials. Temporary source files
live in the container's private `/work` tmpfs.

### Operation and remaining limits

- Mini-PC services: `intellistore-app.service`, `intellistore-release.timer`.
- Laptop service: `intellistore-worker.service`.
- Use `sudo systemctl status <unit>` and `sudo journalctl -u <unit>` for startup
  diagnostics; the setup scripts print container log/stop commands.
- Stopping these services stops only this project's containers; never use
  `docker compose down --volumes` to stop an installation.
- For a full scheduled stop, disable the timer first:
  `sudo systemctl disable --now intellistore-release.timer`, then stop the app.
  Otherwise a later release requires/starts the app service again.
- Re-run the relevant script for explicit rebuild/configuration updates; it does
  not pull code automatically. Preserve the root-only runtime files and copy the
  same revision to both hosts.
- The timer can catch up immediately on activation; starting the worker can
  process released work. The scripts warn and require confirmation.
- Setup does not configure NAS backups/restore. Those remain unimplemented; do
  not treat a first test deployment as the only copy of private financial data.
- Live wake/lease lifecycle, target timings and real-host acceptance remain
  unverified until you run setup and perform the agreed checks.

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
