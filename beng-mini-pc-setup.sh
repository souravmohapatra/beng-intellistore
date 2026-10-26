#!/usr/bin/env bash
#
# Interactive, repeatable setup for the Beng Statement Intelligence mini-PC.
#
# Covers: host prerequisites, the Docker endpoint, local storage, the root-only
# runtime settings and secrets, the first build and migration, and the systemd
# units. Written with the /wizard skill: the library in deploy/setup-wizard.sh is
# sourced unchanged and deploy/setup-common.sh provides the shared safety checks.
# Only the stages below are specific to this host.
#
# Usage:  sudo ./beng-mini-pc-setup.sh
#
# Safe to re-run: existing secrets, the database, uploaded originals and the
# worker token are kept, and every stored value is offered back as a default.
# This script never deletes data or volumes, never changes the Docker daemon,
# the global Docker context, firewall, proxy or sleep policy, and never
# configures DNS, TLS, a reverse proxy or backups.

set -euo pipefail

ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
COMPOSE_FILE="$ROOT/compose.production.yaml"
RUNTIME_DIR=/etc/beng-intellistore
WORKER_TOKEN_FILE="$RUNTIME_DIR/laptop-worker.token"

PROJECT_NAME=beng-intellistore-production
DEFAULT_BASE_DIR=/mnt/media/intelli-store
DEFAULT_BIND_ADDRESS=192.168.68.55
DEFAULT_HTTP_PORT=8017
DEFAULT_CONTROLLER_URL=http://192.168.68.55:8787
MIN_FREE_KIB=$((2 * 1024 * 1024))

# shellcheck source=deploy/setup-wizard.sh disable=SC1090
source "$ROOT/deploy/setup-wizard.sh"
# shellcheck source=deploy/setup-common.sh disable=SC1090
source "$ROOT/deploy/setup-common.sh"

TOTAL_STAGES=6

# ──────────────────────────────────────────────────────────────────────────
# Checks and actions shared by the stages. None of them prompt.
# ──────────────────────────────────────────────────────────────────────────

_usage() {
  cat <<'USAGE'
Usage: sudo ./beng-mini-pc-setup.sh [--help]

Interactive, re-runnable setup for the mini-PC deployment: local storage, the
Docker endpoint, runtime settings and secrets, the first migration, and the
systemd units. Nothing is deleted and no network service is reconfigured.
USAGE
}

