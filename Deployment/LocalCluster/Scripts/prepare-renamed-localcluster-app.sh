#!/usr/bin/env bash
set -euo pipefail

usage() {
  local exit_code="${1:-1}"
  cat >&2 <<'EOF'
usage: prepare-renamed-localcluster-app.sh --old-app-name <name> [options]

Prepare a LocalCluster app after renaming deployment identity in all.yml.
Run this on the control machine from a checkout that already has the new
deployment settings.

By default the script validates settings and prints the planned actions only.
Actions are enabled explicitly with flags.

Required:
  --old-app-name <name>          Previous app_name, for example ship.

Options:
  --old-deploy-root <path>       Previous deploy root. Defaults to /opt/<old-app-name>.
  --setup-control-machine        Create/verify this app's new deploy key locally.
  --install-new-key              Install this app's new deploy key on nodes.
  --existing-key <path>          Existing deploy key used by --install-new-key.
  --configure-runner             Set LOCALCLUSTER_RUNNER_LABEL, install runner, and check it.
  --stop-old-runtime             Stop old Docker Compose stacks under old deploy root.
  --remove-old-marker            Remove /etc/localcluster/apps/<old-app-name>.env.
  --preflight                    Run deployment preflight after requested actions.
  --confirm-cutover              Required with --stop-old-runtime or --remove-old-marker.
  -h, --help                     Show this help.

Typical post-key/post-runner cutover:
  bash ./Deployment/LocalCluster/Scripts/prepare-renamed-localcluster-app.sh \
    --old-app-name ship \
    --stop-old-runtime \
    --remove-old-marker \
    --preflight \
    --confirm-cutover

Full control-machine preparation:
  bash ./Deployment/LocalCluster/Scripts/prepare-renamed-localcluster-app.sh \
    --old-app-name ship \
    --setup-control-machine \
    --install-new-key \
    --existing-key ~/.ssh/ship_deploy \
    --configure-runner \
    --stop-old-runtime \
    --remove-old-marker \
    --preflight \
    --confirm-cutover
EOF
  exit "$exit_code"
}

fail() {
  echo "renamed app preparation failed: $*" >&2
  exit 1
}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
INVENTORY="$REPO_ROOT/Deployment/LocalCluster/inventory/prod/hosts.yml"

OLD_APP_NAME=""
OLD_DEPLOY_ROOT=""
EXISTING_KEY=""
RUN_SETUP_CONTROL_MACHINE="no"
RUN_INSTALL_NEW_KEY="no"
RUN_CONFIGURE_RUNNER="no"
RUN_STOP_OLD_RUNTIME="no"
RUN_REMOVE_OLD_MARKER="no"
RUN_PREFLIGHT="no"
CONFIRM_CUTOVER="no"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --old-app-name)
      [[ $# -ge 2 ]] || usage
      OLD_APP_NAME="$2"
      shift 2
      ;;
    --old-deploy-root)
      [[ $# -ge 2 ]] || usage
      OLD_DEPLOY_ROOT="$2"
      shift 2
      ;;
    --setup-control-machine)
      RUN_SETUP_CONTROL_MACHINE="yes"
      shift
      ;;
    --install-new-key)
      RUN_INSTALL_NEW_KEY="yes"
      shift
      ;;
    --existing-key)
      [[ $# -ge 2 ]] || usage
      EXISTING_KEY="$2"
      shift 2
      ;;
    --configure-runner)
      RUN_CONFIGURE_RUNNER="yes"
      shift
      ;;
    --stop-old-runtime)
      RUN_STOP_OLD_RUNTIME="yes"
      shift
      ;;
    --remove-old-marker)
      RUN_REMOVE_OLD_MARKER="yes"
      shift
      ;;
    --preflight)
      RUN_PREFLIGHT="yes"
      shift
      ;;
    --confirm-cutover)
      CONFIRM_CUTOVER="yes"
      shift
      ;;
    -h|--help)
      usage 0
      ;;
    *)
      usage
      ;;
  esac
done

[[ -n "$OLD_APP_NAME" ]] || usage
[[ "$OLD_APP_NAME" =~ ^[a-z][a-z0-9-]{0,31}$ ]] || fail "old app name must be lowercase and app-name shaped"

