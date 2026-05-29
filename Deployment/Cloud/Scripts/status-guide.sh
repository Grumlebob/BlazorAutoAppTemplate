#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"

cd "$REPO_ROOT"

status_line() {
  local status="$1"
  local step="$2"
  local detail="$3"
  printf '%-8s %-9s %s\n' "$status" "$step" "$detail"
}

has_command() {
  command -v "$1" >/dev/null 2>&1
}

has_opentofu_module() {
  find Deployment/Cloud/infra/opentofu -maxdepth 1 -type f -name '*.tf' | grep -q .
}

check_common_release() {
  bash ./Deployment/Common/Scripts/validate-common-release.sh >/dev/null 2>&1
}

check_cloud_settings() {
  bash ./Deployment/Cloud/Scripts/validate-cloud-settings.sh >/dev/null 2>&1
}

check_hcloud_token() {
  if [[ -z "${HCLOUD_TOKEN:-}" ]]; then
    return 2
  fi
  if ! has_command curl || ! has_command jq; then
    return 3
  fi
  curl -fsS -H "Authorization: Bearer ${HCLOUD_TOKEN}" https://api.hetzner.cloud/v1/locations \
    | jq -e '.locations[] | select(.name == "fsn1")' >/dev/null
}

echo "Cloud guide status"
echo

if [[ -f Deployment/Cloud/HowToDeployCloud.md && -f Deployment/Common/release.yml ]] && check_common_release; then
  status_line "OK" "Step 0" "repo and shared release settings are present"
else
  status_line "BLOCKER" "Step 0" "repo or shared release settings need attention"
fi

if bash ./Deployment/Cloud/Scripts/check-currentpc-tools.sh >/dev/null 2>&1; then
  status_line "OK" "Step 1" "CurrentPC toolchain is installed"
else
  status_line "ACTION" "Step 1" "run: bash ./Deployment/Cloud/Scripts/setup-currentpc-tools.sh"
fi

if [[ -f Deployment/Cloud/inventory/prod/group_vars/all.yml \
  && -f Deployment/Cloud/inventory/prod/group_vars/all.example.yml \
  && -f Deployment/Cloud/inventory/prod/hosts.example.yml \
  && -f Deployment/Cloud/infra/opentofu/terraform.tfvars.example ]] && check_cloud_settings; then
  status_line "OK" "Step 2" "Cloud settings files are present and valid"
else
  status_line "BLOCKER" "Step 2" "Cloud settings files or validation need attention"
fi

if bash ./Deployment/Cloud/Scripts/read-cloud-setting.sh app_name >/dev/null 2>&1 \
  && bash ./Deployment/Cloud/Scripts/read-cloud-setting.sh public_hostname >/dev/null 2>&1 \
  && bash ./Deployment/Cloud/Scripts/read-cloud-setting.sh deploy_root >/dev/null 2>&1 \
  && bash ./Deployment/Cloud/Scripts/read-cloud-setting.sh cloudflare_tunnel_name >/dev/null 2>&1; then
  status_line "OK" "Step 3" "non-secret Cloud settings can be read"
else
  status_line "BLOCKER" "Step 3" "Cloud setting reader failed"
fi

if [[ -f "$HOME/.ssh/bookscloud_deploy" && -f "$HOME/.ssh/bookscloud_deploy.pub" ]]; then
  status_line "OK" "Step 4" "Cloud deploy SSH key exists"
else
  status_line "ACTION" "Step 4" "create ~/.ssh/bookscloud_deploy with the guide command"
fi

case "$(check_hcloud_token; echo $?)" in
  0)
    status_line "OK" "Step 5" "HCLOUD_TOKEN can access Hetzner Cloud API"
    ;;
  2)
    status_line "ACTION" "Step 5" "create/export HCLOUD_TOKEN"
    ;;
  3)
    status_line "ACTION" "Step 5" "install CurrentPC tools before API token verification"
    ;;
  *)
    status_line "BLOCKER" "Step 5" "HCLOUD_TOKEN is set but Hetzner API verification failed"
    ;;
esac

if has_opentofu_module; then
  if [[ -f Deployment/Cloud/infra/opentofu/terraform.tfvars ]]; then
    status_line "OK" "Step 6" "OpenTofu module and local tfvars exist"
  else
    status_line "ACTION" "Step 6" "run: bash ./Deployment/Cloud/Scripts/prepare-opentofu-tfvars.sh"
  fi
else
  status_line "BLOCKER" "Step 6" "OpenTofu module files are missing"
fi

if has_opentofu_module && [[ -f Deployment/Cloud/infra/opentofu/terraform.tfvars ]]; then
  status_line "ACTION" "Step 7" "run tofu plan/apply when ready"
else
  status_line "WAIT" "Step 7" "complete Step 6 first"
fi

if [[ -f Deployment/Cloud/Scripts/render-inventory-from-tofu.sh \
  && -f Deployment/Cloud/Scripts/Component/lib/render-inventory.py ]]; then
  status_line "ACTION" "Step 8" "renderer exists; run it after tofu apply"
else
  status_line "BLOCKER" "Step 8" "inventory renderer files are missing"
fi

status_line "MANUAL" "Step 9" "create Cloudflare tunnel and copy its token"

if has_opentofu_module; then
  status_line "WAIT" "Step 10" "complete successful tofu apply, then run configure-github-environment.sh"
else
  status_line "WAIT" "Step 10" "requires OpenTofu outputs"
fi

if [[ -f Deployment/Cloud/Scripts/preflight.sh \
  && -f Deployment/Cloud/Scripts/provision.sh \
  && -f Deployment/Cloud/ansible/playbooks/provision.yml ]]; then
  status_line "ACTION" "Step 11" "provision scripts exist"
else
  status_line "BLOCKER" "Step 11" "Cloud Ansible provision files are missing"
fi

if [[ -f .github/workflows/cd-cloud.yml ]]; then
  status_line "ACTION" "Step 12" "CD - Cloud workflow exists"
else
  status_line "BLOCKER" "Step 12" "CD - Cloud workflow is missing"
fi

if [[ -f Deployment/Cloud/Scripts/acceptance-check.sh ]]; then
  status_line "ACTION" "Step 13" "acceptance script exists"
else
  status_line "BLOCKER" "Step 13" "acceptance script is missing"
fi

if [[ -f Deployment/Cloud/Scripts/backup-db.sh && -f Deployment/Cloud/Scripts/restore-db.sh ]]; then
  status_line "ACTION" "Step 14" "backup and restore scripts exist"
else
  status_line "BLOCKER" "Step 14" "backup and restore scripts are missing"
fi
