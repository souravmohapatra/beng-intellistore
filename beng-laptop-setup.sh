#!/usr/bin/env bash
#
# Interactive setup for the laptop worker that polls the mini-PC application
# for released jobs. Run it from a checkout of this repository, on the laptop:
#
#   sudo ./beng-laptop-setup.sh
#
# Re-running is safe and idempotent: the worker token and any running service
# are preserved, and installing or restarting the service is confirmed first.
# Nothing here wakes the laptop or changes its sleep policy: while the laptop
# sleeps the container stops polling and resumes when the laptop wakes again.

set -euo pipefail

ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
COMPOSE_FILE="$ROOT/compose.worker.yaml"
ENV_DIR=/etc/beng-intellistore-worker
UNIT_NAME=intellistore-worker.service
UNIT_SOURCE="$ROOT/deploy/systemd/$UNIT_NAME"
UNIT_PATH="/etc/systemd/system/$UNIT_NAME"
DROPIN_DIR="/etc/systemd/system/$UNIT_NAME.d"
DEFAULT_APP_URL='http://192.168.68.55:8017'
MINI_PC_TOKEN_FILE=/etc/beng-intellistore/laptop-worker.token

# shellcheck source=deploy/setup-wizard.sh
source "$ROOT/deploy/setup-wizard.sh"
# shellcheck source=deploy/setup-common.sh
source "$ROOT/deploy/setup-common.sh"

# Set here, once, so every stage shows the same progress.
TOTAL_STAGES=4

# Runs inside the worker container against the app's login page. A GET only:
# no job is claimed, and the worker token is not used.
read -r -d '' WORKER_CONNECTIVITY_CHECK <<'PY' || true
import sys
import urllib.error
import urllib.request

url = sys.argv[1]
try:
    with urllib.request.urlopen(url, timeout=10) as response:
        status = response.status
except urllib.error.HTTPError as exc:
    status = exc.code
except Exception as exc:
    print(f"could not reach {url}: {exc}", file=sys.stderr)
    raise SystemExit(1)
if status == 400:
    print(
        f"{url} returned HTTP 400: the app rejected the request host header. "
        "Add the address used here to DJANGO_ALLOWED_HOSTS in the mini-PC "
        "runtime file.",
        file=sys.stderr,
    )
    raise SystemExit(1)
if not 200 <= status < 400:
    print(f"{url} returned HTTP {status}.", file=sys.stderr)
    raise SystemExit(1)
print(f"reached {url} with HTTP {status}")
PY

worker_usage() {
  cat <<EOF
Usage: sudo $ROOT/beng-laptop-setup.sh

Interactive, idempotent setup for the laptop worker that polls the mini-PC
application for released jobs. There are no options: the wizard prompts for
everything it needs. Re-running keeps the stored worker token and asks before
installing or restarting the service.
EOF
}

# Non-fatal so a mistyped paste is retried rather than ending the run.
worker_check_token() {
  if [[ -z $1 ]]; then
    warn 'The worker token must not be empty.'
    return 1
  fi
  if [[ ! $1 =~ ^[A-Za-z0-9._~+/-]+=*$ ]]; then
    warn 'Use the token exactly as issued: letters, digits and . _ ~ + / - = only, on a single line.'
    return 1
  fi
}

worker_check_docker_path() {
  case $(command -v docker || true) in
    /usr/local/sbin/docker|/usr/local/bin/docker|/usr/sbin/docker|/usr/bin/docker|/sbin/docker|/bin/docker|/snap/bin/docker) ;;
    '') warn 'docker is not on PATH; the service will not find it.' ;;
    *) warn "docker is at $(command -v docker), outside the service PATH; the unit will not find it." ;;
  esac
}

# Printed last, after finish() clears the screen, so it stays visible.
worker_commands() {
  printf '\n%s  Commands%s\n' "$BOLD" "$BLUE"
  say "Status:       systemctl status $UNIT_NAME"
  say "Service log:  journalctl -u $UNIT_NAME -n 50 --no-pager"
  say "Worker log:   sudo docker --host=$DOCKER_HOST logs --tail 50 beng-intellistore-worker-worker-1"
  say "Follow log:   sudo docker --host=$DOCKER_HOST logs -f beng-intellistore-worker-worker-1"
  say "Stop:         sudo systemctl stop $UNIT_NAME"
  say "Start:        sudo systemctl start $UNIT_NAME"
  say "Re-run setup: sudo $ROOT/beng-laptop-setup.sh"
  printf '\n%s  Worker credential%s\n' "$BOLD" "$BLUE"
  say "The token was issued by the mini-PC and is stored root-only in $ENV_FILE."
  say 'The mini-PC keeps the same credential in its own root-only file and never prints it:'
  say "  ssh -t beng-mini-pc 'sudo cat $MINI_PC_TOKEN_FILE'   # then paste it into this wizard's hidden prompt"
  say "Transfer it only that way, never by email, chat, ticket or Git."
  say 'To rotate: issue a new token on the mini-PC, then re-run this script with the new value.'
  printf '\n'
}

