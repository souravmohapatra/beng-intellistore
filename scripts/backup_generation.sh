#!/bin/sh
# Create one consistent recovery generation on the mounted backup destination.
# Runs inside the project `backup` container (postgres:17 client image).
#
# Consistency: pg_dump takes a point-in-time snapshot of the database. Accepted
# originals are immutable and written before their database records exist, so
# copying them after the snapshot yields a superset: every referenced original is
# present. A generation counts only after a manifest hashes every payload, a
# COMPLETE marker is written, and the temporary directory is atomically renamed.
# The published name carries a per-run unique suffix so two runs can never rename
# over or nest into each other.
#
# One run at a time: a lock directory on the destination serialises runs (systemd
# already serialises its own, the lock protects manual runs too). Retention keeps
# the newest generations by their recorded publication sequence, not by their
# random name, so the just-published generation is never the one removed. The lock
# is fail-closed (never stolen by elapsed time) and is released on normal exit and
# on termination signals; after a SIGKILL or power loss an operator must confirm no
# run is active and remove only the lock.
#
# Failure reporting is installed before touching the destination, so an
# unavailable/full destination is visible. The previous successful generation is
# recorded separately and is never erased by a later failure.
set -eu

: "${BACKUP_DIR:?Set BACKUP_DIR (mounted destination)}"
: "${ORIGINALS_DIR:?Set ORIGINALS_DIR (mounted read-only originals)}"
: "${PGHOST:?Set PGHOST}"
: "${PGUSER:?Set PGUSER}"
: "${PGDATABASE:?Set PGDATABASE}"
: "${STATUS_FILE:?Set STATUS_FILE}"
: "${SUCCESS_FILE:?Set SUCCESS_FILE}"

KEEP_GENERATIONS="${KEEP_GENERATIONS:-7}"

case "$KEEP_GENERATIONS" in
  ''|*[!0-9]*) echo "KEEP_GENERATIONS must be a whole number" >&2; exit 2 ;;
esac
if [ "$KEEP_GENERATIONS" -lt 1 ]; then
  echo "KEEP_GENERATIONS must be at least 1" >&2
  exit 2
fi

timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
complete=0
started=0
tmp=""
work=""
lock_dir=""
lock_held=0

json_escape() {
  # Escape backslashes and double quotes and flatten control characters so a
  # path or message can never break the status JSON.
  printf '%s' "$1" | sed -e 's/\\/\\\\/g' -e 's/"/\\"/g' -e 's/[[:cntrl:]]/ /g'
}

write_json() {
  # $1=file $2=status $3=generation $4=message. Atomic, no financial contents.
  target="$1"
  dir="$(dirname "$target")"
  mkdir -p "$dir" || return 1
  scratch="$(mktemp "$target.XXXXXX")" || return 1
  printf '{"status":"%s","finished_at":"%s","generation":"%s","message":"%s"}\n' \
    "$(json_escape "$2")" "$(json_escape "$timestamp")" \
    "$(json_escape "$3")" "$(json_escape "$4")" > "$scratch" || return 1
  mv "$scratch" "$target" || return 1
}

write_failed() {
  write_json "$STATUS_FILE" failed "" "${1:-backup did not complete}" 2>/dev/null ||
    echo "could not write backup status" >&2
}

release_lock() {
  if [ "$lock_held" -eq 1 ] && [ -n "$lock_dir" ]; then
    rm -rf "$lock_dir" 2>/dev/null || true
    lock_held=0
  fi
}

cleanup() {
  if [ -n "$work" ]; then
    rm -rf "$work"
  fi
  if [ "$started" -eq 1 ] && [ "$complete" -ne 1 ]; then
    if [ -n "$tmp" ] && [ -d "$tmp" ]; then
      printf 'backup did not complete; see service logs\n' > "$tmp/FAILED" 2>/dev/null || true
      echo "backup failed; incomplete generation kept at $tmp" >&2
    fi
    write_failed "backup did not complete"
  fi
  release_lock
}
trap cleanup EXIT
trap 'exit 1' HUP INT TERM

