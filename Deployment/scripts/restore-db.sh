#!/usr/bin/env bash
set -euo pipefail

[[ $# -eq 1 ]] || {
  echo "usage: $0 /opt/ship/backups/<backup-file>.sql.gz" >&2
  exit 1
}

BACKUP="$1"
[[ -f "$BACKUP" ]] || {
  echo "backup file not found: $BACKUP" >&2
  exit 1
}

cd /opt/ship
set -a
. ./.env
set +a

gzip -dc "$BACKUP" | docker compose exec -T postgres psql -U "$POSTGRES_USER" "$POSTGRES_DB"
