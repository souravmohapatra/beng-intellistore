#!/usr/bin/env bash
# Local smoke check: isolated PostgreSQL, pinned dependencies, migrations, tests.
#
# Each invocation gets its own Compose project name and loopback port, so it
# never touches a developer database, other host services or private data. Only
# this invocation's container, network and volume are removed.
#
# Pass --keep to leave the isolated database running for manual browsing.
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
export POSTGRES_PORT

python_bin=.venv/bin/python
if [ ! -x "$python_bin" ]; then
  python3 -m venv .venv
fi
"$python_bin" -m pip install --quiet --upgrade pip
"$python_bin" -m pip install --quiet -r requirements.txt

cleanup() {
  local status=$?
  if [ "$KEEP" -eq 1 ] && [ "$status" -eq 0 ]; then
    echo "Isolated database left running: docker compose -p $project down --volumes" >&2
    return
  fi
  docker compose -p "$project" down --volumes --remove-orphans
}
trap cleanup EXIT

docker compose -p "$project" up -d --wait

"$python_bin" manage.py check
"$python_bin" manage.py makemigrations --check --dry-run
"$python_bin" manage.py test -v 2
