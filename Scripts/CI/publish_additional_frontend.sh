#!/usr/bin/env bash
# Publish one explicitly requested additional frontend after the primary release.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/../.."

case "${FRONTEND_PROFILE:?Additional frontend is required}" in
  BlazorAuto) docker_target=final-blazor; suffix=blazorauto ;;
  React) docker_target=final-react; suffix=react ;;
  *) echo 'Unsupported additional frontend profile' >&2; exit 2 ;;
esac
expected_acceptance="$(python3 Scripts/Frontend/resolve_frontend_profile.py --override "$FRONTEND_PROFILE" --acceptance-profile)"
primary_profile="$(python3 Scripts/Frontend/resolve_frontend_profile.py)"
primary_image="$(bash Deployment/Common/Scripts/read-release-setting.sh app_image)"
[[ "$FRONTEND_PROFILE" != "$primary_profile" && "${FRONTEND_ACCEPTANCE_PROFILE:?}" == "$expected_acceptance" ]] || {
  echo 'Additional frontend must differ from the selected profile and use its acceptance contract' >&2; exit 2;
}
[[ "${APP_IMAGE:?}" == "${primary_image}-${suffix}" ]] || {
  echo 'Additional image must use its derived repository, separate from the primary image' >&2; exit 2;
}
[[ "${GITHUB_SHA:?}" =~ ^[0-9a-f]{40}$ && "${GITHUB_RUN_ID:?}" =~ ^[0-9]+$ && "${GITHUB_RUN_ATTEMPT:?}" =~ ^[0-9]+$ ]] || {
  echo 'Additional release requires the exact GitHub source, run and attempt' >&2; exit 2;
}
[[ "${CI_IMAGE_TAG:?}" == "${GITHUB_SHA}-${GITHUB_RUN_ID}-${GITHUB_RUN_ATTEMPT}" ]] || exit 2
export APP_VERSION="$CI_IMAGE_TAG"

cleanup() {
  local status=$?
  trap - EXIT
  local cleanup_status=0
  bash Deployment/LocalCluster/Scripts/ci-docker-smoke.sh --cleanup-only || cleanup_status=$?
  if docker image inspect "${APP_IMAGE}:${CI_IMAGE_TAG}" >/dev/null 2>&1; then
    docker image rm "${APP_IMAGE}:${CI_IMAGE_TAG}" || cleanup_status=$?
  fi
  [[ $status != 0 ]] || status=$cleanup_status
  exit "$status"
}
trap cleanup EXIT

# Copy only the two verified staging inputs; never overwrite the primary manifest.
mkdir artifacts/additional-migrations
cp "artifacts/migrations/${MIGRATION_BUNDLE_NAME:?}" artifacts/migrations/migration-provenance.json artifacts/additional-migrations/
python3 Scripts/CI/migration_staging_artifact.py validate \
  --directory artifacts/additional-migrations --bundle-filename "$MIGRATION_BUNDLE_NAME" --runtime "${MIGRATION_RUNTIME:?}"

# Restore/build the additional composition before using its browser binaries.
dotnet restore GrumPlates.Test/GrumPlates.Test.csproj "-p:FrontendProfile=${FRONTEND_PROFILE}"
dotnet build GrumPlates.Test/GrumPlates.Test.csproj --configuration Release --no-restore "-p:FrontendProfile=${FRONTEND_PROFILE}"
test -s GrumPlates.Test/bin/Release/net10.0/playwright.ps1
docker build --pull --target "$docker_target" \
  --build-arg "FRONTEND_PROFILE_OVERRIDE=${FRONTEND_PROFILE}" \
  --label "localcluster.ci.repository=${GITHUB_REPOSITORY:?}" \
  --label "org.opencontainers.image.source=${GITHUB_SERVER_URL:?}/${GITHUB_REPOSITORY}" \
  --label "org.opencontainers.image.revision=${GITHUB_SHA}" \
  --label localcluster.ci.owner=ci-build \
  --label "localcluster.ci.run_id=${GITHUB_RUN_ID}" \
  --label "localcluster.ci.run_attempt=${GITHUB_RUN_ATTEMPT}" \
  -f GrumPlates/Dockerfile -t "${APP_IMAGE}:${CI_IMAGE_TAG}" .
bash Deployment/LocalCluster/Scripts/ci-docker-smoke.sh
docker tag "${APP_IMAGE}:${CI_IMAGE_TAG}" "${APP_IMAGE}:${GITHUB_SHA}"
docker push "${APP_IMAGE}:${GITHUB_SHA}"
docker image inspect "${APP_IMAGE}:${GITHUB_SHA}" --format '{{json .RepoDigests}}' > "${RUNNER_TEMP:?}/additional-release-digests.json"
docker image inspect "${APP_IMAGE}:${GITHUB_SHA}" --format '{{json .Config.Labels}}' > "$RUNNER_TEMP/additional-release-labels.json"
python3 Scripts/CI/write_release_manifest.py --directory artifacts/additional-migrations \
  --digests "$RUNNER_TEMP/additional-release-digests.json" --labels "$RUNNER_TEMP/additional-release-labels.json"
