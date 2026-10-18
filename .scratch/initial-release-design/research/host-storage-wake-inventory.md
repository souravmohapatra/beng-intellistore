# Host, storage, and wake inventory

Inspected: 2026-10-18. Scope: read-only checks; no wake, sleep, storage writes,
installs, service changes, privileged operations, or deployments.

## Mini-PC: directly observed

The configured `beng-mini-pc` SSH alias authenticated successfully.

| Area | Observation | Design implication or limit |
| --- | --- | --- |
| OS | Ubuntu 24.04.3 LTS, Linux 6.8.0-107-generic, x86_64 | Concrete Linux deployment target. |
| CPU/RAM | Intel N100, four cores, 15 GiB RAM; about 10 GiB available at inspection | Supports runtime planning; not a capacity/performance benchmark. |
| Runtime | Docker 29.1.5, Compose v5.0.1, Python 3.12.3 | Existing container and Python facilities; project versions remain undecided. |
| Other runtimes | Node and Podman not found on inspected noninteractive PATH | Does not establish global absence or prohibit a containerized stack. |
| Local root disk | 98 GB total, 15 GB available, 85% occupied | Account for images/build caches and logs during deployment planning. |
| Other local disk | `/mnt/media`: 364 GB total, 261 GB available | Existing local disk, not an approved fallback for project originals. |
| Services | Docker/containerd, Caddy 2.10.2, Tailscale 1.102.3, cloudflared, netdata, cron | Existing infrastructure, not proof of configured application authentication. |
| Existing databases | PostgreSQL 16 and 17 containers observed on mini-PC | Evidence of container operation only; no authorization to reuse existing databases. |
| Docker daemons | Both `docker.service` and `snap.docker.dockerd.service` appeared running | Determine intended daemon/socket before deployment; no service changes made. |

## NAS: mounts and direct host verification

The mini-PC has these existing read/write NFSv3 mounts:

- `192.168.68.67:/volume3/workspace` at `/mnt/nas/workspace`, about 443 GB free.
- `/volume1/media` and `/volume1/downloads` from the same NAS, mounted under
  `/mnt/nas/`, with reported shared filesystem capacity 17 TB, about 14 TB free.

Observed options include `hard`, `proto=tcp`, `sec=sys`, `timeo=600`, `retrans=2`,
and `local_lock=none`. Existing paths are inventory evidence, not the selected
application workspace/backup paths or independent proof of SSD/HDD assignment.
Sourav will provide the project paths later.

The storage contract must account for network-mounted I/O that may wait during
an outage. Mount options do not prove crash durability, flush guarantees,
database-file safety, or the application's error/timeout behavior.

### Follow-up after user supplied working aliases

Sourav confirmed the intended aliases are `ssh beng-mini-pc`, `ssh beng-nas`,
and `ssh beng-laptop`. All three subsequently authenticated using existing
configuration with strict host checking. The earlier NAS hostname/trust and
laptop authentication failures below were access snapshots, now superseded by
successful checks; no SSH configuration or trust files were changed by us.

NAS facts:

- Model DXP2800, Intel N100, 8 GB RAM: user supplied. Four logical CPUs and
  about 7.5 GiB visible RAM confirmed directly.
- `/etc/os-release`: Debian GNU/Linux 12 base, product series `nasync`, software
  version `1.19.1.0126`; kernel `6.18.15`, x86_64.
- User reports LAN address `192.168.68.67` and 1 Gbps link. Server address also
  matches existing mounts; link throughput was not benchmarked.
- Block-device hierarchy confirms `/volume3` is ext4 on the Samsung 970 EVO
  500 GB-class NVMe SSD, and `/volume1` is ext4 on the 20 TB-class WDC HDD.
  Project subdirectories are still to be supplied; existing mounts are not a
  final application/backup path choice.
- `postgresql.service` and `ugreen-psql.service` were present, with the latter
  running. Installed PostgreSQL package version reported `15.18-0+deb12u1`.
  These existing vendor services are not approved project databases; do not
  repurpose, connect to private application data, or modify them.
- No Docker/Podman command, standard Docker socket, or matching running service
  was found in the inspected locations. This does not prove no container app
  exists anywhere. A dedicated project database runtime remains a deployment
  decision/prerequisite; no software was installed.

Serial number, warranty data, and MAC address are unnecessary for this design
and were not copied into project notes.

## Laptop: direct follow-up verification

`ssh beng-laptop` succeeded on the follow-up without a wake request, despite
Sourav expecting it to be sleeping. We cannot infer what made it reachable or
whether its prior state was suspended. Earlier authentication failure is
historical, not current evidence of an access block.

- Ubuntu 26.04 LTS, kernel `7.0.0-29-generic`, x86_64.
- Intel Core i7-9750H, six cores/twelve threads, about 30.4 GiB visible RAM.
- `nvidia-smi` reported NVIDIA GeForce RTX 2070 with Max-Q Design, 8192 MiB,
  driver `595.84`.
