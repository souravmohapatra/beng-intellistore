# Keep authoritative state on the mini-PC and recovery copies on NAS

Use a dedicated PostgreSQL Docker container with persistent data on mini-PC
local storage, alongside local active originals; the laptop performs processing
and the NAS stores backup files without project compute or a live database.
This replaces NAS-authoritative storage after observing disabled ext4 journal
barriers on the NAS and confirming no UPS; it removes that storage path from
live database operation without claiming that mini-PC power-loss safety is proven.
PostgreSQL was chosen over SQLite following discussion of exact financial values
and transactional publication/job behavior.

## Consequences

- Retain imported transaction history locally; twelve months is the dashboard
  default, not an automatic deletion rule. Old-source archival is deferred.
- Keep seven successful nightly consistent backups of originals and database
  records/corrections on NAS. Retire the oldest only after a new backup completes.
- NAS failure delays backup and is visible; normal application use continues.
  Mini-PC data loss may lose changes since the last successful backup.
- Validate local storage, backup consistency, restoration, and capacity before
  release. Docker restart is not a remedy for arbitrary persistent corruption.
