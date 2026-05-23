#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"
mkdir -p backups
set -a
. ./.env
set +a

BACKUP="backups/predeploy-$(date -u +%Y%m%dT%H%M%SZ).sql.gz"
docker compose exec -T postgres pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB" | gzip > "$BACKUP"

[[ -s "$BACKUP" ]] || {
  echo "backup file is empty: $BACKUP" >&2
  exit 1
}
gzip -t "$BACKUP"
PREVIEW="$(gzip -dc "$BACKUP" 2>/dev/null | sed -n '1,80p' || true)"
if ! grep -Eq "PostgreSQL database dump|SET " <<< "$PREVIEW"; then
  echo "backup does not look like a plain SQL pg_dump: $BACKUP" >&2
  exit 1
fi

BACKUP_ABSOLUTE="$SCRIPT_DIR/$BACKUP"
ls -lh "$BACKUP"
echo "backup path: $BACKUP_ABSOLUTE"
echo "backup verification ok"
