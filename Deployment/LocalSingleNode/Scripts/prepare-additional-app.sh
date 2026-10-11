#!/usr/bin/env bash
# Called only under the existing shared lock by the trusted setup workflow.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/../../.."
[[ "${APP_INSTANCE:-}" == additional && "${GITHUB_REF:-}" == refs/heads/main ]] || exit 2
[[ "$(id -un)" == deploy && "$(uname -s)" == Linux ]] || exit 2
case "$(uname -r)" in *[Mm]icrosoft*) exit 2 ;; esac
[[ -z "${LOCALSINGLENODE_ETC:-}${OPT_ROOT:-}" ]] || exit 2
[[ -n "${LOCALCLUSTER_DEPLOY_LOCK_TOKEN:-}" && -n "${LOCALCLUSTER_DEPLOY_LOCK_DIR:-}" ]] || exit 2
[[ "$(cat "$LOCALCLUSTER_DEPLOY_LOCK_DIR/token")" == "$LOCALCLUSTER_DEPLOY_LOCK_TOKEN" ]] || exit 2
[[ "${LOCALSINGLENODE_SETTINGS_FILE:?}" == "${RUNNER_TEMP:?}/instance-settings.yml" ]] || exit 2
[[ "${INSTANCE_EXTRA_VARS_FILE:?}" == "$RUNNER_TEMP/instance-vars.json" ]] || exit 2

# Readiness checks the existing primary app, not the additional configuration.
env -u LOCALSINGLENODE_SETTINGS_FILE python3 Deployment/LocalSingleNode/Scripts/native-readiness.py
bash Deployment/LocalSingleNode/Scripts/detect-machine.sh --previous /etc/localsinglenode/machine.yml --output "$RUNNER_TEMP/machine.yml"
bash Deployment/LocalSingleNode/Scripts/generate-inventory.sh --machine "$RUNNER_TEMP/machine.yml" --output "$RUNNER_TEMP/hosts.yml"
export ANSIBLE_CONFIG="$PWD/Deployment/LocalSingleNode/ansible/ansible.cfg"
ansible-playbook -i "$RUNNER_TEMP/hosts.yml" Deployment/LocalSingleNode/ansible/playbooks/PrepareAdditionalApp.yml \
  -e @"$INSTANCE_EXTRA_VARS_FILE" -e "instance_settings_file=$LOCALSINGLENODE_SETTINGS_FILE" \
  -e "source_repo_url=${GITHUB_SERVER_URL:?}/${GITHUB_REPOSITORY:?}"
