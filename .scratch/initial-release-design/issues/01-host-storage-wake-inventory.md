# Host, storage, and wake inventory

Type: task
Label: wayfinder:task
Status: resolved
Blocked by: None
Parent: [Initial release technical design](../map.md)

## Question

What existing host, storage, private-network/authentication, and wake facilities
can this design actually use? Establish mini-PC/NAS/laptop OS and service
runtimes, NAS database hosting/storage access, SSD/HDD roles, available resources,
and the existing wake/readiness contract. Inspect known facilities read-only;
do not wake hosts, install software, change configuration, or deploy services.

Start with [local clues](../research/local-infrastructure-clues.md). Seek missing
connection/documentation context only when it cannot be found safely. Exact NAS
paths can be supplied during implementation as agreed; do not invent them.

## Resolution evidence

A redacted inventory identifying observed facts, user reports, unknowns, and
whether each unknown gates design or only deployment. No secrets or private
statements in notes. A failed connection is not proof of unsupported capability.

## Comments

2026-10-18: Mini-PC inspection succeeded; see the
[inventory findings](../research/host-storage-wake-inventory.md). Existing NAS
mounts and controller source/contracts were inspected without wake or changes.
Laptop SSH rejected authentication. NAS direct SSH stopped at missing trusted
host key; strict verification was retained. Asked Sourav for NAS OS/service
hosting and existing access context, with deferral of direct checks as an option.
Task remains claimed while that context is pending; no architecture choice is
being inferred from inaccessible hosts.

## Answer

Resolved after Sourav supplied intended aliases and NAS details. All three
existing aliases authenticated on follow-up: `beng-mini-pc`, `beng-nas`, and
`beng-laptop`. The [inventory](../research/host-storage-wake-inventory.md)
records verified OS/runtime/hardware, NAS SSD/HDD mapping, existing mounts and
services, and the controller request contract. Earlier access limitations are
superseded, with their historical scope retained.

NAS-hosted database deployment remains a choice: existing vendor PostgreSQL is
not a project database, and no Docker command/socket was found in the inspected
locations. GPU and Ollama are verified on the laptop, but model fit is untested.

The existing wake page is directly reachable. Its CSRF token is retrievable
and its source-backed `POST /api/wake` contract can be used programmatically;
no new endpoint is necessary simply to issue that request. No POST, wake, sleep,
install, service change, storage write, or other target-system mutation was
performed. Real wake/readiness and deployment behavior remain later checks.

This resolves the inventory, not the storage/stack/model choices. It unblocks
the application/deployment and authoritative-storage decision discussions.
