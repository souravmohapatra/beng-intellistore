#!/bin/sh
# Restore one recovery generation into an isolated database and directory.
# Runs inside the project `restore` container (postgres:17 client image).
#
# This never restores over the live database or live originals: the caller must
# name a different database and an empty originals target. The manifest is
# verified before any data is written, and the generation must carry COMPLETE.
set -eu

: "${PGHOST:?Set PGHOST}"
: "${PGUSER:?Set PGUSER}"
: "${LIVE_DATABASE:?Set LIVE_DATABASE to refuse accidental overwrite}"

usage() {
  echo "usage: $0 --generation DIR --database NAME --originals-target DIR" >&2
  exit 2
}

generation=""
target_db=""
originals_target=""
while [ $# -gt 0 ]; do
  case "$1" in
    --generation) generation="${2:-}"; shift 2 ;;
    --database) target_db="${2:-}"; shift 2 ;;
    --originals-target) originals_target="${2:-}"; shift 2 ;;
    *) usage ;;
  esac
done

[ -n "$generation" ] && [ -n "$target_db" ] && [ -n "$originals_target" ] || usage
[ -f "$generation/COMPLETE" ] || { echo "generation is incomplete" >&2; exit 1; }
[ -f "$generation/MANIFEST.sha256" ] || { echo "generation has no manifest" >&2; exit 1; }
[ -s "$generation/database.dump" ] || { echo "generation has no database dump" >&2; exit 1; }

if [ "$target_db" = "$LIVE_DATABASE" ]; then
  echo "refusing to restore over the live database" >&2
  exit 1
fi
if [ -e "$originals_target" ] && [ -n "$(ls -A "$originals_target" 2>/dev/null)" ]; then
  echo "originals target must be empty" >&2
  exit 1
fi

sha256_of() {
  if command -v sha256sum >/dev/null 2>&1; then
    sha256sum "$1" | cut -d' ' -f1
  else
    shasum -a 256 "$1" | cut -d' ' -f1
  fi
}

# Verify every manifest entry before writing anything.
while IFS= read -r line; do
  expected_hash="${line%%  *}"
  rest="${line#*  }"
  expected_size="${rest%%  *}"
  relative="${rest#*  }"
  file="$generation/$relative"
  [ -f "$file" ] || { echo "manifest entry missing: $relative" >&2; exit 1; }
  actual_hash="$(sha256_of "$file")"
  actual_size="$(wc -c < "$file" | tr -d ' ')"
  if [ "$actual_hash" != "$expected_hash" ] || [ "$actual_size" != "$expected_size" ]; then
    echo "manifest mismatch: $relative" >&2
    exit 1
  fi
done < "$generation/MANIFEST.sha256"

psql -h "$PGHOST" -U "$PGUSER" -d postgres -v ON_ERROR_STOP=1 \
  -c "CREATE DATABASE \"$target_db\"" >/dev/null
pg_restore -h "$PGHOST" -U "$PGUSER" -d "$target_db" \
  --no-owner --exit-on-error < "$generation/database.dump"

mkdir -p "$originals_target"
if [ -d "$generation/originals" ]; then
  cp -a "$generation/originals/." "$originals_target/"
fi

restored=0
if [ -d "$originals_target" ]; then
  for file in $(find "$originals_target" -type f -print); do
    sha256_of "$file" >/dev/null
    restored=$((restored + 1))
  done
fi

echo "restore complete: database=$target_db originals=$restored"
