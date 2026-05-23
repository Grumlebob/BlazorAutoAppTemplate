#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"
mkdir -p backups
set -a
. ./.env
set +a

BACKUP="backups/predeploy-$(date -u +%Y%m%dT%H%M%SZ).sql.gz"
TEMP_BACKUP="${BACKUP}.tmp"
cleanup() {
  rm -f "$TEMP_BACKUP"
}
trap cleanup EXIT

docker compose exec -T postgres pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB" | gzip > "$TEMP_BACKUP"

[[ -s "$TEMP_BACKUP" ]] || {
  echo "backup file is empty: $TEMP_BACKUP" >&2
  exit 1
}
gzip -t "$TEMP_BACKUP"
PREVIEW="$(gzip -dc "$TEMP_BACKUP" 2>/dev/null | sed -n '1,80p' || true)"
if ! grep -Eq "PostgreSQL database dump|SET " <<< "$PREVIEW"; then
  echo "backup does not look like a plain SQL pg_dump: $TEMP_BACKUP" >&2
  exit 1
fi

mv "$TEMP_BACKUP" "$BACKUP"
trap - EXIT
BACKUP_ABSOLUTE="$SCRIPT_DIR/$BACKUP"
ls -lh "$BACKUP"
echo "backup path: $BACKUP_ABSOLUTE"
echo "backup verification ok"
