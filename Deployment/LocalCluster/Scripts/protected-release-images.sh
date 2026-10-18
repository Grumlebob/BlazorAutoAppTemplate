#!/usr/bin/env bash
# Read the existing authority under the deployment lock; retain no parallel state.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMMON="$SCRIPT_DIR/../../Common/Scripts"
status="$(mktemp "${RUNNER_TEMP:-/tmp}/release-image-protection.XXXXXXXX")"
trap 'rm -f -- "$status"' EXIT
python3 "$SCRIPT_DIR/release-status.py" > "$status"
app_image="$(bash "$COMMON/read-release-setting.sh" app_image)"
python3 "$COMMON/protected-release-images.py" --status-json "$status" \
  --repository "${GITHUB_REPOSITORY:?GITHUB_REPOSITORY is required}" --app-image "$app_image"
