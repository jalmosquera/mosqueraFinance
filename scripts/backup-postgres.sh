#!/bin/sh
set -eu

backup_dir="backups"
timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
backup_file="$backup_dir/mosquera-finance-$timestamp.dump"

umask 077
mkdir -p "$backup_dir"

: "${POSTGRES_USER:?Set POSTGRES_USER from .env before running this script}"
: "${POSTGRES_DB:?Set POSTGRES_DB from .env before running this script}"

temporary_file="$(mktemp "$backup_dir/.mosquera-finance-$timestamp.XXXXXX")"
trap 'rm -f "$temporary_file"' EXIT HUP INT TERM

docker compose exec -T db pg_dump \
  --username="$POSTGRES_USER" \
  --format=custom \
  "$POSTGRES_DB" > "$temporary_file"

mv "$temporary_file" "$backup_file"
trap - EXIT HUP INT TERM

printf 'Backup written to %s\n' "$backup_file"
