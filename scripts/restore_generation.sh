#!/bin/sh
# Restore one recovery generation into an isolated database and directory.
# Runs inside the project `restore` container (postgres:17 client image).
#
# This never restores over the live database or live originals. The database
# identifier, the target directory and the manifest are fully validated
# (non-empty, one dump entry, safe unique paths, no symlinks, exact coverage of
# every original, matching hashes and sizes) before any database or filesystem
# write.
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

# A PostgreSQL identifier accepts letters, digits and underscores, must not start
# with a digit and is limited to 63 bytes. Reject anything else before any write so
# a quote or injection attempt can never reach the CREATE DATABASE statement.
case "$target_db" in
  ''|[!A-Za-z_]*|[!A-Za-z0-9_]*|*[!A-Za-z0-9_]*)
    echo "database name is not a valid identifier: $target_db" >&2
    exit 2
    ;;
esac
if [ "${#target_db}" -gt 63 ]; then
  echo "database name is longer than 63 bytes: $target_db" >&2
  exit 2
fi

if [ "$target_db" = "$LIVE_DATABASE" ]; then
  echo "refusing to restore over the live database" >&2
  exit 1
fi

[ -d "$generation" ] || { echo "generation directory is missing" >&2; exit 1; }
[ -L "$generation" ] && { echo "generation must not be a symbolic link" >&2; exit 1; }
[ -L "$generation/COMPLETE" ] &&
  { echo "generation COMPLETE must not be a symbolic link" >&2; exit 1; }
[ -L "$generation/MANIFEST.sha256" ] &&
  { echo "generation manifest must not be a symbolic link" >&2; exit 1; }
[ -L "$generation/database.dump" ] &&
  { echo "generation database dump must not be a symbolic link" >&2; exit 1; }
[ -f "$generation/COMPLETE" ] || { echo "generation is incomplete" >&2; exit 1; }
[ -s "$generation/MANIFEST.sha256" ] || { echo "generation has no manifest" >&2; exit 1; }
[ -s "$generation/database.dump" ] || { echo "generation has no database dump" >&2; exit 1; }

# Require a target that is truly empty: an absent path is created later, an
# existing path must be a readable, empty, non-symlinked directory.
if [ -e "$originals_target" ] || [ -L "$originals_target" ]; then
  if [ -L "$originals_target" ]; then
    echo "originals target must not be a symbolic link" >&2
    exit 1
  fi
  if [ ! -d "$originals_target" ]; then
    echo "originals target is not a directory" >&2
    exit 1
  fi
  if [ ! -r "$originals_target" ] || [ ! -x "$originals_target" ]; then
    echo "originals target is not readable" >&2
    exit 1
  fi
  if ! entries="$(ls -A "$originals_target" 2>/dev/null)"; then
    echo "originals target could not be read" >&2
    exit 1
  fi
  if [ -n "$entries" ]; then
    echo "originals target must be empty" >&2
    exit 1
  fi
fi

sha256_of() {
  if command -v sha256sum >/dev/null 2>&1; then
    out="$(sha256sum "$1")" || return 1
  else
    out="$(shasum -a 256 "$1")" || return 1
  fi
  printf '%s\n' "${out%% *}"
}

# Return failure if any path component of $2 below base directory $1 is a symlink.
path_has_symlink() {
  base="$1"
  rel="$2"
  cur="$base"
  old_ifs="$IFS"
  IFS=/
  set -f
  for part in $rel; do
    cur="$cur/$part"
    if [ -L "$cur" ]; then
      IFS="$old_ifs"
      set +f
      return 1
    fi
  done
  IFS="$old_ifs"
  set +f
  return 0
}

work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT
manifest_paths="$work/manifest.paths"
manifest_originals="$work/manifest.originals"
: > "$manifest_paths"
: > "$manifest_originals"
dump_entries=0

