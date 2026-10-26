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

`DOCKER_HOST` is also read from that file by the units (see
`deploy/setup-common.sh`); it must be an explicit local Unix endpoint such as
`unix:///var/run/docker.sock`. Never print or paste the file: it holds
`POSTGRES_PASSWORD` and `DJANGO_SECRET_KEY`.

- `INTELLISTORE_BACKUP_DIR` and the existing data directory are what the
  `backup` service needs. `INTELLISTORE_RESTORE_DIR` is restore-only; the layered
  Compose file no longer requires it to run `backup`.

- The NAS directory must be writable by the container user (default uid/gid
  1000). Create it beforehand and check with `touch` as that user; the container
  does not run privileged.
- Status is written to `${INTELLISTORE_HOST_DATA_DIR}/status/backup.json`, inside
  the existing local data directory. The app reads it; no extra mount or path is
  needed. Pre-create it with the application uid/gid; Docker-created bind
  directories would otherwise be root-owned and unwritable by the backup user.
  The current mini-PC setup script also creates this directory.
  
  ```bash
  sudo bash -c '
    set -a; . /etc/beng-intellistore/runtime.env; set +a
    install -d -m 0700 -o "${APP_UID:-1000}" -g "${APP_GID:-1000}" \
      "$INTELLISTORE_HOST_DATA_DIR/status"
    install -d -m 0700 -o "${APP_UID:-1000}" -g "${APP_GID:-1000}" \
      "$INTELLISTORE_RESTORE_DIR"
  '
  ```

  Create the approved NAS destination on its mounted filesystem separately,
  with the same numeric uid/gid. Do not create it over a missing NAS mount.
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

Only a directory containing `COMPLETE` counts. Generations are named
`generation-<UTC timestamp>-<run suffix>`; retention orders them by the
publication sequence recorded in `COMPLETE`, so the newest run is always the one
kept even when two runs share a second and their random suffixes sort the other
way. Incomplete runs remain as `.incomplete-*` with a `FAILED` marker and appear
as `failed` in the Status page. Seven complete generations are kept; an older one
is removed only after a new complete generation is published.

Runs are serialised through a `.backup.lock` directory on the destination, so a
manual `run backup` does not overlap the nightly one (the second invocation exits
non-zero and leaves the running attempt's status untouched). The run removes its
own lock on normal exit and on termination signals. If the host or container was
killed (`SIGKILL`) or lost power the lock can remain: first confirm no backup is
running (`systemctl status intellistore-backup.service`, `docker ps`), then remove
only the `.backup.lock` directory. Never delete generation directories or
originals to clear a lock.

## Isolated restore verification

Never restore over the live database. Choose a new database name and an empty
directory, for example `intellistore_restore_check` and
`/restore/intellistore_restore_check`. Load the root-owned runtime environment and
pass the explicit Docker endpoint, as the systemd unit does — do not print the
file (it holds secrets):

```bash
sudo bash -c '
  set -a; . /etc/beng-intellistore/runtime.env; set +a
  exec docker --host="$DOCKER_HOST" compose --env-file /dev/null \
    --project-directory "$INTELLISTORE_COMPOSE_DIR" \
    -f "$INTELLISTORE_COMPOSE_DIR/compose.production.yaml" \
    -f "$INTELLISTORE_COMPOSE_DIR/compose.recovery.yaml" \
    run --rm restore \
    --generation /backup/generation-<timestamp>-<suffix> \
    --database intellistore_restore_check \
    --originals-target /restore/intellistore_restore_check
'
```

Replace `intellistore_restore_check` with your chosen name. The script rejects a
database name that is not a plain identifier (so a quote or injection cannot reach
`CREATE DATABASE`), refuses the live database and a non-empty or symlinked target,
and rejects symlinked generation/manifest/dump/original paths before writing.

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

A present but unwritable or full destination is reported as `failed`. Note a
limitation: if a bind-mount source is absent (for example the NAS path does not
exist, or `INTELLISTORE_HOST_DATA_DIR` is wrong), Docker refuses to start the
container before the script runs, so no `failed` record is written and the Status
page keeps showing the previous attempt. In that case check the service and the
mounts, not only the status file:

```bash
sudo systemctl start intellistore-backup.service
systemctl status intellistore-backup.service --no-pager   # or: journalctl -u ...
cat "$INTELLISTORE_HOST_DATA_DIR/status/backup.json"      # failed, or the previous attempt
```

To exercise the script-level failure path, make the destination exist but
read-only instead of removing it: then the container starts, the script writes
`failed`, and the previous good generation is preserved.

Expect: non-zero service result, visible failure, no local data deleted, no good
generation retired, and the app still usable. Reconnect and rerun to recover.

## Rollback / disable

```bash
sudo systemctl disable --now intellistore-backup.timer
```

Backups are additive; disabling them never changes local data.
