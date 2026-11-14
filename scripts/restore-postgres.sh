#!/bin/sh
set -eu

if [ "$#" -ne 1 ] || [ ! -f "$1" ]; then
  printf 'Usage: %s path/to/backup.dump\n' "$0" >&2
  exit 1
fi

: "${POSTGRES_USER:?Set POSTGRES_USER from .env before running this script}"
: "${POSTGRES_DB:?Set POSTGRES_DB from .env before running this script}"

backup_file="$1"

if [ "${RESTORE_CONFIRM:-}" != "RESTORE" ]; then
  printf 'Refusing to replace database %s. Re-run with RESTORE_CONFIRM=RESTORE.\n' \
    "$POSTGRES_DB" >&2
  exit 1
fi

# Verify the custom-format archive before making any database changes.
docker compose exec -T db pg_restore --list < "$backup_file" > /dev/null

docker compose exec -T db pg_restore \
  --username="$POSTGRES_USER" \
  --dbname="$POSTGRES_DB" \
  --clean \
  --exit-on-error \
  --if-exists \
  --no-owner \
  --no-privileges < "$1"

printf 'Restore completed from %s\n' "$backup_file"
