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
  dotnet restore "$REPO_ROOT/GrumPlates.sln" "-p:FrontendProfile=$profile"
  dotnet build "$REPO_ROOT/GrumPlates.sln" \
    --configuration Release --no-restore "-p:FrontendProfile=$profile"

  test_arguments=(
    test "$REPO_ROOT/GrumPlates.sln"
    --configuration Release
    --no-build
    --no-restore
    "-p:FrontendProfile=$profile"
    --logger "trx;LogFileName=non-accounts.trx"
    --results-directory "$profile_results"
  )
  non_account_filter='FullyQualifiedName!~Features.Login.Accounts'
  if [[ "$profile" == "React" ]]; then
    # These tests assert Blazor Auto assets and render modes; React has its own
    # host, public route, and browser coverage.
    non_account_filter+='&FrontendProfile!=BlazorAuto'
  fi
  test_arguments+=(--filter "$non_account_filter")

  dotnet "${test_arguments[@]}"
  # No test count is pinned: the validator rejects failures and skips that are not explicit opt-ins.
  python3 "$REPO_ROOT/Scripts/CI/validate_dotnet_test_results.py" \
    "$profile_results/non-accounts.trx" \
    --suite "$profile non-account tests"

  # Non-account tests allow the repository's explicitly opt-in browser skips.
  # Run shared account integration tests once and require every selected
  # test to execute, so an account test cannot silently become opt-in/skipped.
  account_results="$profile_results/accounts"
  account_filter='FullyQualifiedName~Features.Login.Accounts'
  if [[ "$profile" == "React" ]]; then
    account_filter+='&FrontendProfile!=BlazorAuto'
  fi
  mkdir -p "$account_results"
  dotnet test "$REPO_ROOT/GrumPlates.Test/GrumPlates.Test.csproj" \
    --configuration Release --no-build --no-restore "-p:FrontendProfile=$profile" \
    --filter "$account_filter" \
    --logger 'trx;LogFileName=accounts.trx' --results-directory "$account_results"
  python3 "$REPO_ROOT/Scripts/CI/validate_dotnet_test_results.py" \
    "$account_results/accounts.trx" \
    --expected-skipped 0 --suite "$profile account integration tests"
done
