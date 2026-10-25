# Backup and isolated restore runbook (mini-PC + NAS)

The logic runs in the project `backup`/`restore` containers; systemd only invokes
Compose. Nothing here is deployed yet.

## Destination paths and permissions

Set these in `/etc/beng-intellistore/runtime.env` (root-owned, outside the checkout):

```
INTELLISTORE_BACKUP_DIR=/mnt/nas/<approved-project-path>/intellistore
INTELLISTORE_RESTORE_DIR=/var/lib/beng-intellistore/restore-check
INTELLISTORE_BACKUP_GENERATIONS=7
```

- The NAS directory must be writable by the container user (default uid/gid
  1000). Create it beforehand and check with `touch` as that user; the container
  does not run privileged.
- Status is written to `${INTELLISTORE_HOST_DATA_DIR}/status/backup.json`, inside
  the existing local data directory. The app reads it; no extra mount or path is
  needed. The backup container creates the `status` subdirectory.
- Headroom: seven generations roughly equal seven copies of the database dump plus
  seven copies of the originals (originals also remain on local storage). Confirm
  free space with `df -h` before the first run.
- The backup container reads originals read-only; it never deletes local data.

## Install the timer

```bash
sudo install -m 0644 deploy/systemd/intellistore-backup.service \
  deploy/systemd/intellistore-backup.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now intellistore-backup.timer
systemctl list-timers intellistore-backup.timer
```

Runs daily at 03:00 Europe/London with `Persistent=true`, so a missed slot runs
after the host returns.

## First controlled generation

```bash
sudo systemctl start intellistore-backup.service
sudo journalctl -u intellistore-backup.service -n 40 --no-pager
ls -1 "$INTELLISTORE_BACKUP_DIR"
cat "$INTELLISTORE_HOST_DATA_DIR/status/backup.json"
```

Only a directory containing `COMPLETE` counts. Incomplete runs remain as
`.incomplete-*` with a `FAILED` marker and appear as `failed` in the Status page.
Seven complete generations are kept; an older one is removed only after a new
complete generation is published.

## Isolated restore verification

Never restore over the live database. Choose a new database name and an empty
directory, for example:

```bash
sudo systemctl stop intellistore-app.service   # optional; prevents live writes
sudo docker compose --env-file /dev/null \
  --project-directory "$INTELLISTORE_COMPOSE_DIR" \
  -f "$INTELLISTORE_COMPOSE_DIR/compose.production.yaml" \
  -f "$INTELLISTORE_COMPOSE_DIR/compose.recovery.yaml" \
  run --rm restore \
  --generation /backup/generation-<timestamp> \
  --database intellistore_restore_check \
  --originals-target /restore/intellistore_restore_check
```

The restore container verifies every manifest hash before writing, creates the
named database, restores the dump, and copies originals. Then verify through the
public application surface (do not inspect or edit the live database):

1. Point a temporary app instance at `intellistore_restore_check` and the restored
   originals directory; run a read-only dashboard/search/review check.
2. Open an original and confirm its bytes and source links.
3. Confirm a known correction history is present and its reporting effect applies.
4. Record counts, commands, timestamps and any limit. Drop the temporary database
   and directory only after evidence is captured.

## Failure exercise

With the NAS mount unavailable (or the destination made read-only), start the
service:

```bash
sudo systemctl start intellistore-backup.service
cat "$INTELLISTORE_HOST_DATA_DIR/status/backup.json"   # failed + message
```

Expect: non-zero service result, visible failure, no local data deleted, no good
generation retired, and the app still usable. Reconnect and rerun to recover.

## Rollback / disable

```bash
sudo systemctl disable --now intellistore-backup.timer
```

Backups are additive; disabling them never changes local data.
