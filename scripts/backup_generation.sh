#!/bin/sh
# Create one consistent recovery generation on the mounted backup destination.
# Runs inside the project `backup` container (postgres:17 client image).
#
# Consistency: pg_dump takes a point-in-time snapshot of the database. Accepted
# originals are immutable and written before their database records exist, so
# copying them after the snapshot yields a superset: every referenced original is
# present. A generation counts only after a COMPLETE marker is written and the
# temporary directory is atomically renamed. Retention removes an old complete
# generation only after the new one is complete.
#
# Normal application use never depends on this script succeeding.
set -eu

: "${BACKUP_DIR:?Set BACKUP_DIR (mounted destination)}"
: "${ORIGINALS_DIR:?Set ORIGINALS_DIR (mounted read-only originals)}"
: "${PGHOST:?Set PGHOST}"
: "${PGUSER:?Set PGUSER}"
: "${PGDATABASE:?Set PGDATABASE}"

KEEP_GENERATIONS="${KEEP_GENERATIONS:-7}"

case "$KEEP_GENERATIONS" in
  ''|*[!0-9]*) echo "KEEP_GENERATIONS must be a whole number" >&2; exit 2 ;;
esac
if [ "$KEEP_GENERATIONS" -lt 1 ]; then
  echo "KEEP_GENERATIONS must be at least 1" >&2
  exit 2
fi

sha256_of() {
  if command -v sha256sum >/dev/null 2>&1; then
    sha256sum "$1" | cut -d' ' -f1
  else
    shasum -a 256 "$1" | cut -d' ' -f1
  fi
}

timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -p "$BACKUP_DIR"
tmp="$(mktemp -d "$BACKUP_DIR/.incomplete-${timestamp}-XXXXXX")"
complete=0

write_status() {
  # Persist the outcome where the application can read it. No financial contents.
  [ -n "${STATUS_FILE:-}" ] || return 0
  status_dir="$(dirname "$STATUS_FILE")"
  mkdir -p "$status_dir"
  status_tmp="$STATUS_FILE.$$"
  printf '{"status":"%s","finished_at":"%s","generation":"%s","message":"%s"}\n' \
    "$1" "$timestamp" "${2:-}" "${3:-}" > "$status_tmp"
  mv "$status_tmp" "$STATUS_FILE"
}

cleanup() {
  if [ "$complete" -ne 1 ]; then
    # Incomplete generations stay visible for diagnosis but are never counted.
    printf 'backup did not complete; see service logs\n' > "$tmp/FAILED" 2>/dev/null || true
    write_status failed "" "backup did not complete"
    echo "backup failed; incomplete generation kept at $tmp" >&2
  fi
}
trap cleanup EXIT

pg_dump -h "$PGHOST" -U "$PGUSER" -d "$PGDATABASE" --format=custom \
  > "$tmp/database.dump"

if [ ! -s "$tmp/database.dump" ]; then
  echo "database dump was empty" >&2
  exit 1
fi

mkdir -p "$tmp/originals"
if [ -d "$ORIGINALS_DIR" ]; then
  cp -a "$ORIGINALS_DIR/." "$tmp/originals/"
fi

# Hash every payload so an isolated restore can prove exact bytes. Originals are
# content-addressed digests, so path sorting is stable and safe here.
(
  cd "$tmp"
  find . -type f ! -name MANIFEST.sha256 ! -name COMPLETE ! -name FAILED -print \
    | LC_ALL=C sort \
    | while IFS= read -r file; do
        size="$(wc -c < "$file" | tr -d ' ')"
        hash="$(sha256_of "$file")"
        printf '%s  %s  %s\n' "$hash" "$size" "${file#./}"
      done
) > "$tmp/MANIFEST.sha256"

printf 'created_at=%s\nkeep=%s\n' "$timestamp" "$KEEP_GENERATIONS" > "$tmp/COMPLETE"

final="$BACKUP_DIR/generation-$timestamp"
if [ -e "$final" ]; then
  echo "generation $final already exists" >&2
  exit 1
fi
mv "$tmp" "$final"
complete=1

# Retain the newest complete generations; never touch incomplete directories and
# never delete anything before the new generation is complete.
kept=0
for dir in $(ls -1d "$BACKUP_DIR"/generation-* 2>/dev/null | sort -r); do
  [ -f "$dir/COMPLETE" ] || continue
  kept=$((kept + 1))
  if [ "$kept" -gt "$KEEP_GENERATIONS" ]; then
    rm -rf "$dir"
  fi
done

echo "backup generation complete: $final"
write_status success "$final" ""
