# Deployment Foundation

This repository includes a production-oriented Docker Compose foundation. It is separate from local development: continue using Django with `DJANGO_USE_SQLITE=1` and the Vite development server as before.

## Services

- `frontend`: Nginx serves the Vite build and publishes `${APP_PORT:-8080}`. It proxies same-origin `/api/` requests to Django.
- `backend`: Gunicorn runs Django internally on port 8000. It applies migrations before serving requests.
- `db`: PostgreSQL is reachable only on the Compose network. It has no host port mapping.

All three services have health checks. The Django health check verifies database connectivity at `/healthz`; Nginx exposes that endpoint to make the frontend health check end-to-end.

## Configuration

Copy `.env.example` to `.env`, then replace both secret placeholders with strong, unique values. Set `DJANGO_ALLOWED_HOSTS` to the comma-separated public hostnames before exposing the service.

The stack only serves HTTP itself. Put a TLS-terminating reverse proxy in front of the published frontend port for an Internet-facing deployment. No Cloudflare dependency is assumed.

## Compose Operations

After creating `.env`, start the stack with:

```sh
docker compose up -d
```

Inspect service health with:

```sh
docker compose ps
```

The only published port is the frontend's `APP_PORT`. Do not add a `ports` entry to `db`.

## Backups And Restore

Backups are PostgreSQL custom-format dumps written under the gitignored `backups/` directory. Load the Compose environment first, then run:

```sh
set -a; . ./.env; set +a
./scripts/backup-postgres.sh
```

Test backups periodically on a separate non-production Compose project or host.

Restore replaces database objects and data. Stop the backend first so no request writes during the restore, then run:

```sh
docker compose stop backend
set -a; . ./.env; set +a
./scripts/restore-postgres.sh backups/mosquera-finance-YYYYMMDDTHHMMSSZ.dump
docker compose start backend
```

The scripts intentionally operate only on the `db` service of the current Compose project. Verify the selected `.env`, Compose project, and dump file before restoring.
