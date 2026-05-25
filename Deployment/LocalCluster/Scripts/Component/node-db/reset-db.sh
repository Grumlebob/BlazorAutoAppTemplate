#!/usr/bin/env bash
set -euo pipefail

usage() {
  echo "usage: $0 [--skip-backup] --confirm <app-name>/<database-name>" >&2
  exit 1
}

SKIP_BACKUP=false
CONFIRMATION=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --skip-backup)
      SKIP_BACKUP=true
      shift
      ;;
    --confirm)
      [[ $# -ge 2 ]] || usage
      CONFIRMATION="$2"
      shift 2
      ;;
    *)
      usage
      ;;
  esac
done

[[ -n "$CONFIRMATION" ]] || usage

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"
set -a
. ./.env
set +a

EXPECTED_CONFIRMATION="${APP_NAME}/${POSTGRES_DB}"
if [[ "$CONFIRMATION" != "$EXPECTED_CONFIRMATION" ]]; then
  echo "database reset confirmation mismatch" >&2
  echo "expected: $EXPECTED_CONFIRMATION" >&2
  exit 1
fi

for identifier in "$POSTGRES_USER" "$POSTGRES_DB"; do
  if [[ ! "$identifier" =~ ^[A-Za-z_][A-Za-z0-9_]{0,62}$ ]]; then
    echo "refusing to reset database because PostgreSQL identifier is not safe: $identifier" >&2
    exit 1
  fi
done

case "$POSTGRES_DB" in
  postgres | template0 | template1)
    echo "refusing to reset PostgreSQL system database: $POSTGRES_DB" >&2
    exit 1
    ;;
esac

echo "resetting disposable deployment database"
echo "app: $APP_NAME"
echo "database: $POSTGRES_DB"

if [[ "$SKIP_BACKUP" == false ]]; then
  ./backup-db.sh
else
  echo "backup skipped because caller already created one"
fi

docker compose exec -T postgres psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d postgres <<SQL
SELECT pg_terminate_backend(pid)
FROM pg_stat_activity
WHERE datname = '${POSTGRES_DB}'
  AND pid <> pg_backend_pid();
DROP DATABASE IF EXISTS "${POSTGRES_DB}";
CREATE DATABASE "${POSTGRES_DB}" OWNER "${POSTGRES_USER}";
SQL

remaining_tables="$(
  docker compose exec -T postgres psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -tAc \
    "select count(*) from information_schema.tables where table_schema = 'public';"
)"

if [[ "$remaining_tables" != "0" ]]; then
  echo "database reset verification failed: public schema still has $remaining_tables table(s)" >&2
  exit 1
fi

echo "database reset complete"
