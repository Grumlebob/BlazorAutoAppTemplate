#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_NAME="$(bash "$SCRIPT_DIR/read-setting.sh" app_name)"
UNIT="cloudflared-${APP_NAME}.service"
PUBLIC_CONFIG="/etc/${APP_NAME}/public.json"

if [[ ! -s "$PUBLIC_CONFIG" ]]; then
  echo "Public connector is not configured for ${APP_NAME}; refusing restart check." >&2
  exit 1
fi

service_status() {
  systemctl show --no-pager --property=ActiveState,SubState,ExecMainStatus "$UNIT"
}
healthy_status() {
  local status="$1"
  grep -Fxq 'ActiveState=active' <<<"$status" &&
    grep -Fxq 'SubState=running' <<<"$status" &&
    grep -Fxq 'ExecMainStatus=0' <<<"$status"
}
restart_count() {
  systemctl show --no-pager --property=NRestarts --value "$UNIT"
}
invocation_id() {
  systemctl show --no-pager --property=InvocationID --value "$UNIT"
}

before_status="$(service_status)"
if ! healthy_status "$before_status"; then
  echo "Public connector must be healthy before restart; current systemd state:" >&2
  printf '%s\n' "$before_status" >&2
  exit 1
fi
before_invocation="$(invocation_id)"
before_restarts="$(restart_count)"
if [[ -z "$before_invocation" || ! "$before_restarts" =~ ^[0-9]+$ ]]; then
  echo "Could not read connector invocation and restart state; refusing restart check." >&2
  exit 1
fi

sudo -n systemctl restart "$UNIT"
current_status=""
for _ in {1..30}; do
  current_status="$(service_status)"
  if healthy_status "$current_status"; then
    break
  fi
  sleep 1
done
if ! healthy_status "$current_status"; then
  echo "Public connector did not return to active/running with exit status 0:" >&2
  printf '%s\n' "$current_status" >&2
  exit 1
fi
after_invocation="$(invocation_id)"
after_restarts="$(restart_count)"
if [[ -z "$after_invocation" || "$after_invocation" == "$before_invocation" ]]; then
  echo "systemd did not start a new connector invocation." >&2
  exit 1
fi
if [[ ! "$after_restarts" =~ ^[0-9]+$ ]]; then
  echo "Could not read connector restart count after restart." >&2
  exit 1
fi

sleep 10
final_status="$(service_status)"
final_restarts="$(restart_count)"
if ! healthy_status "$final_status" || [[ "$final_restarts" != "$after_restarts" ]]; then
  echo "Public connector did not remain healthy for 10 seconds:" >&2
  printf '%s\nNRestarts after start: %s\nNRestarts after stability window: %s\n' \
    "$final_status" "$after_restarts" "$final_restarts" >&2
  exit 1
fi
printf 'Public connector restart recovery passed: active/running, new systemd invocation, restart count stable (%s).\n' \
  "$final_restarts"
