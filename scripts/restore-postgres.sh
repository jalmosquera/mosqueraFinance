#!/bin/sh
set -eu

if [ "$#" -ne 1 ] || [ ! -f "$1" ]; then
  printf 'Usage: %s path/to/backup.dump\n' "$0" >&2
  exit 1
fi

docker compose exec -T db pg_restore \
  --username="$POSTGRES_USER" \
  --dbname="$POSTGRES_DB" \
  --clean \
  --if-exists \
  --no-owner \
  --no-privileges < "$1"

printf 'Restore completed from %s\n' "$1"
