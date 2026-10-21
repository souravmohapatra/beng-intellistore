#!/usr/bin/env bash
# Local smoke check: isolated PostgreSQL, isolated data directory, pinned
# dependencies, migrations, tests and a two-process restart check.
#
# Each invocation gets its own Compose project name, loopback port and data
# directory, so it never touches a developer database, other host services or
# private data. Only this invocation's container, network and volume are removed.
#
# Pass --keep to leave the isolated database and data directory in place; the
# selected port is printed. Volume deletion is destructive and is never the
# documented way to stop a development database.
set -euo pipefail

cd "$(dirname "$0")/.."

KEEP=0
for arg in "$@"; do
  case "$arg" in
    --keep) KEEP=1 ;;
    *)
      echo "usage: $0 [--keep]" >&2
      exit 2
      ;;
  esac
done

project="beng-intellistore-smoke-$$"
POSTGRES_PORT="$(python3 -c 'import socket; s = socket.socket(); s.bind(("127.0.0.1", 0)); print(s.getsockname()[1]); s.close()')"
data_dir="$(mktemp -d "${TMPDIR:-/tmp}/intellistore-smoke-XXXXXX")"
export POSTGRES_PORT
export INTELLISTORE_DATA_DIR="$data_dir"

python_bin=.venv/bin/python
if [ ! -x "$python_bin" ]; then
  python3 -m venv .venv
fi
"$python_bin" -m pip install --quiet --upgrade pip
"$python_bin" -m pip install --quiet -r requirements.txt

cleanup() {
  local status=$?
  if [ "$KEEP" -eq 1 ] && [ "$status" -eq 0 ]; then
    echo "Left running: project=$project port=$POSTGRES_PORT data_dir=$data_dir" >&2
    echo "Stop with: docker compose -p $project down" >&2
    return
  fi
  docker compose -p "$project" down --volumes --remove-orphans
  rm -rf "$data_dir"
}
trap cleanup EXIT

docker compose -p "$project" up -d --wait

"$python_bin" manage.py check
"$python_bin" manage.py makemigrations --check --dry-run
"$python_bin" manage.py test -v 2

"$python_bin" manage.py migrate --noinput
upload_id="$("$python_bin" scripts/restart_check.py upload)"
"$python_bin" scripts/restart_check.py verify "$upload_id"