# _local_filesystem_type PATH prints the filesystem type of the closest existing
# ancestor on stdout, and succeeds only for local block-device storage.
_local_filesystem_type() {
  local path=$1 fstype source
  while [[ ! -e $path ]]; do path=$(dirname -- "$path"); done
  fstype=$(findmnt -n -o FSTYPE --target "$path" 2>/dev/null) || return 1
  source=$(findmnt -n -o SOURCE --target "$path" 2>/dev/null) || return 1
  printf '%s' "$fstype"
  case $fstype in
    nfs|nfs4|cifs|smb3|9p|ceph|glusterfs|afs|fuse|fuse.*) return 1 ;;
  esac
  [[ $source == /dev/* ]]
}

_dir_has_entries() {
  [[ -d $1 ]] || return 1
  [[ -n $(ls -A -- "$1" 2>/dev/null) ]]
}

# Names of Docker volumes left behind by an earlier project layout.
_postgres_data_volumes() {
  docker --host="$DOCKER_HOST" volume ls \
    --filter "label=com.docker.compose.project=$PROJECT_NAME" \
    --format '{{.Name}}' 2>/dev/null \
    | grep -E '(^|_)postgres-data$' || true
}

_host_lan_addresses() {
  ip -o -4 addr show scope global | awk '{print $4}' | cut -d/ -f1 | sort -u
}

_is_private_lan_ipv4() {
  python3 - "$1" <<'PY'
import ipaddress
import sys

try:
    address = ipaddress.IPv4Address(sys.argv[1])
except ValueError:
    raise SystemExit("not an IPv4 address")
if not address.is_private or address.is_loopback or address.is_link_local \
        or address.is_multicast or address.is_unspecified or address.is_reserved:
    raise SystemExit("not a usable private LAN address")
PY
}

_list_contains() {
  local needle=$1 item
  shift
  for item in "$@"; do
    if [[ $item == "$needle" ]]; then return 0; fi
  done
  return 1
}

# True when something other than this deployment already holds PORT on the bind
# address (an address on the wildcard bind conflicts too).
_port_conflicts() {
  local port=$1 address=$2
  ss -ltnH "( sport = :$port )" 2>/dev/null \
    | awk '{print $4}' \
    | grep -qxE "(${address}|0\.0\.0\.0|\*|\[::\]|::):${port}"
}

# True when this Compose project's app container already publishes PORT.
_project_publishes_port() {
  local port=$1
  docker --host="$DOCKER_HOST" ps \
    --filter "label=com.docker.compose.project=$PROJECT_NAME" \
    --format '{{.Ports}}' 2>/dev/null \
    | grep -qF -- ":$port->8000/tcp"
}

_apply_storage() {
  local base=$1 data=$2 dbdir=$3
  install -d -m 0750 -o "$APP_UID" -g "$APP_GID" "$base" \
    || setup_die "Could not create or fix the storage directory $base."
  install -d -m 0700 -o "$APP_UID" -g "$APP_GID" "$data" \
    || setup_die "Could not create or fix the originals directory $data."
  install -d -m 0700 -o "$APP_UID" -g "$APP_GID" "$data/status" \
    || setup_die "Could not create or fix the backup status directory $data/status."
  if [[ ! -d $dbdir ]]; then
    install -d -m 0700 -o root -g root "$dbdir" \
      || setup_die "Could not create the database directory $dbdir."
    note "Created $dbdir (root-owned 0700); PostgreSQL owns it after first start."
  fi
}

# Drop-in so both units fail early when local storage or the checkout is absent.
_write_mount_dropin() {
  local unit=$1 dir="/etc/systemd/system/$1.d"
  install -d -m 0755 "$dir" || setup_die "Could not create $dir."
  printf '# Generated by beng-mini-pc-setup.sh: require local storage and the checkout.\n[Unit]\nRequiresMountsFor=%s %s\n' \
    "$INTELLISTORE_BASE_DIR" "$ROOT" > "$dir/50-requires-mounts.conf" \
    || setup_die "Could not write the mount drop-in for $unit."
  chmod 0644 "$dir/50-requires-mounts.conf"
}

# ──────────────────────────────────────────────────────────────────────────
# Stages
# ──────────────────────────────────────────────────────────────────────────

run_wizard() {
  local arg
  for arg in "$@"; do
    case $arg in
      -h|--help) _usage; return 0 ;;
      *) setup_die "Unknown option: $arg (try --help)" ;;
    esac
  done

  setup_preflight
  [[ -f $COMPOSE_FILE ]] || setup_die "Missing $COMPOSE_FILE; run this script from the project checkout."
  setup_plain_path "$ROOT"

  printf '\n%s  Intellistore mini-PC setup%s\n' "$BOLD" "$RESET"
  say "Checkout: $ROOT"
  printf '\n'
  say 'This wizard configures the application, its local database and the nightly release timer.'
  say 'Re-run it any time: stored settings, secrets, the database and originals are kept.'
  note 'It never deletes data or volumes, never changes the Docker daemon or global context,'
  note 'never stops unrelated services, and does not configure DNS, TLS, a proxy or backups.'
  pause 'Ready to start?'

  # ── Stage 1: host prerequisites ─────────────────────────────────────────
  stage 'Host checks and prerequisites'
  local tool missing=()
  for tool in ip ss findmnt; do
    if ! command -v "$tool" >/dev/null; then missing+=("$tool"); fi
  done
  if (( ${#missing[@]} )); then
    setup_die "Install iproute2 and util-linux (missing: ${missing[*]})."
  fi
  setup_dependencies
  setup_runtime_file "$RUNTIME_DIR"
  if [[ -e $ENV_FILE ]]; then setup_load_runtime; fi
  note "Runtime file: $ENV_FILE (root-only, mode 0600)"
  say ''
  say 'Prerequisites are present. Next: which Docker daemon this deployment uses.'

  # ── Stage 2: Docker endpoint ────────────────────────────────────────────
  stage 'Docker endpoint'
  say 'Select the local Docker daemon this deployment talks to.'
  note 'The daemon configuration, the global Docker context and other projects are never changed.'
  say ''
  setup_docker
  say ''
  note "Compose project: $PROJECT_NAME (fixed in compose.production.yaml)"

  # ── Stage 3: local storage ──────────────────────────────────────────────
  stage 'Local storage'
  say 'Originals and the database live in one local directory on this mini-PC.'
  note 'Network filesystems are refused, and no parent directory is chowned or chmodded.'
  say ''
  setup_prompt INTELLISTORE_BASE_DIR 'Deployment storage directory' "$DEFAULT_BASE_DIR"
  setup_plain_path "$INTELLISTORE_BASE_DIR"
  local base=$INTELLISTORE_BASE_DIR
  local docker_root
  docker_root=$(docker --host="$DOCKER_HOST" info --format '{{.DockerRootDir}}')
  if [[ $docker_root == /var/snap/docker/* && ( $base == /mnt/* || $base == /media/* ) ]]; then
    command -v snap >/dev/null || setup_die 'The selected snap Docker daemon needs snap tools to check media access.'
    if ! snap connections docker | awk '$1 == "removable-media" && $3 != "-" {connected=1} END {exit !connected}'; then
      warn 'The selected snap Docker daemon lacks removable-media access to this storage path.'
      confirm 'Grant Docker snap access to /mnt and /media (snap connect docker:removable-media)?' \
        || setup_die 'Media permission declined; this daemon cannot use the selected storage.'
      snap connect docker:removable-media
    fi
  fi
  local data=$base/data
  local dbdir=$base/postgres

  setup_prompt APP_UID 'Application user id (owns originals)' 1000
  setup_prompt APP_GID 'Application group id' 1000
  if [[ ! $APP_UID =~ ^[0-9]+$ || ! $APP_GID =~ ^[0-9]+$ ]]; then
    setup_die 'APP_UID and APP_GID must be numeric.'
  fi

  local path
  for path in "$base" "$data" "$dbdir"; do
    if [[ -L $path ]]; then setup_die "Refusing a symlinked storage path: $path"; fi
  done
  [[ ! -e $base || -d $base ]] || setup_die "Storage path is not a directory: $base"

  local probe=$base
  while [[ ! -e $probe ]]; do probe=$(dirname -- "$probe"); done
  local fstype
  if ! fstype=$(_local_filesystem_type "$probe"); then
    setup_die "Storage must be local disk: $probe is ${fstype:-not} local block storage (network filesystems are refused)."
  fi
  if [[ $probe != "$base" ]]; then
    note "$base does not exist yet; it will be created under $probe ($fstype)."
  fi
  local free_kib
  free_kib=$(df -Pk -- "$probe" | awk 'NR==2 {print $4}')
  [[ $free_kib =~ ^[0-9]+$ ]] || setup_die "Could not measure free space on $probe."
  note "$probe: $fstype, $((free_kib / 1024 / 1024)) GiB free."
  if (( free_kib < MIN_FREE_KIB )); then
    setup_die "Only $((free_kib / 1024)) MiB free on $probe; at least $((MIN_FREE_KIB / 1024)) MiB is needed for originals and the database."
  fi
  say ''

  local unexpected=() entry
  if [[ -d $base ]]; then
    while IFS= read -r entry; do
      case $entry in
        data|postgres) ;;
        *) unexpected+=("$entry") ;;
      esac
    done < <(ls -A -- "$base")
  fi
  if (( ${#unexpected[@]} )); then
    setup_die "Storage directory $base already holds other content (${unexpected[*]}); move it away or choose another directory, then re-run."
  fi
  if [[ -d $data && $(stat -c '%u:%g' "$data") != "$APP_UID:$APP_GID" ]] && _dir_has_entries "$data"; then
    setup_die "$data is owned by $(stat -c '%U:%G' "$data") and already contains files; set its owner to $APP_UID:$APP_GID yourself, then re-run."
  fi

  local -a volumes=()
  mapfile -t volumes < <(_postgres_data_volumes)
  local db_present=no
  if _dir_has_entries "$dbdir"; then db_present=yes; fi
  if (( ${#volumes[@]} )); then
    if [[ $db_present == yes ]]; then
      warn "Old Docker volume(s) still present: ${volumes[*]}; this deployment uses $dbdir and leaves them untouched."
    else
      setup_die "Docker volume(s) ${volumes[*]} may hold the only copy of the previous database, and $dbdir is empty. Inspect or copy that volume, remove it deliberately once you are sure, then re-run."
    fi
  fi

  local previous_base previous_db
  previous_base=$(_existing INTELLISTORE_BASE_DIR || true)
  previous_db=$(_existing INTELLISTORE_HOST_DATABASE_DIR || true)
  if [[ -n $previous_base && $previous_base != "$base" ]] && _dir_has_entries "$previous_base"; then
    warn "This deployment previously used $previous_base; this run points at $base."
    if ! confirm "Use $base and leave the previous directory untouched?"; then
      setup_die 'Declined; restore the previous storage directory or move its data first.'
    fi
  fi
  if [[ -n $previous_db && $previous_db != "$dbdir" ]] && _dir_has_entries "$previous_db"; then
    warn "The database currently lives in $previous_db; this run points at $dbdir."
    if ! confirm "Start with the database in $dbdir and leave $previous_db untouched?"; then
      setup_die 'Declined; point the storage directory back at the existing database.'
    fi
  fi

  say ''
  say 'Planned permissions (these paths only; nothing recursive):'
  note "  $base   owner $APP_UID:$APP_GID, mode 0750  — deployment root"
  note "  $data   owner $APP_UID:$APP_GID, mode 0700  — uploads and originals"
  note "  $data/status   owner $APP_UID:$APP_GID, mode 0700  — backup outcomes"
  note "  $dbdir  owner root:root, mode 0700  — PostgreSQL data, handed to the database container"
  say ''
  confirm 'Apply these storage permissions?' || setup_die 'Declined; no storage change was made.'
  _apply_storage "$base" "$data" "$dbdir"

  # ── Stage 4: application settings ───────────────────────────────────────
  stage 'Application settings'
  say "Address, port, controller URL and secrets are stored in $ENV_FILE (root-only)."
  say ''
  local -a lan=()
  mapfile -t lan < <(_host_lan_addresses)
  if (( ${#lan[@]} == 0 )); then
    setup_die 'No LAN IPv4 address on this host; connect the mini-PC to the LAN and re-run.'
  fi
  setup_prompt INTELLISTORE_BIND_ADDRESS 'LAN address the app binds to' "$DEFAULT_BIND_ADDRESS"
  if ! _is_private_lan_ipv4 "$INTELLISTORE_BIND_ADDRESS"; then
    setup_die "Use this mini-PC's private LAN IPv4 address (found: ${lan[*]}) - never 0.0.0.0, loopback or link-local."
  fi
  if ! _list_contains "$INTELLISTORE_BIND_ADDRESS" "${lan[@]}"; then
    setup_die "$INTELLISTORE_BIND_ADDRESS is not an address of this host (found: ${lan[*]})."
  fi
  note "The app publishes $INTELLISTORE_BIND_ADDRESS only; the port is never opened on 0.0.0.0."

  setup_prompt INTELLISTORE_HTTP_PORT 'LAN port for the app' "$DEFAULT_HTTP_PORT"
  setup_port "$INTELLISTORE_HTTP_PORT"
  if _port_conflicts "$INTELLISTORE_HTTP_PORT" "$INTELLISTORE_BIND_ADDRESS"; then
    if _project_publishes_port "$INTELLISTORE_HTTP_PORT"; then
      note "Port $INTELLISTORE_HTTP_PORT is already published by this deployment's app container; reusing it."
    else
      setup_die "Port $INTELLISTORE_HTTP_PORT is already in use on this host by another service; choose a free port or stop that service yourself."
    fi
  fi
  say ''

  ask DJANGO_DNS_HOST 'Optional LAN DNS name (blank skips, "-" clears)' \
    || setup_die 'Input ended; re-run the wizard when you are ready.'
  local dns_name=$DJANGO_DNS_HOST
  if [[ $dns_name == - ]]; then dns_name=''; fi
  if [[ -n $dns_name ]]; then
    if [[ ! $dns_name =~ ^[A-Za-z0-9]([A-Za-z0-9-]{0,61}[A-Za-z0-9])?(\.[A-Za-z0-9]([A-Za-z0-9-]{0,61}[A-Za-z0-9])?)*$ ]]; then
      setup_die "Use a DNS name such as intelli-store.home.arpa: '$dns_name'"
    fi
    local resolved=''
    resolved=$(getent hosts "$dns_name" 2>/dev/null | awk 'NR==1 {print $1}') || resolved=''
    if [[ -z $resolved ]]; then
      note "$dns_name does not resolve yet; add your own DNS/DHCP record (this wizard never changes DNS)."
    elif [[ $resolved != "$INTELLISTORE_BIND_ADDRESS" ]]; then
      warn "$dns_name currently resolves to $resolved, not $INTELLISTORE_BIND_ADDRESS; fix the DNS record later."
    fi
  else
    warn 'No DNS name set; reach the app by address until you add one.'
  fi
  say ''

  setup_prompt LAPTOP_CONTROLLER_URL 'Wake controller URL reachable from containers' "$DEFAULT_CONTROLLER_URL"
  if [[ -n $LAPTOP_CONTROLLER_URL ]]; then
    setup_private_url "$LAPTOP_CONTROLLER_URL"
  else
    warn 'No controller URL: nightly release stays queued and no wake request is sent.'
  fi

  local existing_password existing_secret
  existing_password=$(_existing POSTGRES_PASSWORD || true)
  existing_secret=$(_existing DJANGO_SECRET_KEY || true)
  if [[ $db_present == yes ]]; then
    if [[ -z $existing_password ]]; then
      setup_die "The database in $dbdir already exists but $ENV_FILE has no POSTGRES_PASSWORD. Restore the original runtime.env and re-run; this wizard never points a newly generated database password at existing data."
    fi
    if [[ -z $existing_secret ]]; then
      setup_die "The database in $dbdir already exists but $ENV_FILE has no DJANGO_SECRET_KEY. Restore the original runtime.env (or write the existing key back into it) and re-run; this wizard never replaces the application secret next to existing data."
    fi
  fi
  if [[ -n $existing_password ]]; then
    note 'Keeping the stored POSTGRES_PASSWORD.'
  else
    say 'Generating a new POSTGRES_PASSWORD (stored root-only, never printed).'
  fi
  if [[ -n $existing_secret ]]; then
    note 'Keeping the stored DJANGO_SECRET_KEY.'
  else
    say 'Generating a new DJANGO_SECRET_KEY (stored root-only, never printed).'
  fi
  setup_secret DJANGO_SECRET_KEY
  setup_secret POSTGRES_PASSWORD

  local -a allowed=("$INTELLISTORE_BIND_ADDRESS" localhost 127.0.0.1)
  if [[ -n $dns_name ]]; then allowed+=("$dns_name"); fi
  local -A seen=()
  local -a unique=()
  local host
  for host in "${allowed[@]}"; do
    if [[ -z ${seen[$host]:-} ]]; then
      seen[$host]=1
      unique+=("$host")
    fi
  done
  local allowed_hosts
  allowed_hosts=$(IFS=,; printf '%s' "${unique[*]}")

  write_env INTELLISTORE_COMPOSE_DIR "$ROOT"
  write_env INTELLISTORE_BASE_DIR "$base"
  write_env INTELLISTORE_HOST_DATA_DIR "$data"
  write_env INTELLISTORE_HOST_DATABASE_DIR "$dbdir"
  write_env INTELLISTORE_BIND_ADDRESS "$INTELLISTORE_BIND_ADDRESS"
  write_env INTELLISTORE_HTTP_PORT "$INTELLISTORE_HTTP_PORT"
  write_env LAPTOP_CONTROLLER_URL "$LAPTOP_CONTROLLER_URL"
  write_env APP_UID "$APP_UID"
  write_env APP_GID "$APP_GID"
  write_env DJANGO_DNS_HOST "$dns_name"
  write_env DJANGO_ALLOWED_HOSTS "$allowed_hosts"

  # ── Stage 5: build, database and first-run checks ───────────────────────
  stage 'Build, database and application checks'
  setup_compose config --quiet || setup_die 'Compose configuration is invalid; see the error above.'
  if _dir_has_entries "$dbdir"; then
    warn "The database in $dbdir already exists: migrations upgrade it in place."
    warn 'Back it up first if you care about its current contents.'
  fi
  say ''
  confirm 'Build the images, migrate the database and start the application?' \
    || setup_die 'Declined; nothing was built, migrated or started.'
  say 'Building images (this can take a few minutes)...'
  setup_compose build || setup_die 'Image build failed; see the output above.'
  say 'Starting PostgreSQL...'
  setup_compose up -d --wait postgres || setup_die 'PostgreSQL did not become healthy; see the output above.'
  say 'Applying migrations...'
  setup_compose run --rm --no-deps release-jobs migrate \
    || setup_die 'Migrations failed; fix the cause shown above and re-run.'

  local superusers
  superusers=$(setup_compose run --rm --no-deps -T release-jobs shell -c \
    'from django.contrib.auth import get_user_model; print(get_user_model().objects.filter(is_superuser=True).exists())') \
    || setup_die 'Could not check for an existing superuser; see the output above.'
  if [[ $superusers == *True* ]]; then
    note 'A superuser already exists; keeping it and every other sign-in account.'
  else
    say 'Create the private sign-in account now; the app container asks for the username, e-mail and password.'
    setup_compose run --rm --no-deps release-jobs createsuperuser \
      || setup_die 'Superuser creation failed; re-run the wizard to try again.'
  fi

  if [[ -n $LAPTOP_CONTROLLER_URL ]]; then
    local controller_report
    controller_report=$(setup_compose run --rm -T --no-deps release-jobs shell -c '
import os
from jobs.controller import LaptopController

url = os.environ.get("LAPTOP_CONTROLLER_URL", "").strip()
if not url:
    raise SystemExit("LAPTOP_CONTROLLER_URL is empty in the container environment")
token = LaptopController(url)._fetch_token()
print(f"controller reachable and action token parsed: {bool(token)}")
') || setup_die "The app container could not read the wake controller page at $LAPTOP_CONTROLLER_URL (GET only, no wake was sent). Confirm the controller is running and reachable from containers, then re-run."
    note "$controller_report"
  fi

  [[ ! -L $WORKER_TOKEN_FILE ]] || setup_die "Refusing symlinked worker token file: $WORKER_TOKEN_FILE"
  local token token_hash token_valid
  if [[ -e $WORKER_TOKEN_FILE ]]; then
    if [[ $(stat -c '%u:%a' "$WORKER_TOKEN_FILE") != 0:600 ]]; then
      chown root:root "$WORKER_TOKEN_FILE"
      chmod 0600 "$WORKER_TOKEN_FILE"
      warn "Restored root-only mode 0600 on $WORKER_TOKEN_FILE."
    fi
    [[ -f $WORKER_TOKEN_FILE ]] || setup_die 'Worker token must be a regular file.'
    IFS= read -r token < "$WORKER_TOKEN_FILE" || setup_die 'Worker token file is empty or incomplete.'
    [[ $token =~ ^[A-Za-z0-9_-]{43}$ ]] || setup_die 'Stored worker token is malformed; restore the original token file.'
    token_hash=$(printf '%s' "$token" | sha256sum | cut -d' ' -f1)
    token_valid=$(setup_compose run --rm --no-deps -T release-jobs shell -c \
      "from jobs.models import WorkerCredential; print(WorkerCredential.objects.filter(token_hash='$token_hash', revoked_at__isnull=True).exists())")
    [[ $token_valid == *True* ]] || setup_die 'Stored worker token is not active in this database; restore the matching database/token before continuing.'
    unset token token_hash token_valid
    note "Worker token $WORKER_TOKEN_FILE already exists; keeping it and issuing no new credential."
  else
    local issuing
    issuing=$(setup_compose run --rm --no-deps -T release-jobs provision_worker --label laptop) \
      || setup_die 'Issuing the worker credential failed; re-run the wizard to try again.'
    token=$(printf '%s\n' "$issuing" | tail -n1)
    if [[ ! $token =~ ^[A-Za-z0-9_-]{43}$ ]]; then
      setup_die 'The worker credential output did not end in a token; check manage.py provision_worker and re-run.'
    fi
    (umask 077; printf '%s\n' "$token" > "$WORKER_TOKEN_FILE") \
      || setup_die "Could not write $WORKER_TOKEN_FILE."
    chown root:root "$WORKER_TOKEN_FILE"
    chmod 0600 "$WORKER_TOKEN_FILE"
    unset token issuing
    say "Worker credential stored in $WORKER_TOKEN_FILE (root-only, mode 0600); it was not printed."
  fi

  if _port_conflicts "$INTELLISTORE_HTTP_PORT" "$INTELLISTORE_BIND_ADDRESS" \
    && ! _project_publishes_port "$INTELLISTORE_HTTP_PORT"; then
    setup_die "Port $INTELLISTORE_HTTP_PORT became busy while the wizard ran; stop that service or pick another port and re-run."
  fi
  say 'Starting the application...'
  setup_compose up -d --wait app || setup_die 'The application did not become healthy; see the output above.'

  local url="http://$INTELLISTORE_BIND_ADDRESS:$INTELLISTORE_HTTP_PORT"
  local code='' _attempt
  for _attempt in 1 2 3 4 5; do
    code=$(curl -sS -o /dev/null --max-time 10 -w '%{http_code}' "$url/login/" 2>/dev/null) || code=''
    if [[ $code == 200 ]]; then break; fi
    sleep 3
  done
  if [[ $code != 200 ]]; then
    setup_die "The app did not answer $url/login/ with HTTP 200 (last status: ${code:-none}); inspect systemctl status intellistore-app.service and the container logs."
  fi
  say "$url/login/ answered HTTP 200."

  # ── Stage 6: systemd units ──────────────────────────────────────────────
  stage 'Systemd services'
  say 'Two units manage this deployment from now on:'
  note '  intellistore-app.service    brings the Compose stack up at boot and stops it cleanly'
  note '  intellistore-release.timer  runs the nightly 21:00 Europe/London release command'
  note 'Both receive a drop-in requiring the storage and checkout mounts.'
  say ''
  if confirm 'Install the systemd units and enable the app service?'; then
    install -m 0644 "$ROOT/deploy/systemd/intellistore-app.service" /etc/systemd/system/intellistore-app.service \
      || setup_die 'Could not install intellistore-app.service.'
    install -m 0644 "$ROOT/deploy/systemd/intellistore-release.service" /etc/systemd/system/intellistore-release.service \
      || setup_die 'Could not install intellistore-release.service.'
    install -m 0644 "$ROOT/deploy/systemd/intellistore-release.timer" /etc/systemd/system/intellistore-release.timer \
      || setup_die 'Could not install intellistore-release.timer.'
    _write_mount_dropin intellistore-app.service
    _write_mount_dropin intellistore-release.service
    systemctl daemon-reload || setup_die 'systemctl daemon-reload failed.'
    systemd-analyze verify /etc/systemd/system/intellistore-app.service \
      /etc/systemd/system/intellistore-release.service \
      /etc/systemd/system/intellistore-release.timer \
      || setup_die 'Installed units failed verification; fix the output above before enabling them.'
    note 'systemd-analyze verify accepted the installed units.'
    systemctl enable --now intellistore-app.service || setup_die 'Could not enable intellistore-app.service.'
    if ! systemctl is-active --quiet intellistore-app.service; then
      setup_die 'intellistore-app.service did not stay active; inspect systemctl status intellistore-app.service.'
    fi
    say 'intellistore-app.service is enabled and active.'
    warn 'intellistore-release.timer is Persistent: enabling it now may immediately catch up a'
    warn 'missed 21:00 slot, release pending work and ask the controller to wake the laptop.'
    if confirm 'Enable the nightly release timer (it will ask the controller to wake the laptop)?'; then
      systemctl enable --now intellistore-release.timer || setup_die 'Could not enable intellistore-release.timer.'
      note 'intellistore-release.timer is enabled; the wizard ran no release or wake itself.'
    else
      if systemctl is-active --quiet intellistore-release.timer \
        || systemctl is-enabled --quiet intellistore-release.timer; then
        warn 'Existing release timer state is unchanged: it may still release work and wake the laptop.'
        note 'To stop and disable it explicitly: sudo systemctl disable --now intellistore-release.timer'
      else
        note 'Timer is not active or enabled; enable it later with: sudo systemctl enable --now intellistore-release.timer'
      fi
      SKIPPED+=('Enable intellistore-release.timer')
    fi
  else
    note 'Existing units are unchanged; the containers started above remain running.'
    note 'Declining does not stop or disable a previous installation.'
    SKIPPED+=('Install and enable the systemd units')
  fi

  finish
  printf '\n'
  say "Application:  http://$INTELLISTORE_BIND_ADDRESS:$INTELLISTORE_HTTP_PORT"
  if [[ -n $dns_name ]]; then
    note "  $dns_name still needs the port: http://$dns_name:$INTELLISTORE_HTTP_PORT (add the DNS record yourself)"
  else
    note '  No DNS name; add one yourself and keep appending the port.'
  fi
  say "Storage:      $data (owner $APP_UID:$APP_GID, mode 0700; $base is 0750)"
  say "Database:     $dbdir (PostgreSQL-owned; never deleted by this wizard)"
  say "Settings:     $ENV_FILE (root-only, mode 0600)"
  say "Worker token: $WORKER_TOKEN_FILE (root-only, mode 0600)"
  say "Sign-in:      $url/login/"
  say "Logs:         journalctl -u intellistore-app.service, journalctl -u intellistore-release.service"
  note "  app logs:    sudo docker --host=$DOCKER_HOST logs -f beng-intellistore-production-app-1"
  note "  stop:        sudo systemctl stop intellistore-app.service   (never 'compose down --volumes')"
  printf '\n'
  note 'Not installed here: NAS or off-site backups, DNS/DHCP records, TLS, a reverse proxy and the laptop worker.'
  note 'The release timer is Persistent, so its next start may catch up a missed 21:00 slot.'
  say ''
  say 'Move the worker token to the laptop yourself when you are ready; this wizard never prints it:'
  note "  ssh -t beng-mini-pc 'sudo cat $WORKER_TOKEN_FILE'"
  note '  then paste that line into the hidden "Worker token" prompt of sudo ./beng-laptop-setup.sh on the laptop.'
}

run_wizard "$@"
