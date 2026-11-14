#!/bin/sh
# Validate an already-running Compose stack without starting, stopping, or restoring it.
set -eu

fail() {
  printf 'Runtime validation failed: %s\n' "$1" >&2
  exit 1
}

show_service_diagnostics() {
  service="$1"
  printf '\nCompose status:\n' >&2
  docker compose ps >&2 || true
  printf '\nRecent %s logs:\n' "$service" >&2
  docker compose logs --tail=50 "$service" >&2 || true
}

require_healthy() {
  service="$1"
  if ! container_id="$(docker compose ps -q "$service")"; then
    fail "Compose could not inspect $service. Confirm the required environment is available from .env or the shell, then run 'docker compose config -q'."
  fi

  if [ -z "$container_id" ]; then
    show_service_diagnostics "$service"
    fail "the $service service is not running. Start the configured stack with 'docker compose up -d' before validating it."
  fi

  state="$(docker inspect --format '{{.State.Status}}' "$container_id")"
  health="$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' "$container_id")"
  if [ "$state" != "running" ] || [ "$health" != "healthy" ]; then
    show_service_diagnostics "$service"
    fail "the $service service is state=$state, health=$health; expected state=running and health=healthy."
  fi

  printf 'healthy: %s\n' "$service"
}

if ! command -v docker >/dev/null 2>&1; then
  fail "Docker CLI is not installed. Install Docker and start its daemon, then re-run this script."
fi

if ! docker compose version >/dev/null 2>&1; then
  fail "Docker Compose v2 is unavailable. Install the Docker Compose plugin, then re-run this script."
fi

if ! docker info >/dev/null 2>&1; then
  fail "Docker daemon is unavailable. Start Docker Desktop or the Docker service, confirm 'docker info' succeeds, then re-run this script."
fi

if ! command -v curl >/dev/null 2>&1; then
  fail "curl is not installed. Install curl to validate the published frontend proxy."
fi

require_healthy db
require_healthy backend
require_healthy frontend

if ! frontend_address="$(docker compose port frontend 80)"; then
  fail "Compose could not resolve frontend port 80. Confirm the required environment is available from .env or the shell, then run 'docker compose config -q'."
fi
if [ -z "$frontend_address" ]; then
  fail "frontend has no published port. Check the Compose port mapping and the active Compose project."
fi

if ! curl --fail --silent --show-error --max-time 10 "http://$frontend_address/healthz" >/dev/null; then
  show_service_diagnostics frontend
  fail "the frontend proxy did not return a successful response for /healthz at http://$frontend_address/healthz."
fi
printf 'healthy: frontend proxy at http://%s/healthz\n' "$frontend_address"

temporary_backup="$(mktemp "${TMPDIR:-/tmp}/mosquera-finance-runtime-validation.XXXXXX")"
trap 'rm -f "$temporary_backup"' EXIT HUP INT TERM

if ! docker compose exec -T db sh -c 'pg_dump --username="$POSTGRES_USER" --format=custom "$POSTGRES_DB"' > "$temporary_backup"; then
  show_service_diagnostics db
  fail "could not create a temporary PostgreSQL backup. Check database health, credentials, and pg_dump output above."
fi

if ! docker compose exec -T db pg_restore --list < "$temporary_backup" >/dev/null; then
  fail "the temporary PostgreSQL backup is not a readable restore archive. Investigate pg_dump/pg_restore compatibility."
fi
printf 'validated: temporary PostgreSQL backup is readable by pg_restore (no restore was performed)\n'
