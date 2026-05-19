#!/usr/bin/env bash
set -euo pipefail

cd /opt/ship
mkdir -p backups
set -a
. ./.env
set +a

BACKUP="backups/predeploy-$(date -u +%Y%m%dT%H%M%SZ).sql.gz"
docker compose exec -T postgres pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB" | gzip > "$BACKUP"
ls -lh "$BACKUP"