run_wizard() {
  while (($#)); do
    case $1 in
      -h|--help) worker_usage; return 0 ;;
      *) setup_die "Unknown argument: $1 (try --help)" ;;
    esac
  done

  printf '\n%s%s  Intellistore laptop worker setup%s\n' "$BOLD" "$BLUE" "$RESET"
  printf '  This laptop polls the mini-PC app for released jobs, interprets them and\n'
  printf '  submits the results. Four stages: host and Docker; app address and worker\n'
  printf '  token; image build and app check; service install.\n'
  printf '  Re-running keeps the stored token and asks before changing the service.\n\n'
  pause 'Press Enter to begin.'

  stage 'Host, Docker and configuration file'
  setup_preflight
  setup_dependencies
  setup_runtime_file "$ENV_DIR"
  say "Configuration lives in $ENV_FILE (root-only, mode 0600)."
  setup_docker
  worker_check_docker_path
  setup_prompt APP_UID 'Container app uid' 1000
  [[ $APP_UID =~ ^[0-9]{1,10}$ ]] || setup_die 'APP_UID must be a numeric user id.'
  write_env APP_UID "$APP_UID"
  setup_prompt APP_GID 'Container app gid' 1000
  [[ $APP_GID =~ ^[0-9]{1,10}$ ]] || setup_die 'APP_GID must be a numeric group id.'
  write_env APP_GID "$APP_GID"
  setup_plain_path "$ROOT"
  write_env INTELLISTORE_COMPOSE_DIR "$ROOT"
  say "The service will read this checkout at $ROOT and wait for its mount before starting."

  stage 'App address and worker credential'
  setup_prompt INTELLISTORE_APP_URL 'Mini-PC app URL' "$DEFAULT_APP_URL"
  setup_private_url "$INTELLISTORE_APP_URL"
  INTELLISTORE_APP_URL=${INTELLISTORE_APP_URL%/}
  write_env INTELLISTORE_APP_URL "$INTELLISTORE_APP_URL"
  setup_prompt WORKER_POLL_SECONDS 'Poll interval in seconds' 30
  [[ $WORKER_POLL_SECONDS =~ ^[0-9]{1,5}$ ]] \
    || setup_die 'The poll interval must be whole seconds from 1 to 86400.'
  ((10#$WORKER_POLL_SECONDS >= 1 && 10#$WORKER_POLL_SECONDS <= 86400)) \
    || setup_die 'The poll interval must be whole seconds from 1 to 86400.'
  write_env WORKER_POLL_SECONDS "$WORKER_POLL_SECONDS"
  say 'Paste the worker token issued by the mini-PC. Input is hidden; Enter keeps the stored token.'
  note "On the mini-PC the token is $MINI_PC_TOKEN_FILE (root-only, never printed by that setup)."
  note "Read it there, then paste it here: ssh -t beng-mini-pc 'sudo cat $MINI_PC_TOKEN_FILE'"
  while :; do
    ask_secret WORKER_TOKEN 'Worker token' || setup_die 'A worker token is required; nothing was installed.'
    if worker_check_token "$WORKER_TOKEN"; then break; fi
    note 'Try again: paste the whole token from the mini-PC file, with no spaces.'
  done
  write_env WORKER_TOKEN "$WORKER_TOKEN"
  note 'The worker credential can claim jobs and submit results only; it cannot sign in or reach the database.'

  stage 'Build the worker image and check the app'
  say 'Building the worker image from this checkout; the first build takes a few minutes.'
  setup_compose build worker
  say "Checking ${INTELLISTORE_APP_URL}/login/ from inside the worker container (read-only GET, no job claimed)."
  if ! setup_compose run --rm --no-deps --entrypoint python worker \
    -c "$WORKER_CONNECTIVITY_CHECK" "$INTELLISTORE_APP_URL/login/"; then
    warn 'The worker container could not reach the mini-PC app login page.'
    say 'Check that the mini-PC setup finished and its app is running, then that this laptop reaches that address on the LAN.'
    say "From this host you can compare with: curl -fsS ${INTELLISTORE_APP_URL}/login/ >/dev/null"
    setup_die 'App connectivity check failed; nothing was installed or started.'
  fi

  stage 'Install and start the worker service'
  say 'The service runs one container that polls the mini-PC app and processes jobs released to this worker.'
  warn 'Starting the worker immediately claims and processes any eligible released jobs.'
  warn 'This laptop must be awake. The mini-PC requests bounded keep-awake leases during jobs; the worker does not force sleep or wake.'
  note 'While the laptop sleeps, polling stops and resumes when the laptop wakes.'
  note 'A rejected token shows up in the worker log as the container exits and restarts.'
  if systemctl is-active --quiet "$UNIT_NAME"; then
    question='Apply the current configuration and restart the running worker service now?'
    action=restart
  else
    question='Install and start the worker service now?'
    action=start
  fi
  if confirm "$question"; then
    install -d -m 0755 "$DROPIN_DIR"
    install -m 0644 "$UNIT_SOURCE" "$UNIT_PATH"
    cat >"$DROPIN_DIR/10-mounts.conf" <<EOF
# Written by beng-laptop-setup.sh: start only once this checkout is mounted.
[Unit]
RequiresMountsFor=$ROOT
EOF
    chmod 0644 "$DROPIN_DIR/10-mounts.conf"
    systemctl daemon-reload
    systemctl enable --quiet "$UNIT_NAME"
    if ! systemctl "$action" "$UNIT_NAME"; then
      systemctl --no-pager --full status "$UNIT_NAME" || true
      setup_die "The worker service failed to $action. Inspect: journalctl -u $UNIT_NAME -n 100 --no-pager"
    fi
    systemctl --no-pager --full status "$UNIT_NAME" || true
  else
    note 'Skipped: no unit was installed and no service was started.'
  fi

  finish
  worker_commands
}

run_wizard "$@"
