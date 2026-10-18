#!/usr/bin/env bash
# Start the freshly built app image with disposable PostgreSQL and Redis
# containers, check its HTTP surface, then run the browser smoke tests.
#
# Every container and network carries localcluster.ci.* labels, and cleanup
# removes only resources whose labels match this repository and run. Nothing
# here prunes, and PostgreSQL/Redis use tmpfs, so no Docker volume is created.
set -euo pipefail
CLEANUP_ONLY=false
if [[ $# -gt 0 ]]; then
  [[ $# == 1 && "$1" == --cleanup-only ]] || { echo 'Usage: ci-docker-smoke.sh [--cleanup-only]' >&2; exit 2; }
  CLEANUP_ONLY=true
  [[ -n "${GITHUB_REPOSITORY:-}" && "${GITHUB_RUN_ID:-}" =~ ^[0-9]+$ && "${GITHUB_RUN_ATTEMPT:-}" =~ ^[0-9]+$ ]] || {
    echo 'Cleanup-only requires the exact GitHub repository, run ID and attempt.' >&2; exit 2;
  }
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -P "$SCRIPT_DIR/../../.." && pwd)"
APP_IMAGE="${APP_IMAGE:?APP_IMAGE is required}"
APP_VERSION="${APP_VERSION:-${GITHUB_SHA:?APP_VERSION or GITHUB_SHA is required}}"
IMAGE_REF="${APP_IMAGE}:${APP_VERSION}"
FRONTEND_PROFILE="${FRONTEND_PROFILE:-BlazorAuto}"
case "$FRONTEND_PROFILE" in
  BlazorAuto|React) ;;
  *) echo "Unsupported frontend profile: $FRONTEND_PROFILE" >&2; exit 2 ;;
esac
expected_acceptance_profile="$(python3 "$REPO_ROOT/Scripts/Frontend/resolve_frontend_profile.py" --override "$FRONTEND_PROFILE" --acceptance-profile)"
FRONTEND_ACCEPTANCE_PROFILE="${FRONTEND_ACCEPTANCE_PROFILE:-$expected_acceptance_profile}"
[[ "$FRONTEND_ACCEPTANCE_PROFILE" == "$expected_acceptance_profile" ]] || {
  echo "Acceptance profile does not match the selected frontend profile" >&2
  exit 2
}
if [[ -n "${GITHUB_SHA:-}" && ! "$GITHUB_SHA" =~ ^[0-9a-f]{40}$ ]]; then
  echo "GITHUB_SHA must be a full lowercase commit SHA" >&2
  exit 2
fi
APP_NAME="${APP_NAME:-$(bash "$SCRIPT_DIR/read-deploy-setting.sh" app_name)}"
[[ "$APP_NAME" =~ ^[a-z0-9][a-z0-9-]*$ ]] || { echo "app_name must be a lowercase slug: $APP_NAME" >&2; exit 1; }

# Keep these tags equal to TestContainerImages.cs and the CI preflight pulls.
POSTGRES_IMAGE="postgres:18.4-alpine3.23"
REDIS_IMAGE="redis:8.8.0-alpine3.23"
SMTP_FIXTURE_IMAGE="node:24.21.0-bookworm-slim"
# Browser tests that prove SSR, hydration and pre-hydration control state.
BROWSER_SMOKE_FILTER="FullyQualifiedName~RenderModeE2ETests|FullyQualifiedName~PreHydrationControlsE2ETests"
REACT_DISABLED_BROWSER_FILTER="Category=ReactPackagedDisabled"
REACT_ENABLED_BROWSER_FILTER="Category=ReactPackagedEnabled"

expected_repository="${GITHUB_REPOSITORY:-local}"
expected_run_id="${GITHUB_RUN_ID:-local-$(cat /proc/sys/kernel/random/uuid)}"
expected_run_attempt="${GITHUB_RUN_ATTEMPT:-1}"
session="${expected_run_id}-${expected_run_attempt}"
network="${APP_NAME}-ci-${session}"
postgres="${APP_NAME}-ci-postgres-${session}"
redis="${APP_NAME}-ci-redis-${session}"
web="${APP_NAME}-ci-web-${session}"
web_enabled="${APP_NAME}-ci-web-enabled-${session}"
smtp="${APP_NAME}-ci-smtp-${session}"
fixture_dir=""
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
  local status="$1"
  trap - EXIT INT TERM
  if [[ "$status" -ne 0 ]]; then
    owned_container "$web" && docker logs --tail 200 --since 10m "$web" || true
    owned_container "$web_enabled" && docker logs --tail 200 --since 10m "$web_enabled" || true
    owned_container "$smtp" && docker logs --tail 200 --since 10m "$smtp" || true
    owned_container "$postgres" && docker logs --tail 200 --since 10m "$postgres" || true
    owned_container "$redis" && docker logs --tail 200 --since 10m "$redis" || true
  fi
  for container in "$web" "$web_enabled" "$smtp" "$postgres" "$redis"; do
    owned_container "$container" && docker rm -f "$container" >/dev/null 2>&1 || true
  done
  owned_network "$network" && docker network rm "$network" >/dev/null 2>&1 || true
  for container in "$web" "$web_enabled" "$smtp" "$postgres" "$redis"; do
    if owned_container "$container"; then echo "Owned smoke container remains: $container" >&2; status=1; fi
  done
  if owned_network "$network"; then echo "Owned smoke network remains: $network" >&2; status=1; fi
  if [[ -n "$fixture_dir" ]]; then
    local expected_prefix="${RUNNER_TEMP:-${TMPDIR:-/tmp}}/react-auth-${session}-"
    if [[ "$fixture_dir" == "$expected_prefix"* ]]; then
      rm -rf -- "$fixture_dir"
    else
      echo "Refusing to remove unexpected fixture path: $fixture_dir" >&2
      status=1
    fi
  fi
  exit "$status"
}
if [[ "$CLEANUP_ONLY" == true ]]; then cleanup 0; fi
image_labels="$(docker image inspect "$IMAGE_REF" --format '{{json .Config.Labels}}')"
python3 - "$FRONTEND_PROFILE" "$FRONTEND_ACCEPTANCE_PROFILE" "${GITHUB_SHA:-}" "$image_labels" <<'PY'
import json
import sys

