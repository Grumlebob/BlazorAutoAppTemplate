#!/usr/bin/env bash
# Start the freshly built app image with disposable PostgreSQL and Redis
# containers, check its HTTP surface, then run the browser smoke tests.
#
# Every container and network carries localcluster.ci.* labels, and cleanup
# removes only resources whose labels match this repository and run. Nothing
# here prunes, and PostgreSQL/Redis use tmpfs, so no Docker volume is created.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -P "$SCRIPT_DIR/../../.." && pwd)"
APP_IMAGE="${APP_IMAGE:?APP_IMAGE is required}"
APP_VERSION="${APP_VERSION:-${GITHUB_SHA:?APP_VERSION or GITHUB_SHA is required}}"
IMAGE_REF="${APP_IMAGE}:${APP_VERSION}"
APP_NAME="${APP_NAME:-$(bash "$SCRIPT_DIR/read-deploy-setting.sh" app_name)}"
[[ "$APP_NAME" =~ ^[a-z0-9][a-z0-9-]*$ ]] || { echo "app_name must be a lowercase slug: $APP_NAME" >&2; exit 1; }

# Keep these tags equal to TestContainerImages.cs and the CI preflight pulls.
POSTGRES_IMAGE="postgres:18.4-alpine3.23"
REDIS_IMAGE="redis:8.8.0-alpine3.23"
# Browser tests that prove SSR, hydration and pre-hydration control state.
BROWSER_SMOKE_FILTER="FullyQualifiedName~RenderModeE2ETests|FullyQualifiedName~PreHydrationControlsE2ETests"

expected_repository="${GITHUB_REPOSITORY:-local}"
expected_run_id="${GITHUB_RUN_ID:-local-$(cat /proc/sys/kernel/random/uuid)}"
expected_run_attempt="${GITHUB_RUN_ATTEMPT:-1}"
session="${expected_run_id}-${expected_run_attempt}"
network="${APP_NAME}-ci-${session}"
postgres="${APP_NAME}-ci-postgres-${session}"
redis="${APP_NAME}-ci-redis-${session}"
web="${APP_NAME}-ci-web-${session}"
owned_label_args=(
  --label "localcluster.ci.repository=${expected_repository}"
  --label localcluster.ci.owner=ci-smoke
  --label localcluster.ci.purpose=smoke
  --label "localcluster.ci.session=${session}"
  --label "localcluster.ci.run_id=${expected_run_id}"
  --label "localcluster.ci.run_attempt=${expected_run_attempt}"
  --label "localcluster.ci.created_at=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
)
expected_identity="${expected_repository} ci-smoke ${expected_run_id} ${expected_run_attempt}"
identity_format='{{index .Labels "localcluster.ci.repository"}} {{index .Labels "localcluster.ci.owner"}} {{index .Labels "localcluster.ci.run_id"}} {{index .Labels "localcluster.ci.run_attempt"}}'

