# Container workflow facts

Read-only snapshot, 2026-10-18. No software or services were changed.

## Local development machine

The local Mac's shell did not find `docker`. Checked Docker Desktop, Homebrew,
`/usr/local`, and OrbStack CLI locations also lacked it. Compose and daemon
reachability could not be queried without a client. This is a bounded availability
check, not proof about every possible runtime location. A local container-based
developer workflow needs runtime setup or a separately chosen remote dev host.

## Mini-PC

Strict noninteractive SSH through `beng-mini-pc` succeeded. Both `docker.service`
and `snap.docker.dockerd.service` were active/running, and their distinct process
IDs each had command name `dockerd`. These are two live processes, not merely
stale service entries.

The current `/usr/bin/docker` default context uses `unix:///var/run/docker.sock`.
The server identified itself as `beng-mini-pc`, Docker 29.8.0, with data root
`/var/snap/docker/common/var-lib-docker`; Compose reported v5.0.1. `/var/run`
resolves to `/run`, and querying that equivalent socket reached the same server.
This is a current endpoint snapshot; earlier inventory's Docker version is not
used to infer either an upgrade or which other daemon it contacted.

Unprivileged socket metadata did not establish API ownership or health for the
other daemon. Choose an explicit daemon/context and isolated project before
deployment. Do not stop, consolidate, or migrate either existing daemon as part
of this design task.

## Evidence and limits

Checks used local command/path availability, SSH with strict host checking,
systemd active/MainPID/FragmentPath metadata, process command names, Docker
version/context/info fields, Compose version and Unix socket metadata. No
environment dumps, secrets or container configuration were retained. No launches,
installs, builds, pulls, container changes, sudo or wake requests were performed.
