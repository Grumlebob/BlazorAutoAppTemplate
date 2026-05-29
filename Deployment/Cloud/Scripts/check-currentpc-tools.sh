#!/usr/bin/env bash
set -euo pipefail

required_tools=(
  bash
  curl
  gh
  git
  jq
  openssl
  python3
  ssh
  ssh-keygen
  tofu
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
printf '  ssh         %s\n' "$(ssh -V 2>&1)"
printf '  ssh-keygen  %s\n' "$(command -v ssh-keygen)"
printf '  tofu        %s\n' "$(tofu version | head -n 1)"

if gh auth status >/dev/null 2>&1; then
  printf '  gh auth     OK\n'
else
  printf '  gh auth     BLOCKER: run gh auth login\n' >&2
  exit 1
fi
