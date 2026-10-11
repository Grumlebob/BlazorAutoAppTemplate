#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -P "$SCRIPT_DIR/../.." && pwd)"

if [[ $# -ne 1 || -z "$1" ]]; then
  echo "Usage: validate-frontend-profiles.sh <results-directory>" >&2
  exit 2
fi
results_root="$1"
mkdir -p "$results_root"

for profile in BlazorAuto React; do
  acceptance_profile="$(python3 "$REPO_ROOT/Scripts/Frontend/resolve_frontend_profile.py" \
    --override "$profile" --acceptance-profile)"
  profile_results="$results_root/$profile"
  mkdir -p "$profile_results"

  echo "Restore, build and test frontend profile: $profile/$acceptance_profile"
  dotnet restore "$REPO_ROOT/BlazorAutoApp.sln" "-p:FrontendProfile=$profile"
  dotnet build "$REPO_ROOT/BlazorAutoApp.sln" \
    --configuration Release --no-restore "-p:FrontendProfile=$profile"

  test_arguments=(
    test "$REPO_ROOT/BlazorAutoApp.sln"
    --configuration Release
    --no-build
    --no-restore
    "-p:FrontendProfile=$profile"
    --logger "trx;LogFileName=suite.trx"
    --results-directory "$profile_results"
  )
  if [[ "$profile" == "React" ]]; then
    # These tests assert Blazor Auto assets and render modes; React has its own
    # host, public route, and browser coverage.
    test_arguments+=(--filter 'FrontendProfile!=BlazorAuto')
    expected_passed=202
  else
    expected_passed=210
  fi

  dotnet "${test_arguments[@]}"
  python3 "$REPO_ROOT/Scripts/CI/validate_dotnet_test_results.py" \
    "$profile_results/suite.trx" \
    --expected-passed "$expected_passed" \
    --expected-skipped 13 \
    --suite "$profile solution tests"
done
