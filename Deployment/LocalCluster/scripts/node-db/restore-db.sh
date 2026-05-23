#!/usr/bin/env bash
set -euo pipefail

[[ $# -eq 1 ]] || {
  echo "usage: $0 <deploy-root>/backups/<backup-file>.sql.gz" >&2
  exit 1
}

BACKUP="$1"
[[ -f "$BACKUP" ]] || {
  echo "backup file not found: $BACKUP" >&2
  exit 1
}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"
set -a
. ./.env
set +a

gzip -dc "$BACKUP" | docker compose exec -T postgres psql -U "$POSTGRES_USER" "$POSTGRES_DB"
