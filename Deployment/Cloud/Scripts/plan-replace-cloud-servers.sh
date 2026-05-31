#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
TOFU_DIR="$REPO_ROOT/Deployment/Cloud/infra/opentofu"
PLAN_FILE="${CLOUD_TOFU_PLAN_FILE:-cloud.tfplan}"

# shellcheck disable=SC1091
. "$SCRIPT_DIR/Component/lib/cloud-env.sh"
cloud_env_bootstrap_path

fail() {
  echo "cloud server replacement plan failed: $*" >&2
  exit 1
}

command -v tofu >/dev/null 2>&1 || fail "tofu is missing. Run Deployment/Cloud/Scripts/setup-currentpc-tools.sh."
[[ -f "$TOFU_DIR/terraform.tfvars" ]] || fail "missing Deployment/Cloud/infra/opentofu/terraform.tfvars. Run Step 6 first."

cd "$TOFU_DIR"

cloud_env_load_hcloud_token
bash "$SCRIPT_DIR/check-hcloud-token.sh"
tofu init
tofu fmt -check versions.tf variables.tf locals.tf main.tf firewalls.tf outputs.tf
tofu validate
rm -f "$PLAN_FILE"
tofu plan \
  -replace='hcloud_server.cloud_main' \
  -replace='hcloud_server.private_nodes["cloud-app1"]' \
  -replace='hcloud_server.private_nodes["cloud-app2"]' \
  -replace='hcloud_server.private_nodes["cloud-db"]' \
  -out "$PLAN_FILE"

cat <<EOF
Cloud server replacement plan written:

  Deployment/Cloud/infra/opentofu/$PLAN_FILE

Review the plan. It should replace the four cloud servers, keep the project
network/firewalls/SSH key under OpenTofu, and create the private network
attachments at server creation time.

Apply after review:

  cd "\$(git rev-parse --show-toplevel)/Deployment/Cloud/infra/opentofu"
  tofu apply "$PLAN_FILE"

If OpenTofu says the saved plan is stale, rerun this script and apply the new
plan immediately. That means the local state changed after the plan was created.
EOF