frontend_profile, acceptance_profile, source_sha, labels_json = sys.argv[1:]
labels = json.loads(labels_json)
if not isinstance(labels, dict):
    raise SystemExit("final image labels are missing")
expected = {
    "com.blazorautoapp.frontend-profile": frontend_profile,
    "com.blazorautoapp.acceptance-profile": acceptance_profile,
}
if source_sha:
    expected["org.opencontainers.image.revision"] = source_sha
for key, value in expected.items():
    if labels.get(key) != value:
        raise SystemExit(f"final image label {key!r} does not match the selected release")
PY
trap 'cleanup "$?"' EXIT
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
# Loopback-only random host port: the browser tests clean up the users they
# register directly in this disposable database.
postgres_password="$(python3 -c 'import secrets; print(secrets.token_hex(24))')"
POSTGRES_PASSWORD="$postgres_password" docker run -d --name "$postgres" --network "$network" "${owned_label_args[@]}" \
  --network-alias ci-postgres \
  -p 127.0.0.1::5432 \
  --tmpfs /var/lib/postgresql:rw,size=1073741824 \
  -e POSTGRES_PASSWORD \
  -e POSTGRES_DB=app \
  "$POSTGRES_IMAGE"
docker run -d --name "$redis" --network "$network" "${owned_label_args[@]}" \
  --network-alias ci-redis \
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
  -e "ConnectionStrings__DefaultConnection=Host=ci-postgres;Port=5432;Database=app;Username=postgres;Password=${postgres_password};GSS Encryption Mode=Disable" \
  -e "Redis__Configuration=ci-redis:6379,abortConnect=false" \
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

