# Authoritative storage, acceptance, and backup

Type: grilling
Label: wayfinder:grilling
Status: resolved
Blocked by: 01, 02
Parent: [Initial release technical design](../map.md)

## Question

Choose database engine/runtime placement and original-file access based on NAS
facts and durability evidence. Define accepted-upload consistency, incomplete
write/restart recovery, exact financial storage, atomic publication and retained
corrections, plus a simple consistent SSD-to-HDD copy and recovery check.
Preserve application-owned authoritative updates and no local fallback.

## Resolution evidence

Agreed persistence and backup contracts with concrete failure outcomes, and
clear distinction between required evidence and untested deployment claims.
Final NAS paths remain user-supplied implementation configuration.

User requires Docker deployment for the project database; do not select a
native NAS database simply because vendor PostgreSQL exists. NAS Docker/SSD
PostgreSQL feasibility is being checked read-only before a deployment decision.

## Feasibility follow-up

[NAS Docker/PostgreSQL feasibility](../research/nas-docker-postgres-feasibility.md)
combines live read-only checks and official UGREEN/image documentation. DXP2800
supports the vendor Docker app and Compose Projects; NAS has cgroup v2, overlay,
and a writable local SSD filesystem. Docker packages/binaries/units/socket were
not found in checked locations; installation and a dedicated Compose deployment
are prerequisites, not completed work. Native vendor PostgreSQL is untouched.

The SSD mount reports `nobarrier`; establish write-cache/flush/power-loss behavior
before claiming durable acceptance. Actual image start, persistent-volume
initialization, private connectivity and recovery remain untested. This research
supports feasibility, not final selection or permission to deploy.

## Power-loss decision now required

Sourav confirms no NAS UPS and no known power-loss protection. Automatic recovery
on restart is acceptable; persistent corruption/data loss requiring restoration
needs explicit discussion, not silent acceptance.

Read-only checks show both NAS SSD and HDD kernel write-cache attributes report
`write back`; SSD ext4 still reports `nobarrier`. This is not equivalent to
PostgreSQL `fsync=off` and does not prove inevitable corruption, but storage
ordering/flush guarantees are not established. Mini-PC local root ext4 shows
`rw,relatime` without `nobarrier`; full mini-PC power-loss safety is unverified.

Options to discuss: vendor-supported NAS barrier/cache correction with retained
NAS database placement, or a Docker database on mini-PC local storage with
consistent NAS backups. The latter changes the HLD's all-authoritative-state-on-
NAS rule and requires user agreement. Merely moving the PostgreSQL process while
keeping its live data on NAS does not remove the storage concern. NAS originals
and same-NAS HDD copies retain NAS-level risks whichever database host is chosen.

Evidence: [Power loss and database placement](../research/power-loss-and-database-placement.md)
distinguishes normal WAL crash recovery from storage failures that can require
restore. Lack of UPS alone is not disqualifying, and write-back cache alone is
not proof of unsafety; honored flushes and journal ordering matter. Do not equate
`nobarrier` with PostgreSQL `fsync=off`, or treat container restart as data repair.

## Evidence to consult

[Host inventory](../research/host-storage-wake-inventory.md) identifies existing
NFSv3 hard mounts. Account for waiting/outage behavior rather than assuming
every storage outage immediately raises an application error. Existing paths
are not the approved project paths, verified SSD/HDD mapping, or flush guarantees.

## Placement direction from Sourav

All authoritative state moves to mini-PC local storage; compute remains on
mini-PC/laptop. NAS is for file backups/archive, not a live database or project
compute. Sourav proposes approximately one year of active database history and
older data backed up to NAS. Exact retention/archive meaning, original-file
placement, backup loss window and restore behavior remain to be agreed. Do not
delete/move data or describe this as guaranteed power-loss safety.

### Confirmed retention and recovery direction

Sourav accepted Q32-Q34: keep imported historical transaction records locally,
use twelve months as the default dashboard window, and do not automatically
remove older records. Active originals remain local and are included with
records/corrections/provenance in nightly consistent NAS backups. A mini-PC disk
failure can lose changes since the last successful backup; visible failure and
last-success status are required. NAS downtime delays backups, not normal use;
backup failure never permits local deletion. Old-source archival is deferred.

HLD v0.3 now reconciles roles, logical diagram, flows, requirements and acceptance
to this direction. Engine selection, backup generations and exact recovery
mechanics remain open; this ticket is still claimed.

## Answer

Resolved after Sourav accepted Q32-Q36 and the placement change. The latest
decision supersedes the earlier NAS feasibility discussion above. See
[ADR: local authority and NAS backups](../../../docs/adr/0001-local-authority-and-nas-backups.md)
and HLD v0.3.

- Dedicated PostgreSQL Docker container on mini-PC local persistent storage,
  separate from existing application databases. No live database files on NAS.
- Active originals and all imported transaction history remain local. The
  twelve-month dashboard default is not retention; old-source archival is deferred.
- Accept uploads only after the immutable original and tracking record are
  preserved locally. Failure must not produce a successful acceptance. A retry
  or restart cannot silently create duplicate financial effects; incomplete
  processing leaves the original and last committed view available.
- Application-owned publication is transactional and preserves user corrections.
  Use exact financial values; schema precision and source normalization depend
  on supplied formats. Detailed job/version/idempotency mechanics belong to
  Worker jobs, retries, and result publication and the implementation spec.
- Nightly backups form a consistent recovery set containing database state,
  originals, corrections and provenance. Keep the seven most recent successful
  generations; retire the oldest only after a new generation completes. An
  interrupted copy is not a successful backup and cannot replace the last good one.
- Show backup failures/last success. NAS outage does not stop normal use or
  authorize deleting local data. Sourav accepts loss of changes since the last
  successful backup if mini-PC data is lost; failed backups can extend the window.
- Release acceptance includes restoring to an isolated location and checking
  records, source relationships and corrections. No restore or storage test has
  yet run; local disk safety/headroom, paths, permissions, image version and
  exact backup/restore commands remain implementation/deployment prerequisites.

Backup scheduling, failure reporting and operating limits are refined in
Private access, batching, and operating policy. These are explicit downstream
contracts, not permission to start implementation before the four sample formats.
No installation, migration, deletion, target change, commit or push performed.
