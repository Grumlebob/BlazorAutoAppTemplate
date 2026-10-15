#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"

if [[ "${ACTIONS_ARTIFACT_RETENTION_ENABLED:-false}" != "true" ]]; then
  echo "::notice::Artifact deletion is disabled; reporting candidates in dry-run mode."
  set -- "$@" --dry-run
fi

exec python3 "$REPO_ROOT/Deployment/Common/Scripts/Component/lib/prune-actions-artifacts.py" "$@"