if ! docker exec "$web" sh -c 'if command -v node >/dev/null 2>&1; then exit 1; fi; test ! -e /usr/local/bin/node && test ! -e /usr/bin/node'; then
  echo "final application image must not contain a Node.js runtime" >&2
  exit 1
fi

# Production runs behind a TLS-terminating proxy; send the same forwarded
# protocol so HTTPS redirection does not apply to these plain-HTTP checks.
forwarded_proto=(--header "X-Forwarded-Proto: https")

if [[ "$FRONTEND_PROFILE" == "React" ]]; then
  client_config_response="$(curl --silent --show-error --max-time 30 --dump-header - --output - "${forwarded_proto[@]}" "$base_url/api/client-config")"
  accounts_enabled="$(python3 -c 'import json,re,sys
raw=sys.stdin.buffer.read()
headers,body=raw.split(b"\r\n\r\n",1)
lines=headers.decode("latin1").splitlines()
assert lines and len(lines[0].split()) > 1 and lines[0].split()[1] == "200", "client config did not return 200"
header_lines=[line.lower() for line in lines[1:]]
assert any(line.startswith("cache-control:") and "no-store" in line for line in header_lines), "client config must be no-store"
assert not any(line.startswith("set-cookie:") for line in header_lines), "client config must not set cookies"
payload=json.loads(body)
assert type(payload.get("schemaVersion")) is int and payload["schemaVersion"] == 1, "client config schema version is invalid"
assert type(payload.get("accountsEnabled")) is bool, "client config capability is invalid"
assert re.fullmatch(r"[0-9a-fA-F]{32}", payload.get("applicationId", "")), "client config application ID is invalid"
print(str(payload["accountsEnabled"]).lower())' <<< "$client_config_response")"

  home_html="$(curl --fail --silent --show-error --max-time 30 --header 'Accept: text/html' "${forwarded_proto[@]}" "$base_url/")"
  grep -Fqi '<!DOCTYPE html>' <<< "$home_html" || { echo "React home page did not return HTML" >&2; exit 1; }
  grep -Eqi '<script[^>]+type="module"' <<< "$home_html" || { echo "React home page does not load an ES module" >&2; exit 1; }
  if grep -Eiq '(_framework|_content|blazor)' <<< "$home_html"; then
    echo "React home page contains inactive Blazor assets" >&2
    exit 1
  fi

  home_headers="$(curl --silent --show-error --max-time 30 --header 'Accept: text/html' "${forwarded_proto[@]}" --dump-header - --output /dev/null "$base_url/")"
  grep -Eiq '^Cache-Control:[[:space:]]*no-cache' <<< "$home_headers" || { echo "React shell must revalidate" >&2; exit 1; }
  shell_file_headers="$(curl --silent --show-error --max-time 30 --head "${forwarded_proto[@]}" "$base_url/index.html")"
  grep -Eiq '^HTTP/[^ ]+[[:space:]]+200([[:space:]]|$)' <<< "$shell_file_headers" || { echo "published React index.html did not return 200" >&2; exit 1; }
  grep -Eiq '^Cache-Control:[[:space:]]*no-cache' <<< "$shell_file_headers" || { echo "published React index.html must revalidate" >&2; exit 1; }
  grep -Eiq '^Content-Security-Policy:.*default-src .self.' <<< "$home_headers" || { echo "React shell is missing its content security policy" >&2; exit 1; }
  grep -Eiq '^Content-Security-Policy:.*sha256-' <<< "$home_headers" || { echo "React inline shell scripts must be authorized by exact hashes" >&2; exit 1; }
  if grep -Eiq '^Content-Security-Policy:.*unsafe-(inline|eval)' <<< "$home_headers"; then
    echo "React shell CSP contains an unsafe script directive" >&2
    exit 1
  fi

  asset_attribute="$(grep -Eo '(src|href)="[^"]+-[A-Za-z0-9_-]{8,}\.js"' <<< "$home_html" | head -n 1 || true)"
  asset_path="${asset_attribute#*=}"; asset_path="${asset_path#\"}"; asset_path="${asset_path%\"}"
  [[ -n "$asset_path" ]] || { echo "React shell does not reference a fingerprinted JavaScript asset" >&2; exit 1; }
  [[ "$asset_path" == /* ]] || asset_path="/$asset_path"
  asset_headers="$(curl --silent --show-error --max-time 30 --head "${forwarded_proto[@]}" "$base_url$asset_path")"
  grep -Eiq '^HTTP/[^ ]+[[:space:]]+200([[:space:]]|$)' <<< "$asset_headers" || { echo "fingerprinted React asset did not return 200" >&2; exit 1; }
  grep -Eiq '^Cache-Control:[[:space:]]*public, ?max-age=31536000, ?immutable' <<< "$asset_headers" || { echo "fingerprinted React assets must be immutable" >&2; exit 1; }

  for path in /books /books/author/example; do
    navigation_html="$(curl --fail --silent --show-error --max-time 30 --header 'Accept: text/html' "${forwarded_proto[@]}" "$base_url$path")"
    grep -Eqi '<script[^>]+type="module"' <<< "$navigation_html" || { echo "React navigation GET failed for $path" >&2; exit 1; }
    navigation_headers="$(curl --silent --show-error --max-time 30 --head --header 'Accept: text/html' "${forwarded_proto[@]}" "$base_url$path")"
    grep -Eiq '^HTTP/[^ ]+[[:space:]]+200([[:space:]]|$)' <<< "$navigation_headers" || { echo "React navigation HEAD failed for $path" >&2; exit 1; }
  done

  public_books="$(curl --fail --silent --show-error --max-time 30 "${forwarded_proto[@]}" "$base_url/api/author-books")"
  python3 -c 'import json,sys; books=json.load(sys.stdin).get("books"); assert isinstance(books,list) and books, "public author-book API returned no sample data"' <<< "$public_books" || { echo "public author-book API did not return seeded sample data" >&2; exit 1; }

  private_api_headers="$(curl --silent --show-error --max-time 30 "${forwarded_proto[@]}" --dump-header - --output /dev/null "$base_url/api/books")"
  private_api_status="$(head -n 1 <<< "$private_api_headers" | awk '{print $2}')"
  [[ "$private_api_status" == "401" ]] || { echo "anonymous /api/books returned ${private_api_status:-no status}, expected 401" >&2; exit 1; }
  grep -Eiq '^Cache-Control:[[:space:]]*private, ?no-store' <<< "$private_api_headers" || { echo "private API denial must not be cached" >&2; exit 1; }
  if grep -qi '^location:' <<< "$private_api_headers"; then
    echo "anonymous /api/books redirected instead of returning 401" >&2
    exit 1
  fi

  if [[ "$accounts_enabled" == "true" ]]; then
    login_headers="$(curl --silent --show-error --max-time 30 --dump-header - --output /dev/null "${forwarded_proto[@]}" "$base_url/api/auth/login")"
    grep -Eiq '^HTTP/[^ ]+[[:space:]]+405([[:space:]]|$)' <<< "$login_headers" || { echo "enabled GET /api/auth/login did not return 405" >&2; exit 1; }
    grep -Eiq '^Allow:[[:space:]]*POST[[:space:]]*$' <<< "$login_headers" || { echo "enabled GET /api/auth/login did not advertise Allow: POST" >&2; exit 1; }
    inactive_paths=(/Account /api/auth/not-a-real-operation /assets/missing.js)
  else
    inactive_paths=(/Account /api/auth /api/auth/session /api/auth/login /assets/missing.js)
  fi

  for path in "${inactive_paths[@]}"; do
    response="$(curl --silent --show-error --max-time 30 --write-out $'\n%{http_code}' --header 'Accept: text/html' "${forwarded_proto[@]}" "$base_url$path")"
    response_status="${response##*$'\n'}"
    response_body="${response%$'\n'*}"
    [[ "$response_status" == "404" ]] || { echo "$path returned ${response_status:-no status}, expected 404" >&2; exit 1; }
    if grep -Eiq '(<html|<script[^>]+type="module")' <<< "$response_body"; then
      echo "$path incorrectly returned the React shell" >&2
      exit 1
    fi
  done

  if docker exec "$web" sh -c 'test ! -e /app/wwwroot/_framework && test ! -e /app/wwwroot/_content'; then
    :
  else
    echo "React image contains inactive Blazor assets" >&2
    exit 1
  fi
  cd "$REPO_ROOT"
  pwsh -NoProfile -File "$REPO_ROOT/Scripts/Test-DeployedSite.ps1" \
    -FrontendProfile "$FRONTEND_PROFILE" -AcceptanceProfile "$FRONTEND_ACCEPTANCE_PROFILE" \
    -ForwardedProto https -BaseUrl "$base_url"
  echo "React public HTTP acceptance passed"
  echo "React disabled HTTP smoke passed"

  postgres_host_port="$(docker port "$postgres" 5432/tcp | sed -n 's/.*:\([0-9][0-9]*\)$/\1/p' | head -n 1)"
  [[ -n "$postgres_host_port" ]] || { echo "postgres did not publish port 5432" >&2; exit 1; }
  cd "$REPO_ROOT"
  pwsh "$REPO_ROOT/BlazorAutoApp.Test/bin/Release/net10.0/playwright.ps1" install chromium
  react_disabled_results_dir="${RUNNER_TEMP:-${TMPDIR:-/tmp}}/test-results/${expected_run_id}-${expected_run_attempt}/${GITHUB_JOB:-validate}/docker-smoke/React-disabled"
  mkdir -p "$react_disabled_results_dir"
  cd "$REPO_ROOT"
  E2E_CLEANUP_CONNECTION_STRING="Host=127.0.0.1;Port=${postgres_host_port};Database=app;Username=postgres;Password=${postgres_password};GSS Encryption Mode=Disable" \
  RUN_E2E=1 \
  E2E_BASE_URL="$base_url" \
  E2E_HEADLESS=1 \
  E2E_SLOW_MO_MS=0 \
    dotnet test "$REPO_ROOT/BlazorAutoApp.Test/BlazorAutoApp.Test.csproj" \
      --configuration Release --no-build --no-restore \
      --filter "$REACT_DISABLED_BROWSER_FILTER" \
      --logger "trx;LogFileName=react-disabled-browser.trx" \
      --results-directory "$react_disabled_results_dir"
  python3 "$REPO_ROOT/Scripts/CI/validate_dotnet_test_results.py" \
    "$react_disabled_results_dir/react-disabled-browser.trx" \
    --expected-skipped 0 --suite "Packaged React disabled browser journey"

  docker rm -f "$web" >/dev/null
  web="${APP_NAME}-ci-web-disabled-removed-${session}"

  runner_temp="${RUNNER_TEMP:-${TMPDIR:-/tmp}}"
  mkdir -p "$runner_temp"
  fixture_dir="$(mktemp -d "$runner_temp/react-auth-${session}-XXXXXXXX")"
  chmod 0755 "$fixture_dir"
  tls_dir="$fixture_dir/tls"
  app_tls_dir="$fixture_dir/app-tls"
  capture_dir="$fixture_dir/captures"
  mkdir -m 0755 "$tls_dir" "$app_tls_dir"
  mkdir -m 0700 "$capture_dir"

  openssl req -x509 -newkey rsa:2048 -nodes -sha256 -days 2 \
    -keyout "$tls_dir/ca.key" -out "$tls_dir/ca.pem" \
    -subj "/CN=React packaged SMTP test CA" \
    -addext "basicConstraints=critical,CA:TRUE" \
    -addext "keyUsage=critical,keyCertSign,cRLSign" >/dev/null 2>&1
  openssl req -newkey rsa:2048 -nodes -sha256 \
    -keyout "$tls_dir/server.key" -out "$tls_dir/server.csr" \
    -subj "/CN=ci-smtp" >/dev/null 2>&1
  cat > "$tls_dir/server.ext" <<'EOF'
basicConstraints=critical,CA:FALSE
keyUsage=critical,digitalSignature,keyEncipherment
extendedKeyUsage=serverAuth
subjectAltName=DNS:ci-smtp,DNS:localhost,IP:127.0.0.1
EOF
  openssl x509 -req -in "$tls_dir/server.csr" -CA "$tls_dir/ca.pem" \
    -CAkey "$tls_dir/ca.key" -CAcreateserial -out "$tls_dir/server.pem" \
    -days 2 -sha256 -extfile "$tls_dir/server.ext" >/dev/null 2>&1
  fixture_pfx_password="$(openssl rand -hex 32)"
  openssl pkcs12 -export -out "$tls_dir/server.pfx" \
    -inkey "$tls_dir/server.key" -in "$tls_dir/server.pem" \
    -certfile "$tls_dir/ca.pem" -passout "pass:${fixture_pfx_password}" >/dev/null 2>&1
  cp "$tls_dir/server.pfx" "$app_tls_dir/server.pfx"
  cp "$tls_dir/ca.pem" "$app_tls_dir/ca.pem"
  chmod 0444 "$app_tls_dir/server.pfx" "$app_tls_dir/ca.pem"

  smtp_username="fixture-$(openssl rand -hex 8)"
  smtp_password="$(openssl rand -hex 32)"
  smtp_port=2525
  docker run -d --name "$smtp" --network "$network" "${owned_label_args[@]}" \
    --network-alias ci-smtp --user "$(id -u):$(id -g)" --read-only \
    --tmpfs /tmp:rw,size=16777216 \
    -v "$tls_dir:/fixture/tls:ro" -v "$capture_dir:/fixture/captures:rw" \
    -v "$REPO_ROOT/Scripts/Testing/react_smtp_fixture.mjs:/fixture/react_smtp_fixture.mjs:ro" \
    -e "SMTP_FIXTURE_USERNAME=${smtp_username}" \
    -e "SMTP_FIXTURE_PASSWORD=${smtp_password}" \
    "$SMTP_FIXTURE_IMAGE" node /fixture/react_smtp_fixture.mjs \
      --bind 0.0.0.0 --port "$smtp_port" \
      --certificate /fixture/tls/server.pem --key /fixture/tls/server.key \
      --capture-directory /fixture/captures
  smtp_ready() { docker logs "$smtp" 2>&1 | grep -Fxq "READY ${smtp_port}"; }
  wait_until_stable 30 smtp_ready

  react_https_host_port="$(python3 -c 'import socket; s=socket.socket(); s.bind(("127.0.0.1",0)); print(s.getsockname()[1]); s.close()')"
  [[ "$react_https_host_port" =~ ^[0-9]+$ ]] || { echo "Could not allocate a loopback HTTPS port" >&2; exit 1; }
  admin_email="admin-${expected_run_id}-${expected_run_attempt}@example.test"
  account_password="E2E-$(openssl rand -hex 24)-A9!"
  changed_password="E2E-$(openssl rand -hex 24)-B7!"
  admin_password="E2E-$(openssl rand -hex 24)-C5!"
  docker run -d --name "$web_enabled" --network "$network" "${owned_label_args[@]}" \
    -p 127.0.0.1::8080 -p "127.0.0.1:${react_https_host_port}:8443" \
    -v "$app_tls_dir:/run/react-auth-fixture:ro" \
    -e ASPNETCORE_ENVIRONMENT=Docker \
    -e 'ASPNETCORE_URLS=http://+:8080;https://+:8443' \
    -e ASPNETCORE_Kestrel__Certificates__Default__Path=/run/react-auth-fixture/server.pfx \
    -e "ASPNETCORE_Kestrel__Certificates__Default__Password=${fixture_pfx_password}" \
    -e SSL_CERT_FILE=/run/react-auth-fixture/ca.pem \
    -e "APP_VERSION=${APP_VERSION}" \
    -e "App__Name=${APP_NAME}" \
    -e "Accounts__Enabled=true" \
    -e "Accounts__RegistrationEnabled=true" \
    -e "Accounts__PublicOrigin=https://127.0.0.1:${react_https_host_port}" \
    -e Accounts__Email__Host=ci-smtp \
    -e "Accounts__Email__Port=${smtp_port}" \
    -e Accounts__Email__Security=StartTls \
    -e "Accounts__Email__Username=${smtp_username}" \
    -e "Accounts__Email__Password=${smtp_password}" \
    -e Accounts__Email__From=accounts@example.test \
    -e Accounts__Email__MaxAttempts=3 \
    -e TestFixtures__Enabled=true \
    -e TestFixtures__AccountSmtpRootCertificatePath=/run/react-auth-fixture/ca.pem \
    -e Accounts__AdminSeed__Enabled=true \
    -e "Accounts__AdminSeed__Email=${admin_email}" \
    -e "Accounts__AdminSeed__Password=${admin_password}" \
    -e "DataProtection__KeyEncryptionCertificatePath=/run/react-auth-fixture/server.pfx" \
    -e "DataProtection__KeyEncryptionCertificatePassword=${fixture_pfx_password}" \
    -e "ConnectionStrings__DefaultConnection=Host=ci-postgres;Port=5432;Database=app;Username=postgres;Password=${postgres_password};GSS Encryption Mode=Disable" \
    -e Redis__Configuration=ci-redis:6379,abortConnect=false \
    -e Redis__AllowMissing=false \
    -e Database__RunMigrationsAtStartup=true \
    -e RateLimiting__Global__PermitLimit=10000 \
    -e RateLimiting__Api__PermitLimit=1000 \
    -e RateLimiting__Authentication__PermitLimit=1000 \
    -e Accounts__WriteLimit__PermitLimit=1000 \
    -e LocalAccounts__Enabled=false \
    -e Observability__OpenTelemetry__Enabled=false \
    "$IMAGE_REF"

  enabled_base_url="https://127.0.0.1:${react_https_host_port}"
  ready_deadline=$((SECONDS + 180))
  until [[ "$(curl --silent --insecure --output /dev/null --write-out '%{http_code}' --max-time 5 "${enabled_base_url}/health/ready" || true)" == "200" ]]; do
    if (( SECONDS >= ready_deadline )); then
      echo "enabled React app did not report /health/ready within 180 seconds" >&2
      exit 1
    fi
    sleep 2
  done
  echo "enabled React app ready at ${enabled_base_url}"
  enabled_http_port="$(docker port "$web_enabled" 8080/tcp | sed -n 's/.*:\([0-9][0-9]*\)$/\1/p' | head -n 1)"
  [[ -n "$enabled_http_port" ]] || { echo "enabled React app did not publish its loopback HTTP port" >&2; exit 1; }
  cd "$REPO_ROOT"
  pwsh -NoProfile -File "$REPO_ROOT/Scripts/Test-DeployedSite.ps1" \
    -FrontendProfile React -AcceptanceProfile ReactPublicV1 \
    -ForwardedProto https -BaseUrl "http://127.0.0.1:${enabled_http_port}"

  react_enabled_results_dir="$runner_temp/test-results/${expected_run_id}-${expected_run_attempt}/${GITHUB_JOB:-validate}/docker-smoke/React-enabled"
  mkdir -p "$react_enabled_results_dir"
  cd "$REPO_ROOT"
  E2E_CLEANUP_CONNECTION_STRING="Host=127.0.0.1;Port=${postgres_host_port};Database=app;Username=postgres;Password=${postgres_password};GSS Encryption Mode=Disable" \
  E2E_SMTP_CAPTURE_DIR="$capture_dir" \
  E2E_ACCOUNT_PASSWORD="$account_password" \
  E2E_ACCOUNT_CHANGED_PASSWORD="$changed_password" \
  E2E_ADMIN_EMAIL="$admin_email" \
  E2E_ADMIN_PASSWORD="$admin_password" \
  RUN_E2E=1 \
  E2E_BASE_URL="$enabled_base_url" \
  E2E_HEADLESS=1 \
  E2E_SLOW_MO_MS=0 \
    dotnet test "$REPO_ROOT/BlazorAutoApp.Test/BlazorAutoApp.Test.csproj" \
      --configuration Release --no-build --no-restore \
      --filter "$REACT_ENABLED_BROWSER_FILTER" \
      --logger "trx;LogFileName=react-enabled-browser.trx" \
      --results-directory "$react_enabled_results_dir"
  python3 "$REPO_ROOT/Scripts/CI/validate_dotnet_test_results.py" \
    "$react_enabled_results_dir/react-enabled-browser.trx" \
    --expected-skipped 0 --suite "Packaged React enabled account browser journey"
  echo "React packaged disabled/enabled HTTP and browser journeys passed"
else
  home_html="$(curl --fail --silent --show-error --max-time 30 "${forwarded_proto[@]}" "${base_url}/")"
  grep -Fqi '<!DOCTYPE html>' <<< "$home_html" || { echo "home page did not return HTML" >&2; exit 1; }
  grep -Fq '_framework/blazor.web' <<< "$home_html" || { echo "home page does not load the Blazor web script" >&2; exit 1; }
  if docker exec "$web" sh -c 'test ! -e /app/wwwroot/index.html && test ! -e /app/wwwroot/assets'; then
    :
  else
    echo "Blazor image contains inactive React assets" >&2
    exit 1
  fi

  api_headers="$(curl --silent --show-error --max-time 30 "${forwarded_proto[@]}" --dump-header - --output /dev/null "${base_url}/api/books")"
  api_status="$(head -n 1 <<< "$api_headers" | awk '{print $2}')"
  [[ "$api_status" == "401" ]] || { echo "anonymous /api/books returned ${api_status:-no status}, expected 401" >&2; exit 1; }
  if grep -qi '^location:' <<< "$api_headers"; then
    echo "anonymous /api/books redirected instead of returning 401" >&2
    exit 1
  fi
  cd "$REPO_ROOT"
  pwsh -NoProfile -File "$REPO_ROOT/Scripts/Test-DeployedSite.ps1" \
    -FrontendProfile "$FRONTEND_PROFILE" -AcceptanceProfile "$FRONTEND_ACCEPTANCE_PROFILE" \
    -BaseUrl "$base_url"
  echo "Blazor HTTP smoke passed"

  postgres_host_port="$(docker port "$postgres" 5432/tcp | sed -n 's/.*:\([0-9][0-9]*\)$/\1/p' | head -n 1)"
  [[ -n "$postgres_host_port" ]] || { echo "web container did not publish port 5432" >&2; exit 1; }

  cd "$REPO_ROOT"
  pwsh "$REPO_ROOT/BlazorAutoApp.Test/bin/Release/net10.0/playwright.ps1" install chromium
  browser_results_dir="${RUNNER_TEMP:-${TMPDIR:-/tmp}}/test-results/${expected_run_id}-${expected_run_attempt}/${GITHUB_JOB:-validate}/docker-smoke/BlazorAuto"
  mkdir -p "$browser_results_dir"
  cd "$REPO_ROOT"
  E2E_CLEANUP_CONNECTION_STRING="Host=127.0.0.1;Port=${postgres_host_port};Database=app;Username=postgres;Password=${postgres_password};GSS Encryption Mode=Disable" \
  RUN_E2E=1 \
  E2E_BASE_URL="$base_url" \
  E2E_HEADLESS=1 \
  E2E_SLOW_MO_MS=0 \
    dotnet test "$REPO_ROOT/BlazorAutoApp.Test/BlazorAutoApp.Test.csproj" \
      --configuration Release --no-build --no-restore \
      --filter "$BROWSER_SMOKE_FILTER" \
      --logger "trx;LogFileName=blazor-browser-smoke.trx" \
      --results-directory "$browser_results_dir"
  python3 "$REPO_ROOT/Scripts/CI/validate_dotnet_test_results.py" \
    "$browser_results_dir/blazor-browser-smoke.trx" \
    --expected-skipped 0 --suite "Blazor Docker browser smoke"
fi