- Python 3.14.4 and Ollama 0.33.0 observed; `ollama.service` and
  `beng-laptop-agent.service` active. Tailscale service also active.
- No inference, model loading/download, GPU workload, or wake/sleep action was
  invoked. Installed runtime/GPU identity does not establish candidate model
  fit, quality, processing throughput, or compatibility with future packages.

## Existing wake controller: observed/source-backed contract

The mini-PC runs a `laptop-control` container using host networking. Source and
documentation are under `/opt/beng-laptop-controller/source/`, including
`README.md`, `app.py`, `controller/agent_client.py`, and `shared/models.py`.
These are host paths, not files copied into this repository.

| Interface or behavior | Evidence and meaning |
| --- | --- |
| Listener | Port 8787 bound to loopback, LAN and Tailscale addresses; README's localhost/Serve intent differs from actual binding. |
| `GET /health`, `GET /api/status` | Source reads cached controller/agent state, without requesting wake. |
| Observed health | HTTP 200; device `beng-laptop`, state `Idle`, cached `online=true`, `sleep_ready=true`, idle policy 30 minutes. Point-in-time cache, not verified worker readiness. |
| `GET /api/capabilities` | HTTP 200; module names Host, Top processes, Power. Private snapshots/process lists were not retained. |
| `POST /api/wake` | Requires `X-CSRF-Token` matching a per-process random value embedded in controller HTML. Token values were not emitted or retained. A stable machine-client authentication contract was not established. |
| Wake acknowledgement | HTTP 202 with message `Wake signal sent`; source transmits Wake-on-LAN packets. No POST was invoked, so actual wake behavior is untested. |
| Controller/agent connection | Source/docs describe bearer-authenticated, certificate-verified TLS. Secret values were not inspected. |
| Sleep coordination | Models include expiring leases and `inhibit_while_active` managed workload behavior. Integration and renewal/recovery semantics remain unverified. |

A wake acknowledgement is not proof of laptop readiness, and controller cached
online state is not proof of application-worker or GPU readiness. The job and
operating-policy decisions must establish these separately. Sleep inhibition
may be needed while work runs without giving the application ownership of
forcing sleep afterward.

## Private access

Caddy has existing LAN-bound reverse proxy configuration. Tailscale is running,
but `tailscale serve status` returned `No serve config`. Application login,
VPN ACLs, TLS routing, and a supported machine-client path to the controller
are still design/deployment work, not supplied by installation alone.

## Programmatic wake feasibility

A direct local-client `GET http://beng-mini-pc:8787/` returned HTTP 200 with
page title `beng / control desk`. The live page contains a retrievable CSRF
value; the value was neither displayed nor persisted. Source confirms:

1. The page renders a process-generated token into its `const csrf` value.
2. The Wake button sends `POST /api/wake` with that value in `X-CSRF-Token`.
3. The handler compares the header, calls `send_wake()`, and returns HTTP 202
   with `Wake signal sent` (or an error when sending fails).

Therefore the existing route is programmatically callable without browser
click automation or a newly exposed endpoint. This is source/request-contract
verification, not an actual POST or end-to-end wake test. A future client must
fetch the current token rather than hard-code one; controller restarts change
it. A stable authenticated machine-client contract remains desirable to settle
in the operating-policy ticket; no controller changes are requested or made.

## Remaining design/deployment work

- Docker/PostgreSQL feasibility follow-up: [supported route and prerequisites](nas-docker-postgres-feasibility.md).
  Additional read-only checks found cgroup v2 CPU/memory controllers, overlay
  support, and user write access according to `test -w` (no writes). Docker,
  containerd and runc package records/binaries/units/socket were not found in
  checked locations; only app icons and old systemd helper metadata appeared.
  SSD mount options include `nobarrier`, requiring durability review. Vendor
  PostgreSQL listener observed on `127.0.0.1:5432`.
- Select an isolated NAS project-database runtime and permissions; existing
  vendor PostgreSQL services are not assumed reusable.
- Obtain exact project SSD workspace/HDD copy paths during implementation.
- Verify application acceptance/outage recovery, storage flush assumptions and
  consistent backup/restore using the selected deployment.
- Agree wake machine-client authentication, readiness and sleep-inhibition
  contracts; test real sleep-to-wake only when separately authorized.
- Evaluate model/runtime compatibility, memory fit and quality against the four
  representative account formats before making performance claims.

These belong to the existing storage, worker, operating-policy and local-model
choices; they do not require keeping the basic inventory task open.

## Evidence methods and limits

Successful mini-PC SSH checks used OS/CPU/RAM/filesystem queries, executable
versions, mount metadata, service metadata, bounded container names/status and
network/mount inspection, listener metadata, filtered proxy configuration,
targeted controller source/documentation reads, and documented cache-read GETs.
No environment dumps, secrets, private statements, tokens or raw process lists
were stored. Initial laptop authentication and NAS host-trust failures were superseded by
follow-up successes using user-confirmed aliases. They were never treated as
conclusions about host capability. Only safe GET requests and diagnostic
commands were used; all target-system changes and wake/sleep POSTs were omitted.
