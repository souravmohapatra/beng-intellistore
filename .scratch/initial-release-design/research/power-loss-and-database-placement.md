# Power loss and database placement

Investigated 2026-10-18 using official documentation and read-only observations
supplied by the parent investigator. No target connections or changes by this
research task. This records risk and options, not a storage decision.

## Evidence and consequence

The user reports no UPS. NAS `/volume3` is ext4 with `nobarrier`; NAS NVMe and HDD
queue files report `write back`. The mini-PC root filesystem is local SSD/ext4
with `rw,relatime`, without a reported `nobarrier` option. These observations do
not establish either host's complete flush path, power-loss protection, or actual
crash behavior. A write-back setting alone does not establish unsafe storage:
honored flushes and ordering matter. No drive-specific protection claim is made.

**The possible consequence is more serious than a container restart.** PostgreSQL
normally recovers from an abrupt stop by replaying its write-ahead log (WAL), but
that depends on WAL reaching permanent storage before the corresponding data
changes. PostgreSQL explains that volatile caches and unreliable flush behavior
can undermine this protection. If the storage guarantees fail, outcomes can
include lost acknowledged changes or damaged database files; restoration may be
needed. Corruption is possible, not established or inevitable on this NAS.
[PostgreSQL WAL](https://www.postgresql.org/docs/current/wal-intro.html),
[storage reliability](https://www.postgresql.org/docs/current/wal-reliability.html).

## What `nobarrier` means

Linux documents this option as disabling ext4 journal write barriers. Those
barriers enforce journal-commit ordering and make volatile write caches safe to
use; the documented safe performance case for disabling them is battery-backed
storage. This makes the observed configuration a concrete reason to investigate
before promising durable acceptance.
[Linux ext4 options](https://www.kernel.org/doc/html/latest/admin-guide/ext4.html).

**It does not mean PostgreSQL `fsync` is disabled**, nor prove that every flush
request is ignored. They are different settings at different layers. PostgreSQL
`fsync`, `full_page_writes`, and normal synchronous commit should remain enabled;
full-page WAL images protect against partially written database pages, while
`fsync` requests persistent storage. These cannot repair arbitrary filesystem or
hardware failures that violate their assumptions.
[PostgreSQL WAL configuration](https://www.postgresql.org/docs/current/runtime-config-wal.html).

Lack of a UPS by itself does not mean databases cannot run safely. Proper
filesystem ordering and correctly honored flushes are fundamental; a UPS adds
protection against utility outages but does not replace those requirements.
That distinction follows from the storage reliability mechanisms above, rather
than a verified property of either machine.

## Docker and placement

Docker volumes write to host storage and outlive individual containers. Restarting
or replacing a container reuses its persistent files, including any damage. Docker
therefore does not create this power-loss problem and cannot solve it.
[Docker volumes](https://docs.docker.com/engine/storage/volumes/).

Moving only the database process to the mini-PC while keeping its live data files
on the NAS leaves the suspect storage path involved. PostgreSQL supports NFS only
with suitable durability behavior, including a synchronous export; an extra host
is not a durability fix.
[PostgreSQL network filesystems](https://www.postgresql.org/docs/current/creating-cluster.html).

A PostgreSQL container using **local mini-PC SSD storage**, with supported backups
copied to NAS, is a conditional alternative. It requires checking the mini-PC
storage path, changes the agreed all-authoritative-state-on-NAS architecture, and
does not protect originals still stored on NAS. Raw source files can also suffer
loss or filesystem damage; “files only” does not eliminate the underlying issue.

## Recommendation and remaining checks

Keep Docker. Pause the NAS database choice while checking the vendor-supported
route to enabled barriers and cache-flush behavior. Do not remount a live vendor
volume casually. If that cannot be established, evaluate local mini-PC database
storage with Sourav rather than assuming NAS restart recovery is sufficient.

Retain simple SSD-to-HDD backups, but copy a supported database backup, or stop
PostgreSQL cleanly before copying its entire cluster. Test restoration; a live
ordinary file copy is not a consistent PostgreSQL backup. Recent changes since
the last backup remain exposed, and same-NAS copies share failure risks.
[PostgreSQL filesystem backup](https://www.postgresql.org/docs/current/backup-file.html).

No mount changes, installations, container starts, destructive power-cut tests,
or Git operations were performed. Exact probability of damage remains unknown.
