#!/usr/bin/env bash

cloud_env_bootstrap_path() {
  local local_bin="$HOME/.local/bin"

  if [[ -d "$local_bin" && ":$PATH:" != *":$local_bin:"* ]]; then
    export PATH="$local_bin:$PATH"
  fi
}

cloud_env_note() {
  if [[ "${CLOUD_ENV_QUIET:-0}" != "1" ]]; then
    echo "$*"
  fi
}

cloud_env_repo_root() {
  if [[ -n "${REPO_ROOT:-}" ]]; then
    printf '%s\n' "$REPO_ROOT"
    return 0
  fi

  git rev-parse --show-toplevel 2>/dev/null
}

cloud_env_trim() {
  local value="$1"
  value="${value#"${value%%[![:space:]]*}"}"
  value="${value%"${value##*[![:space:]]}"}"
  printf '%s\n' "$value"
}

cloud_env_read_dotenv_value() {
  local name="$1"
  local repo_root
  local env_file
  local line
  local value

  repo_root="$(cloud_env_repo_root)" || return 1
  env_file="$repo_root/.env.cloud"
  [[ -f "$env_file" ]] || return 1

  line="$(grep -E "^[[:space:]]*(export[[:space:]]+)?${name}[[:space:]]*=" "$env_file" | tail -n 1 || true)"
  [[ -n "$line" ]] || return 1

  value="${line#*=}"
  value="$(cloud_env_trim "$value")"
  if [[ ${#value} -ge 2 && "$value" == \"*\" && "$value" == *\" ]]; then
    value="${value:1:${#value}-2}"
  elif [[ ${#value} -ge 2 && "$value" == \'*\' && "$value" == *\' ]]; then
    value="${value:1:${#value}-2}"
  fi

  printf '%s\n' "$value"
}

cloud_env_load_missing_var() {
  local name="$1"
  local value

  [[ -z "${!name:-}" ]] || return 0

  value="$(cloud_env_read_dotenv_value "$name" || true)"
  [[ -n "$value" ]] || return 0

  printf -v "$name" '%s' "$value"
  export "${name?}"
  cloud_env_note "loaded ${name} from .env.cloud"
}

cloud_env_cloudflare_tunnel_token_is_valid() {
  local value="$1"

  [[ -n "$value" ]] || return 1
  [[ ${#value} -ge 80 ]] || return 1
  [[ "$value" != *[[:space:]]* ]] || return 1
  [[ "$value" =~ ^[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+$ ]] || return 1
}

cloud_env_load_valid_cloudflare_tunnel_token() {
  local value

  [[ -z "${CLOUD_CLOUDFLARE_TUNNEL_TOKEN:-}" ]] || return 0

  value="$(cloud_env_read_dotenv_value CLOUD_CLOUDFLARE_TUNNEL_TOKEN || true)"
  [[ -n "$value" ]] || return 0

  if cloud_env_cloudflare_tunnel_token_is_valid "$value"; then
    printf -v CLOUD_CLOUDFLARE_TUNNEL_TOKEN '%s' "$value"
    export CLOUD_CLOUDFLARE_TUNNEL_TOKEN
    cloud_env_note "loaded CLOUD_CLOUDFLARE_TUNNEL_TOKEN from .env.cloud"
    return 0
  fi

  cloud_env_note "ignored CLOUD_CLOUDFLARE_TUNNEL_TOKEN because it does not look like a Cloudflare tunnel token"
}

cloud_env_load_hcloud_token() {
  cloud_env_load_missing_var HCLOUD_TOKEN
}