# Take the destination lock before any work. If it already exists we fail closed
# rather than run two backups at once. Never steal a lock by elapsed time: a
# legitimate dump/copy can run for more than an hour. The owner is released by the
# exit trap on normal exit and on termination signals; after a SIGKILL or power
# loss an operator must confirm no backup is running and remove only the lock.
acquire_lock() {
  if mkdir "$lock_dir" 2>/dev/null; then
    lock_held=1
    printf '%s\n' "$$" > "$lock_dir/owner" 2>/dev/null || true
    return 0
  fi
  return 1
}

# Recorded publication sequence of a generation (0 when absent/legacy). Retention
# orders by this rather than by the random directory name.
generation_seq() {
  seq_value=0
  if [ -f "$1/COMPLETE" ] && [ ! -L "$1/COMPLETE" ]; then
    while IFS= read -r complete_line; do
      case "$complete_line" in
        seq=*) seq_value="${complete_line#seq=}" ;;
      esac
    done < "$1/COMPLETE"
  fi
  case "$seq_value" in
    ''|*[!0-9]*) seq_value=0 ;;
  esac
  printf '%s\n' "$seq_value"
}

started=1
mkdir -p "$BACKUP_DIR"
lock_dir="$BACKUP_DIR/.backup.lock"
if ! acquire_lock; then
  if [ -e "$lock_dir" ] || [ -L "$lock_dir" ]; then
    # Do not overwrite the status owned by a currently running backup.
    started=0
    echo "another backup is already running; refusing to start (lock: $lock_dir)" >&2
    echo "if no backup is running (a previous run was killed), remove only $lock_dir and retry" >&2
  else
    echo "backup destination cannot create its lock: $lock_dir" >&2
  fi
  exit 1
fi

work="$(mktemp -d)"

# Refuse a wrong/unavailable originals mount instead of silently publishing an
# unrecoverable backup. A fresh install may have no originals directory yet,
# but its parent data mount must exist. A symlink or special file would be
# silently omitted by the payload enumeration, so refuse rather than publish a
# generation that does not cover every original.
orig_parent="$(dirname "$ORIGINALS_DIR")"
if [ ! -d "$orig_parent" ]; then
  echo "originals parent directory is missing: $orig_parent" >&2
  exit 1
fi
if [ -L "$ORIGINALS_DIR" ]; then
  echo "originals path must not be a symbolic link: $ORIGINALS_DIR" >&2
  exit 1
fi
if [ -e "$ORIGINALS_DIR" ]; then
  if [ ! -d "$ORIGINALS_DIR" ] || [ ! -r "$ORIGINALS_DIR" ] || [ ! -x "$ORIGINALS_DIR" ]; then
    echo "originals directory is not readable: $ORIGINALS_DIR" >&2
    exit 1
  fi
  nonregular="$work/originals.nonregular"
  : > "$nonregular"
  if ! find "$ORIGINALS_DIR" ! -type f ! -type d -print > "$nonregular"; then
    echo "could not enumerate originals: $ORIGINALS_DIR" >&2
    exit 1
  fi
  if [ -s "$nonregular" ]; then
    echo "originals contain a symlink or special file; refusing to omit it" >&2
    exit 1
  fi
fi

tmp="$(mktemp -d "$BACKUP_DIR/.incomplete-${timestamp}-XXXXXX")"

sha256_of() {
  if command -v sha256sum >/dev/null 2>&1; then
    out="$(sha256sum "$1")" || return 1
  else
    out="$(shasum -a 256 "$1")" || return 1
  fi
  printf '%s\n' "${out%% *}"
}

pg_dump -h "$PGHOST" -U "$PGUSER" -d "$PGDATABASE" --format=custom \
  > "$tmp/database.dump"

if [ ! -s "$tmp/database.dump" ]; then
  echo "database dump was empty" >&2
  exit 1
fi

mkdir -p "$tmp/originals"
if [ -d "$ORIGINALS_DIR" ]; then
  cp -a "$ORIGINALS_DIR/." "$tmp/originals/" ||
    { echo "could not copy originals into the generation" >&2; exit 1; }
fi

# Re-check the staged payload: a symlink or special file would be skipped by the
# manifest and published as a backup that silently omits it.
staged_nonregular="$work/staged.nonregular"
: > "$staged_nonregular"
if ! find "$tmp" ! -type f ! -type d -print > "$staged_nonregular"; then
  echo "could not inspect the staged generation" >&2
  exit 1
