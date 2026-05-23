#!/usr/bin/env bash
set -euo pipefail

[[ $# -eq 3 && "$2" == "--confirm" ]] || {
  echo "usage: $0 <deploy-root>/backups/<backup-file>.sql.gz --confirm <app-name>/<database-name>" >&2
  exit 1
}

BACKUP="$1"
CONFIRMATION="$3"
[[ -f "$BACKUP" ]] || {
  echo "backup file not found: $BACKUP" >&2
  exit 1
}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"
set -a
. ./.env
set +a

EXPECTED_CONFIRMATION="${APP_NAME}/${POSTGRES_DB}"
if [[ "$CONFIRMATION" != "$EXPECTED_CONFIRMATION" ]]; then
  echo "restore confirmation mismatch" >&2
  echo "expected: $EXPECTED_CONFIRMATION" >&2
  exit 1
fi

[[ -s "$BACKUP" ]] || {
  echo "backup file is empty: $BACKUP" >&2
  exit 1
}
gzip -t "$BACKUP"

echo "restoring database"
echo "app: $APP_NAME"
echo "database: $POSTGRES_DB"
echo "backup: $BACKUP"
gzip -dc "$BACKUP" | docker compose exec -T postgres psql -U "$POSTGRES_USER" "$POSTGRES_DB"
echo "database restore complete"
