#!/usr/bin/env bash
set -euo pipefail

required_tools=(
  ansible
  ansible-playbook
  bash
  curl
  gh
  git
  jq
  openssl
  python3
  shellcheck
  ssh
  ssh-keygen
  tofu
  yamllint
)

missing=()
for tool in "${required_tools[@]}"; do
  if ! command -v "$tool" >/dev/null 2>&1; then
    missing+=("$tool")
  fi
done

if ((${#missing[@]} > 0)); then
  printf 'missing required CurrentPC tools:\n' >&2
  printf ' - %s\n' "${missing[@]}" >&2
  printf '\nRun this setup script first:\n' >&2
  printf '  bash ./Deployment/Cloud/Scripts/setup-currentpc-tools.sh\n' >&2
  exit 1
fi

printf 'CurrentPC tool check ok\n'
printf '  bash        %s\n' "$(bash --version | head -n 1)"
printf '  curl        %s\n' "$(curl --version | head -n 1)"
printf '  git         %s\n' "$(git --version)"
printf '  gh          %s\n' "$(gh --version | head -n 1)"
printf '  jq          %s\n' "$(jq --version)"
printf '  openssl     %s\n' "$(openssl version)"
printf '  python3     %s\n' "$(python3 --version)"
printf '  shellcheck  %s\n' "$(shellcheck --version | awk -F': ' '/^version:/ { print $2; exit }')"
printf '  ssh         %s\n' "$(ssh -V 2>&1)"
printf '  ssh-keygen  %s\n' "$(command -v ssh-keygen)"
printf '  tofu        %s\n' "$(tofu version | head -n 1)"
printf '  yamllint    %s\n' "$(yamllint --version)"
printf '  ansible     %s\n' "$(ansible --version | head -n 1)"

if gh auth status >/dev/null 2>&1; then
  printf '  gh auth     OK\n'
else
  printf '  gh auth     BLOCKER: run gh auth login\n' >&2
  exit 1
fi
