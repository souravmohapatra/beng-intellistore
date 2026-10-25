#!/bin/sh
# Create one consistent recovery generation on the mounted backup destination.
# Runs inside the project `backup` container (postgres:17 client image).
#
# Consistency: pg_dump takes a point-in-time snapshot of the database. Accepted
# originals are immutable and written before their database records exist, so
# copying them after the snapshot yields a superset: every referenced original is
# present. A generation counts only after a manifest hashes every payload, a
# COMPLETE marker is written, and the temporary directory is atomically renamed.
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
tmp=""
work=""

write_json() {
  # $1=file $2=status $3=generation $4=message. Atomic, no financial contents.
  target="$1"
  dir="$(dirname "$target")"
  mkdir -p "$dir" || return 1
  scratch="$target.$$"
  printf '{"status":"%s","finished_at":"%s","generation":"%s","message":"%s"}\n' \
    "$2" "$timestamp" "$3" "$4" > "$scratch" || return 1
  mv "$scratch" "$target" || return 1
}

write_failed() {
  write_json "$STATUS_FILE" failed "" "${1:-backup did not complete}" 2>/dev/null ||
    echo "could not write backup status" >&2
}

cleanup() {
  if [ -n "$work" ]; then
    rm -rf "$work"
  fi
  if [ "$complete" -ne 1 ]; then
    if [ -n "$tmp" ] && [ -d "$tmp" ]; then
      printf 'backup did not complete; see service logs\n' > "$tmp/FAILED" 2>/dev/null || true
      echo "backup failed; incomplete generation kept at $tmp" >&2
    fi
    write_failed "backup did not complete"
  fi
}
trap cleanup EXIT

work="$(mktemp -d)"
mkdir -p "$BACKUP_DIR"
tmp="$(mktemp -d "$BACKUP_DIR/.incomplete-${timestamp}-XXXXXX")"

# Refuse a wrong/unavailable originals mount instead of silently publishing an
# unrecoverable empty backup. A fresh install may have no originals directory yet,
# but its parent data mount must exist.
orig_parent="$(dirname "$ORIGINALS_DIR")"
if [ ! -d "$orig_parent" ]; then
  echo "originals parent directory is missing: $orig_parent" >&2
  exit 1
fi
if [ -e "$ORIGINALS_DIR" ] && { [ ! -d "$ORIGINALS_DIR" ] || [ ! -r "$ORIGINALS_DIR" ] || [ ! -x "$ORIGINALS_DIR" ]; }; then
  echo "originals directory is not readable: $ORIGINALS_DIR" >&2
  exit 1
fi

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
  if [ -n "$(ls -A "$ORIGINALS_DIR" 2>/dev/null)" ]; then
    cp -a "$ORIGINALS_DIR/." "$tmp/originals/"
  fi
fi

# Build the manifest without masking failures through pipelines. Each payload is
# read and hashed individually, and the result is validated before publication.
list="$work/filelist"
sorted="$work/files.sorted"
find "$tmp" -type f ! -name MANIFEST.sha256 ! -name COMPLETE ! -name FAILED -print \
  > "$list"
LC_ALL=C sort "$list" > "$sorted"
: > "$tmp/MANIFEST.sha256"
while IFS= read -r file; do
  [ -r "$file" ] || { echo "payload is unreadable: ${file#"$tmp/"}" >&2; exit 1; }
  hash="$(sha256_of "$file")" || exit 1
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

printf 'created_at=%s\nkeep=%s\n' "$timestamp" "$KEEP_GENERATIONS" > "$tmp/COMPLETE"

final="$BACKUP_DIR/generation-$timestamp"
if [ -e "$final" ]; then
  echo "generation $final already exists" >&2
  exit 1
fi
mv "$tmp" "$final"
tmp=""

write_json "$STATUS_FILE" success "$final" "" || exit 1
write_json "$SUCCESS_FILE" success "$final" "" || exit 1
complete=1

# Retain the newest complete generations; never touch incomplete directories and
# never delete anything before the new generation is complete.
generations="$work/generations"
ls -1d "$BACKUP_DIR"/generation-* > "$generations" 2>/dev/null || : > "$generations"
LC_ALL=C sort -r "$generations" > "$generations.sorted"
kept=0
while IFS= read -r dir; do
  [ -f "$dir/COMPLETE" ] || continue
  kept=$((kept + 1))
  if [ "$kept" -gt "$KEEP_GENERATIONS" ]; then
    rm -rf "$dir"
  fi
done < "$generations.sorted"

echo "backup generation complete: $final"