fi
if [ -s "$staged_nonregular" ]; then
  echo "staged generation contains a symlink or special file; refusing to publish" >&2
  exit 1
fi

# Build the manifest without masking failures through pipelines. Each payload is
# read and hashed individually, and the result is validated before publication.
list="$work/filelist"
sorted="$work/files.sorted"
: > "$list"
if ! find "$tmp" -type f ! -name MANIFEST.sha256 ! -name COMPLETE ! -name FAILED -print \
  > "$list"; then
  echo "could not enumerate backup payloads" >&2
  exit 1
fi
if [ ! -s "$list" ]; then
  echo "no backup payloads were found" >&2
  exit 1
fi
: > "$sorted"
if ! LC_ALL=C sort "$list" > "$sorted"; then
  echo "could not order backup payloads" >&2
  exit 1
fi
: > "$tmp/MANIFEST.sha256"
while IFS= read -r file; do
  [ -r "$file" ] || { echo "payload is unreadable: ${file#"$tmp/"}" >&2; exit 1; }
  hash="$(sha256_of "$file")" || { echo "hashing failed for a payload" >&2; exit 1; }
  case "$hash" in
    ''|*[!0-9a-f]*) echo "hashing failed for a payload" >&2; exit 1 ;;
  esac
  if [ "${#hash}" -ne 64 ]; then
    echo "invalid hash length for a payload" >&2
    exit 1
  fi
  size="$(wc -c < "$file")" || exit 1
  size=$((size + 0))
  printf '%s  %s  %s\n' "$hash" "$size" "${file#"$tmp/"}" >> "$tmp/MANIFEST.sha256"
done < "$sorted"

[ -s "$tmp/MANIFEST.sha256" ] || { echo "manifest is empty" >&2; exit 1; }
grep -q "  database.dump$" "$tmp/MANIFEST.sha256" ||
  { echo "manifest has no database dump" >&2; exit 1; }

# Publication sequence: strictly greater than every complete generation already
# present. Under the lock this is race-free and makes the new generation the
# newest by recorded order, independent of its random name.
max_seq=0
for candidate in "$BACKUP_DIR"/generation-*; do
  [ -d "$candidate" ] || continue
  [ -L "$candidate" ] && continue
  current_seq="$(generation_seq "$candidate")"
  if [ "$current_seq" -gt "$max_seq" ]; then
    max_seq="$current_seq"
  fi
done
next_seq=$((max_seq + 1))

printf 'created_at=%s\nseq=%s\nkeep=%s\n' \
  "$timestamp" "$next_seq" "$KEEP_GENERATIONS" > "$tmp/COMPLETE"

run_suffix="${tmp##*-}"
final="$BACKUP_DIR/generation-${timestamp}-${run_suffix}"
if [ -e "$final" ] || [ -L "$final" ]; then
  echo "generation $final already exists" >&2
  exit 1
fi
mv "$tmp" "$final"
tmp=""

write_json "$STATUS_FILE" success "$final" "" || exit 1
write_json "$SUCCESS_FILE" success "$final" "" || exit 1
complete=1

# Retain the newest complete generations by recorded publication order; never
# touch incomplete directories and never delete anything before the new
# generation is complete. Symlinked entries are skipped so retention can never
# count or remove an out-of-tree generation.
generations="$work/generations"
: > "$generations"
for candidate in "$BACKUP_DIR"/generation-*; do
  [ -d "$candidate" ] || continue
  [ -L "$candidate" ] && continue
  [ -f "$candidate/COMPLETE" ] || continue
  current_seq="$(generation_seq "$candidate")"
  printf '%s %s\n' "$(printf '%09d' "$current_seq")" "$candidate"
done > "$generations"
if [ ! -s "$generations" ]; then
  echo "no complete generations found after publishing $final" >&2
  exit 1
fi
: > "$generations.sorted"
if ! LC_ALL=C sort -r "$generations" > "$generations.sorted"; then
  echo "could not order generations for retention" >&2
  exit 1
fi
kept=0
while IFS= read -r entry; do
  dir="${entry#* }"
  kept=$((kept + 1))
  if [ "$kept" -gt "$KEEP_GENERATIONS" ] && [ "$dir" != "$final" ]; then
    rm -rf "$dir"
  fi
done < "$generations.sorted"

echo "backup generation complete: $final"
