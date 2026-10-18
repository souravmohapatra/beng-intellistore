# Database durability and NAS storage evidence

Investigated 2026-10-18. Primary-source research for
[Database durability and NAS storage evidence](../issues/02-database-durability-research.md).
This compares PostgreSQL and SQLite without selecting the stack. Proposals below
are inferences, not approved architecture or verified deployment facts.

## Placement is the decisive distinction

SQLite warns that remote database files depend on network-filesystem locking and
synchronization behavior; an apparently successful test does not establish
reliability. Its guidance favors putting the network boundary at a database/API
interface, with the engine on the machine holding the file. SQLite WAL explicitly
does not work over network filesystems. Rollback mode does not turn arbitrary
network shares into a guaranteed-safe deployment. [SQLite network guidance](https://www.sqlite.org/useovernet.html),
[WAL limitations](https://www.sqlite.org/wal.html)

PostgreSQL can use NFS data directories, but requires `hard` mounts; these may
hang indefinitely during network failure. Its docs recommend synchronous NFS
server exports so acknowledged flushes reach permanent storage. This is not a
blanket guarantee for an unidentified NAS or SMB share.
[PostgreSQL filesystem requirements](https://www.postgresql.org/docs/18/creating-cluster.html#CREATING-CLUSTER-NFS)

**Project implications (inference):** PostgreSQL running on the NAS with a
NAS-local SSD data directory naturally separates mini-PC SQL traffic from database
file I/O. SQLite on a mini-PC opening a NAS share conflicts with the documented
cautions. SQLite with all database access executed locally on the NAS remains a
candidate, but requires a NAS-side application/API boundary; the deployment cost
must be considered against the agreed mini-PC ownership. No extra service is
approved by this note.

## Exact financial values

PostgreSQL `numeric`/`decimal` supports exact decimal arithmetic; fixed declared
scale rounds excess fractional digits. Integer types are also exact within their
range. SQLite INTEGER is exact signed 64-bit, whereas REAL is approximate.
SQLite `DECIMAL(...)` declarations do not provide PostgreSQL-style decimal
semantics: NUMERIC affinity can convert values to INTEGER or REAL.
[PostgreSQL numeric types](https://www.postgresql.org/docs/18/datatype-numeric.html),
[SQLite number accuracy](https://www.sqlite.org/floatingpoint.html),
[SQLite affinity](https://www.sqlite.org/datatype3.html)

**Design options (inference):** either engine can hold validated integer minor
units plus currency and an agreed scale. PostgreSQL also offers native exact
decimal storage. Do not assume two decimal places before inspecting supported
currencies and samples. Reject unsupported precision rather than silently round;
preserve source text. API and application arithmetic must also avoid binary
floating-point conversion. Representation remains an open decision.

## Transactions, jobs, and publication

PostgreSQL transactions make grouped changes visible together and roll back
uncommitted work. Unique constraints can prevent repeated identities. Its
`FOR UPDATE ... SKIP LOCKED` is documented for queue-like consumers, although
skipped rows give an inconsistent general query view. SQLite supports multiple
readers but one simultaneous writer; `BEGIN IMMEDIATE` obtains a write transaction
upfront or fails with `SQLITE_BUSY`.
[PostgreSQL transactions](https://www.postgresql.org/docs/18/tutorial-transactions.html),
[constraints](https://www.postgresql.org/docs/18/ddl-constraints.html),
[queue locking](https://www.postgresql.org/docs/18/sql-select.html#SQL-FOR-UPDATE-SHARE),
[SQLite transactions](https://www.sqlite.org/lang_transaction.html)

**Application implications (inference):** either offers primitives for durable
job rows and atomic per-upload publication; neither supplies the complete worker
protocol. Claim briefly, commit, then process outside the transaction. Persist an
attempt identity and expiry; validate that identity and correction/version state
when publishing results in a new transaction. Expiry permits retry, not proof that
the previous worker stopped. Reject stale submissions and make repeat publication
idempotent. One worker does not require parallel queue consumers or `SKIP LOCKED`.

## Original plus tracking record

Database transactions above cover database state, not a separately written
original file. SQLite's atomic-commit account specifically relies on filesystem
locking and flush assumptions. Neither cited transaction interface promises an
atomic commit spanning an arbitrary NAS file and a database record.
[SQLite atomic commit assumptions](https://www.sqlite.org/atomiccommit.html),
[PostgreSQL transaction scope](https://www.postgresql.org/docs/18/tutorial-transactions.html)

**Recovery proposal (inference):** durably finalize an immutable original before
committing its accepted tracking record and job; acknowledge only afterward.
Persist a retry identity. A crash can leave an orphan file, so reconciliation must
identify it without deleting accepted sources. A lost success response must allow
the same submission to be looked up or retried safely. Finalization/flush behavior
needs protocol-specific verification and crash tests. Database success alone does
not prove original durability.

## Simple consistent SSD-to-HDD copy

An ordinary copy of a running PostgreSQL data directory is not a usable backup:
the server must stop unless a documented coordinated snapshot/base-backup method
is used. `pg_dump` produces a consistent database export while clients run; it
does not include cluster-global roles. The docs caution that dumps are not the
general answer for every production backup requirement.
[Filesystem backup](https://www.postgresql.org/docs/18/backup-file.html),
[pg_dump](https://www.postgresql.org/docs/18/app-pgdump.html)

SQLite's Backup API produces a consistent snapshot. `VACUUM INTO` is another
supported live-copy mechanism; interrupted output may be corrupt. Copying only a
live WAL database's main file can omit committed data still in its WAL.
[Backup API](https://www.sqlite.org/backup.html),
[VACUUM INTO](https://www.sqlite.org/lang_vacuum.html),
[WAL operation](https://www.sqlite.org/wal.html)

**Proportional proposal (inference):** briefly pause authoritative mutations and
drain in-flight intake/publication/corrections; export the database with its
supported tool and copy originals into a new HDD backup generation. Publish a
completion marker only after all steps succeed; retain the previous successful
generation. Include reconstructible configuration and role setup without exposing
secrets. Resume writes and check restoration into an isolated location, including
source references and corrections. Cadence and acceptable pause remain decisions.

## Evidence limits

No host was contacted. NAS OS, mounts, container bind paths, write-cache/power-loss
behavior, database versions, permissions, capacity, restore procedure, and the
two-second target are unverified. The user reports database-service capability;
that is not deployed-service evidence. A second disk in the same NAS protects
neither against complete NAS loss nor every administrative mistake.
