#!/usr/bin/env bash
set -euo pipefail
# Root-owned installation only. Wait for the entire job, including post steps.
[[ "$EUID" == 0 && $# == 4 ]] || { echo 'Operator-installed reboot helper requires root and four arguments.' >&2; exit 2; }
INSTALL_USER="$1"
REPOSITORY="$2"
RUN_ID="$3"
EXPECTED_NODE="$4"
[[ "$INSTALL_USER" =~ ^[a-z_][a-z0-9_-]*$ && "$INSTALL_USER" != root && "$INSTALL_USER" != deploy ]]
[[ "$REPOSITORY" =~ ^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$ && "$RUN_ID" =~ ^[0-9]+$ ]]
[[ "$(hostname)" == "$EXPECTED_NODE" ]]
for attempt in {1..30}; do
  echo "Waiting for whole-run success ($attempt/30)"
  result="$(sudo -u "$INSTALL_USER" -H gh api "repos/$REPOSITORY/actions/runs/$RUN_ID" --jq '[.status, .conclusion] | join(":")')"
  case "$result" in
    completed:success)
      sleep 30
      systemctl reboot
      exit 0
      ;;
    completed:*) echo 'Run failed or was cancelled; reboot withheld.'; exit 1 ;;
  esac
  sleep 60
done
echo 'Run completion deadline exceeded; reboot withheld.' >&2
exit 1