# Validate every manifest entry, path safety, uniqueness and exact bytes before
# writing anywhere.
while IFS= read -r line; do
  [ -n "$line" ] || { echo "manifest has an empty line" >&2; exit 1; }
  hash="${line%%  *}"
  rest="${line#*  }"
  [ "$hash" != "$line" ] || { echo "manifest entry is malformed" >&2; exit 1; }
  size="${rest%%  *}"
  relative="${rest#*  }"
  [ "$size" != "$rest" ] && [ -n "$size" ] && [ -n "$relative" ] ||
    { echo "manifest entry is malformed" >&2; exit 1; }
  case "$relative" in
    /*|..|../*|*/..|*/../*|*/|*//*)
      echo "manifest path is unsafe: $relative" >&2
      exit 1
      ;;
  esac
  file="$generation/$relative"
  path_has_symlink "$generation" "$relative" ||
    { echo "manifest path contains a symbolic link: $relative" >&2; exit 1; }
  [ -f "$file" ] && [ ! -L "$file" ] ||
    { echo "manifest entry is missing or not a regular file: $relative" >&2; exit 1; }
  actual_hash="$(sha256_of "$file")" || exit 1
  case "$actual_hash" in
    ''|*[!0-9a-f]*) echo "manifest hash is malformed" >&2; exit 1 ;;
  esac
  if [ "${#actual_hash}" -ne 64 ]; then
    echo "manifest hash is malformed" >&2
    exit 1
  fi
  actual_size="$(wc -c < "$file")" || exit 1
  actual_size=$((actual_size + 0))
  if [ "$actual_hash" != "$hash" ] || [ "$actual_size" -ne "$size" ]; then
    echo "manifest mismatch: $relative" >&2
    exit 1
  fi
  printf '%s\n' "$relative" >> "$manifest_paths"
  case "$relative" in
    database.dump) dump_entries=$((dump_entries + 1)) ;;
    originals/*) printf '%s\n' "$relative" >> "$manifest_originals" ;;
    *)
      echo "manifest contains an unexpected path: $relative" >&2
      exit 1
      ;;
  esac
done < "$generation/MANIFEST.sha256"

if [ "$dump_entries" -ne 1 ]; then
  echo "manifest must contain exactly one database dump" >&2
  exit 1
fi

: > "$work/paths.sorted"
if ! sort "$manifest_paths" > "$work/paths.sorted"; then
  echo "could not order manifest paths" >&2
  exit 1
fi
: > "$work/paths.duplicated"
if ! uniq -d "$work/paths.sorted" > "$work/paths.duplicated"; then
  echo "could not check manifest paths for duplicates" >&2
  exit 1
fi
if [ -s "$work/paths.duplicated" ]; then
  echo "manifest contains duplicate paths" >&2
  exit 1
fi

# Every original in the generation must be covered by the manifest, and no
# original may be a symlink or special file that enumeration would omit.
actual="$work/actual.originals"
: > "$actual"
if [ -L "$generation/originals" ]; then
  echo "generation originals must not be a symbolic link" >&2
  exit 1
fi
if [ -d "$generation/originals" ]; then
  if ! find "$generation/originals" -type f -print > "$actual"; then
    echo "could not enumerate generation originals" >&2
    exit 1
  fi
  nonregular="$work/nonregular.originals"
  : > "$nonregular"
  if ! find "$generation/originals" ! -type f ! -type d -print > "$nonregular"; then
    echo "could not inspect generation originals" >&2
    exit 1
  fi
  if [ -s "$nonregular" ]; then
    echo "generation originals contain a symlink or special file" >&2
    exit 1
  fi
fi
: > "$work/actual.originals.sorted"
if ! sort "$actual" > "$work/actual.originals.sorted"; then
  echo "could not order generation originals" >&2
  exit 1
fi
: > "$work/manifest.originals.sorted"
if ! sort "$manifest_originals" > "$work/manifest.originals.sorted"; then
  echo "could not order manifest originals" >&2
  exit 1
fi
: > "$work/actual.relative"
while IFS= read -r file; do
  [ -n "$file" ] || continue
  printf '%s\n' "${file#"$generation/"}" >> "$work/actual.relative"
done < "$work/actual.originals.sorted"
: > "$work/actual.relative.sorted"
if ! sort "$work/actual.relative" > "$work/actual.relative.sorted"; then
  echo "could not order actual originals" >&2
  exit 1
fi
if ! cmp -s "$work/manifest.originals.sorted" "$work/actual.relative.sorted"; then
  echo "manifest does not cover every original exactly once" >&2
  exit 1
fi

psql -h "$PGHOST" -U "$PGUSER" -d postgres -v ON_ERROR_STOP=1 \
  -c "CREATE DATABASE \"$target_db\"" >/dev/null
pg_restore -h "$PGHOST" -U "$PGUSER" -d "$target_db" \
  --no-owner --exit-on-error < "$generation/database.dump"

mkdir -p "$originals_target"
if [ -d "$generation/originals" ]; then
  cp -a "$generation/originals/." "$originals_target/"
fi

# Verify restored originals against the same manifest.
restored=0
while IFS= read -r line; do
  hash="${line%%  *}"
  rest="${line#*  }"
  size="${rest%%  *}"
  relative="${rest#*  }"
  case "$relative" in
    originals/*) ;;
    *) continue ;;
  esac
  target="$originals_target/${relative#originals/}"
  [ -f "$target" ] && [ ! -L "$target" ] ||
    { echo "restored original missing: $relative" >&2; exit 1; }
  actual_hash="$(sha256_of "$target")" || exit 1
  actual_size="$(wc -c < "$target")" || exit 1
  actual_size=$((actual_size + 0))
  if [ "$actual_hash" != "$hash" ] || [ "$actual_size" -ne "$size" ]; then
    echo "restored original mismatch: $relative" >&2
    exit 1
  fi
  restored=$((restored + 1))
done < "$generation/MANIFEST.sha256"

echo "restore complete: database=$target_db originals=$restored"
