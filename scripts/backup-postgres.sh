#!/bin/sh
set -eu

backup_dir="backups"
timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
backup_file="$backup_dir/mosquera-finance-$timestamp.dump"

mkdir -p "$backup_dir"
umask 077

docker compose exec -T db pg_dump \
  --username="$POSTGRES_USER" \
  --format=custom \
  "$POSTGRES_DB" > "$backup_file"

printf 'Backup written to %s\n' "$backup_file"
