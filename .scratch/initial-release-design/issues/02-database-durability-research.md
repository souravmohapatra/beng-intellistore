# Database durability and NAS storage evidence

Type: research
Label: wayfinder:research
Status: resolved
Blocked by: None
Parent: [Initial release technical design](../map.md)

## Question

What do first-party database/storage documents establish about a small NAS-hosted
database service versus an application opening a database on a network share?
Compare PostgreSQL and SQLite only as concrete candidates, without choosing
the product stack. Address exact money, transactional job/result publication,
file-plus-record intake recovery, and a simple consistent SSD-to-HDD backup.

## Resolution evidence

Cited findings in `research/database-durability.md`, with documented guarantees,
limitations, inference, and host-specific prerequisites clearly separated.
Explain why copying an active database directory may need coordination. Keep
the solution proportional to one user and the map's provisional scale.

## Answer

Resolved 2026-10-18: Primary-source comparison complete. See the linked research note for network-filesystem limitations, exact money options, transactional primitives, file/record recovery proposals, and consistent-copy methods. This resolves evidence gathering only; engine/placement, backup contracts, and host durability remain decisions in Authoritative storage, acceptance, and backup.

Evidence: [Research findings](../research/database-durability.md). No host checks, installs, implementation, commits, or pushes.