owned_container() {
  [[ "$(docker inspect --format "${identity_format//.Labels/.Config.Labels}" "$1" 2>/dev/null || true)" == "$expected_identity" ]]
}

owned_network() {
  [[ "$(docker network inspect --format "$identity_format" "$1" 2>/dev/null || true)" == "$expected_identity" ]]
}

cleanup() {
  local status=$?
  trap - EXIT INT TERM
  if [[ "$status" -ne 0 ]]; then
    owned_container "$web" && docker logs --tail 200 --since 10m "$web" || true
    owned_container "$postgres" && docker logs --tail 200 --since 10m "$postgres" || true
    owned_container "$redis" && docker logs --tail 200 --since 10m "$redis" || true
  fi
  for container in "$web" "$postgres" "$redis"; do
    owned_container "$container" && docker rm -f "$container" >/dev/null 2>&1 || true
  done
  owned_network "$network" && docker network rm "$network" >/dev/null 2>&1 || true
  exit "$status"
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

wait_until_stable() {
  local attempts="$1"
  shift
  local consecutive_ready=0
  for ((attempt = 1; attempt <= attempts; attempt++)); do
    if "$@" >/dev/null 2>&1; then
      consecutive_ready=$((consecutive_ready + 1))
      if [[ "$consecutive_ready" -ge 3 ]]; then
        return 0
      fi
    else
      consecutive_ready=0
    fi
    sleep 2
  done
  "$@"
}

postgres_ready() {
  docker exec "$postgres" pg_isready -U postgres -d app
}

redis_ready() {
  docker exec "$redis" redis-cli ping | grep -Fxq PONG
}

docker network create "${owned_label_args[@]}" "$network"
docker run -d --name "$postgres" --network "$network" "${owned_label_args[@]}" \
  --tmpfs /var/lib/postgresql:rw,size=1073741824 \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=app \
  "$POSTGRES_IMAGE"
docker run -d --name "$redis" --network "$network" "${owned_label_args[@]}" \
  --tmpfs /data:rw,size=67108864 "$REDIS_IMAGE" \
  redis-server --save "" --appendonly no

wait_until_stable 90 postgres_ready
wait_until_stable 60 redis_ready

# The HTTP and browser checks share one client IP. Raise the limits only for
# this disposable container so the smoke does not trip production budgets.
docker run -d --name "$web" --network "$network" "${owned_label_args[@]}" \
  -p 127.0.0.1::8080 \
  -e ASPNETCORE_ENVIRONMENT=Docker \
  -e ASPNETCORE_HTTP_PORTS=8080 \
  -e "APP_VERSION=${APP_VERSION}" \
  -e "ConnectionStrings__DefaultConnection=Host=${postgres};Port=5432;Database=app;Username=postgres;Password=postgres;GSS Encryption Mode=Disable" \
  -e "Redis__Configuration=${redis}:6379,abortConnect=false" \
  -e Redis__AllowMissing=false \
  -e Database__RunMigrationsAtStartup=true \
  -e RateLimiting__Global__PermitLimit=10000 \
  -e RateLimiting__Api__PermitLimit=1000 \
  -e RateLimiting__Authentication__PermitLimit=1000 \
  -e LocalAccounts__Enabled=false \
  -e Observability__OpenTelemetry__Enabled=false \
  "$IMAGE_REF"

host_port="$(docker port "$web" 8080/tcp | sed -n 's/.*:\([0-9][0-9]*\)$/\1/p' | head -n 1)"
[[ -n "$host_port" ]] || { echo "web container did not publish port 8080" >&2; exit 1; }
base_url="http://127.0.0.1:${host_port}"

ready_deadline=$((SECONDS + 180))
until [[ "$(curl --silent --output /dev/null --write-out '%{http_code}' --max-time 5 "${base_url}/health/ready" || true)" == "200" ]]; do
  if (( SECONDS >= ready_deadline )); then
    echo "app did not report /health/ready within 180 seconds" >&2
    exit 1
  fi
  sleep 2
done
echo "app ready at ${base_url}"

# Production runs behind a TLS-terminating proxy; send the same forwarded
# protocol so HTTPS redirection does not apply to these plain-HTTP checks.
forwarded_proto=(--header "X-Forwarded-Proto: https")

home_html="$(curl --fail --silent --show-error --max-time 30 "${forwarded_proto[@]}" "${base_url}/")"
grep -Fqi '<!DOCTYPE html>' <<< "$home_html" || { echo "home page did not return HTML" >&2; exit 1; }
grep -Fq '_framework/blazor.web' <<< "$home_html" || { echo "home page does not load the Blazor web script" >&2; exit 1; }

api_headers="$(curl --silent --show-error --max-time 30 "${forwarded_proto[@]}" --dump-header - --output /dev/null "${base_url}/api/books")"
api_status="$(head -n 1 <<< "$api_headers" | awk '{print $2}')"
[[ "$api_status" == "401" ]] || { echo "anonymous /api/books returned ${api_status:-no status}, expected 401" >&2; exit 1; }
if grep -qi '^location:' <<< "$api_headers"; then
  echo "anonymous /api/books redirected instead of returning 401" >&2
  exit 1
fi
echo "HTTP smoke passed"

pwsh "$REPO_ROOT/BlazorAutoApp.Test/bin/Release/net10.0/playwright.ps1" install chromium
RUN_E2E=1 \
  E2E_BASE_URL="$base_url" \
  E2E_HEADLESS=1 \
  E2E_SLOW_MO_MS=0 \
  dotnet test "$REPO_ROOT/BlazorAutoApp.Test/BlazorAutoApp.Test.csproj" \
    --configuration Release --no-build --no-restore \
    --filter "$BROWSER_SMOKE_FILTER"
