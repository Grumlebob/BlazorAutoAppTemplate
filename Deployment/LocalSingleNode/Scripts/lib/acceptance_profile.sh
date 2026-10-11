#!/usr/bin/env bash

resolve_acceptance_profiles() {
  local repo_root="$1"
  local script_dir="$2"
  local profile_pair expected frontend_input acceptance_input

  frontend_input="$(printenv FRONTEND_PROFILE || true)"
  acceptance_input="$(printenv ACCEPTANCE_PROFILE || true)"
  if [[ -n "$frontend_input" || -n "$acceptance_input" ]]; then
    [[ -n "$frontend_input" && -n "$acceptance_input" ]] || {
      echo "Both FRONTEND_PROFILE and ACCEPTANCE_PROFILE are required together." >&2
      return 2
    }
    FRONTEND_PROFILE="$frontend_input"
    ACCEPTANCE_PROFILE="$acceptance_input"
  else
    local deploy_root
    deploy_root="$(bash "$script_dir/read-setting.sh" deploy_root)" || return
    profile_pair="$(python3 "$script_dir/lib/read_release_acceptance.py" "$deploy_root/release.json" | tr '\n' ' ')" || return
    read -r FRONTEND_PROFILE ACCEPTANCE_PROFILE <<< "$profile_pair"
    [[ -n "$FRONTEND_PROFILE" && -n "$ACCEPTANCE_PROFILE" ]] || {
      echo "Deployed release marker did not provide a frontend and acceptance profile." >&2
      return 2
    }
  fi

  expected="$(python3 "$repo_root/Scripts/Frontend/resolve_frontend_profile.py" \
    --override "$FRONTEND_PROFILE" --acceptance-profile)" || return
  [[ "$ACCEPTANCE_PROFILE" == "$expected" ]] || {
    echo "Frontend and acceptance profiles do not match." >&2
    return 2
  }
  export FRONTEND_PROFILE ACCEPTANCE_PROFILE
}