if [[ -z "$OLD_DEPLOY_ROOT" ]]; then
  OLD_DEPLOY_ROOT="/opt/$OLD_APP_NAME"
fi

[[ "$OLD_DEPLOY_ROOT" == /opt/* ]] || fail "old deploy root must be under /opt"
[[ "$OLD_DEPLOY_ROOT" != "/opt/" ]] || fail "old deploy root must not be /opt/"
[[ ! "$OLD_DEPLOY_ROOT" =~ [[:space:]] ]] || fail "old deploy root must not contain whitespace"
[[ "$OLD_DEPLOY_ROOT" =~ ^/[A-Za-z0-9._/-]+$ ]] || fail "old deploy root contains unsupported characters"

command -v bash >/dev/null 2>&1 || fail "bash is missing"
command -v python3 >/dev/null 2>&1 || fail "python3 is missing"

bash "$SCRIPT_DIR/validate-deploy-settings.sh" >/dev/null

APP_NAME="$(bash "$SCRIPT_DIR/read-deploy-setting.sh" app_name)"
APP_IMAGE="$(bash "$SCRIPT_DIR/read-deploy-setting.sh" app_image)"
PUBLIC_HOSTNAME="$(bash "$SCRIPT_DIR/read-deploy-setting.sh" public_hostname)"
DEPLOY_ROOT="$(bash "$SCRIPT_DIR/read-deploy-setting.sh" deploy_root)"
APP_PORT="$(bash "$SCRIPT_DIR/read-deploy-setting.sh" app_port)"
POSTGRES_PORT="$(bash "$SCRIPT_DIR/read-deploy-setting.sh" postgres_port)"
REDIS_PORT="$(bash "$SCRIPT_DIR/read-deploy-setting.sh" redis_port)"
CLOUDFLARE_TUNNEL_NAME="$(bash "$SCRIPT_DIR/read-deploy-setting.sh" cloudflare_tunnel_name)"
RUNNER_LABEL="$(bash "$SCRIPT_DIR/read-deploy-setting.sh" runner_label)"
RUNNER_NAME="$(bash "$SCRIPT_DIR/read-deploy-setting.sh" runner_name)"

[[ "$APP_NAME" != "$OLD_APP_NAME" ]] || fail "current app_name is still $OLD_APP_NAME; rename all.yml first"
[[ "$DEPLOY_ROOT" != "$OLD_DEPLOY_ROOT" ]] || fail "current deploy_root equals old deploy root"
[[ -f "$INVENTORY" ]] || fail "missing inventory: Deployment/LocalCluster/inventory/prod/hosts.yml"

if [[ "$RUN_INSTALL_NEW_KEY" == "yes" ]]; then
  [[ -n "$EXISTING_KEY" ]] || fail "--install-new-key requires --existing-key"
fi

if [[ "$RUN_STOP_OLD_RUNTIME" == "yes" || "$RUN_REMOVE_OLD_MARKER" == "yes" ]]; then
  [[ "$CONFIRM_CUTOVER" == "yes" ]] || fail "--confirm-cutover is required before stopping old runtime or removing old marker"
fi

cat <<EOF
Renamed LocalCluster app preparation

Current app:
  app_name:               $APP_NAME
  app_image:              $APP_IMAGE
  public_hostname:        $PUBLIC_HOSTNAME
  deploy_root:            $DEPLOY_ROOT
  ports:                  app=$APP_PORT postgres=$POSTGRES_PORT redis=$REDIS_PORT
  cloudflare_tunnel_name: $CLOUDFLARE_TUNNEL_NAME
  runner:                 $RUNNER_NAME [$RUNNER_LABEL]

Old app:
  old_app_name:           $OLD_APP_NAME
  old_deploy_root:        $OLD_DEPLOY_ROOT

Requested actions:
  setup control machine:  $RUN_SETUP_CONTROL_MACHINE
  install new key:        $RUN_INSTALL_NEW_KEY
  configure runner:       $RUN_CONFIGURE_RUNNER
  stop old runtime:       $RUN_STOP_OLD_RUNTIME
  remove old marker:      $RUN_REMOVE_OLD_MARKER
  run preflight:          $RUN_PREFLIGHT
EOF

if [[ "$RUN_SETUP_CONTROL_MACHINE" == "yes" ]]; then
  bash "$SCRIPT_DIR/setup-control-machine.sh"
fi

if [[ "$RUN_INSTALL_NEW_KEY" == "yes" ]]; then
  bash "$SCRIPT_DIR/prepare-existing-localcluster-app.sh" --existing-key "$EXISTING_KEY"
fi

if [[ "$RUN_CONFIGURE_RUNNER" == "yes" ]]; then
  command -v gh >/dev/null 2>&1 || fail "gh is missing"
  gh auth status >/dev/null 2>&1 || fail "gh is not authenticated"
  gh variable set LOCALCLUSTER_RUNNER_LABEL --body "$RUNNER_LABEL"
  bash "$SCRIPT_DIR/install-github-runner.sh"
  bash "$SCRIPT_DIR/check-github-runner.sh"
fi

if [[ "$RUN_STOP_OLD_RUNTIME" == "yes" ]]; then
  command -v ansible >/dev/null 2>&1 || fail "ansible is missing"
  OLD_APP_NAME_Q="$(printf '%q' "$OLD_APP_NAME")"
  OLD_DEPLOY_ROOT_Q="$(printf '%q' "$OLD_DEPLOY_ROOT")"
  for group in app_servers node_db; do
    ansible "$group" -i "$INVENTORY" -m ansible.builtin.shell -a \
      "OLD_APP_NAME=$OLD_APP_NAME_Q OLD_DEPLOY_ROOT=$OLD_DEPLOY_ROOT_Q bash -lc 'set -euo pipefail
if [ ! -d \"\$OLD_DEPLOY_ROOT\" ]; then
  echo \"old deploy root absent: \$OLD_DEPLOY_ROOT\"
  exit 0
fi
if [ ! -f \"\$OLD_DEPLOY_ROOT/docker-compose.yml\" ]; then
  echo \"old deploy root has no docker-compose.yml: \$OLD_DEPLOY_ROOT\"
  exit 0
fi
if [ ! -f \"\$OLD_DEPLOY_ROOT/.env\" ]; then
  echo \"refusing to stop \$OLD_DEPLOY_ROOT because .env is missing\" >&2
  exit 1
fi
root_app=\"\$(sed -n \"s/^APP_NAME=//p\" \"\$OLD_DEPLOY_ROOT/.env\" | tail -n 1)\"
if [ -n \"\$root_app\" ] && [ \"\$root_app\" != \"\$OLD_APP_NAME\" ]; then
  echo \"refusing to stop \$OLD_DEPLOY_ROOT; .env says APP_NAME=\$root_app\" >&2
  exit 1
fi
cd \"\$OLD_DEPLOY_ROOT\"
docker compose down'"
  done
fi

if [[ "$RUN_REMOVE_OLD_MARKER" == "yes" ]]; then
  command -v ansible >/dev/null 2>&1 || fail "ansible is missing"
  OLD_APP_NAME_Q="$(printf '%q' "$OLD_APP_NAME")"
  ansible all -i "$INVENTORY" -m ansible.builtin.shell -a \
    "OLD_APP_NAME=$OLD_APP_NAME_Q bash -lc 'set -euo pipefail
marker=\"/etc/localcluster/apps/\${OLD_APP_NAME}.env\"
if [ ! -f \"\$marker\" ]; then
  echo \"old marker absent: \$marker\"
  exit 0
fi
APP_NAME=\"\"
. \"\$marker\"
if [ \"\$APP_NAME\" != \"\$OLD_APP_NAME\" ]; then
  echo \"refusing to remove \$marker; marker APP_NAME=\$APP_NAME\" >&2
  exit 1
fi
rm -f \"\$marker\"
echo \"removed old marker: \$marker\"'" \
    --become
fi

if [[ "$RUN_PREFLIGHT" == "yes" ]]; then
  bash "$SCRIPT_DIR/preflight.sh" deploy
fi

echo
echo "renamed app preparation complete"
