# Deployment Foundation

This repository includes a production-oriented Docker Compose foundation. It is separate from local development: continue using Django with `DJANGO_USE_SQLITE=1` and the Vite development server as before.

## Services

- `frontend`: Nginx serves the Vite build on `127.0.0.1:${APP_PORT:-8080}`. It proxies same-origin `/api/` requests to Django.
- `backend`: Gunicorn runs Django internally on port 8000. It applies migrations before serving requests.
- `db`: PostgreSQL is reachable only on the Compose network. It has no host port mapping.

All three services have health checks. The Django health check verifies database connectivity at `/healthz`; Nginx exposes that endpoint to make the frontend health check end-to-end.

## Configuration

Copy `.env.example` to `.env`, then replace both secret placeholders with strong, unique values. Set `DJANGO_ALLOWED_HOSTS` to the comma-separated public hostnames before exposing the service. Do not quote values unless the shell syntax requires it.

The stack only listens on loopback and does not terminate TLS. Put a TLS-terminating reverse proxy in front of the published frontend port for an Internet-facing deployment. The proxy must set `X-Forwarded-Proto: https`; the internal Nginx proxy preserves that header so Django can enforce HTTPS redirects and secure cookies. No Cloudflare dependency is assumed.

Production enables secure session and CSRF cookies, HTTPS redirects, HSTS, content-type sniffing protection, and a same-origin referrer policy. Do not bypass the TLS proxy: direct HTTP access will be redirected and cannot authenticate with secure cookies.

## Compose Operations

After creating `.env`, start the stack with:

```sh
docker compose up -d
```

Inspect service health with:

```sh
docker compose ps
```

Run the non-destructive runtime validation after the stack is healthy:

```sh
./scripts/validate-runtime.sh
```

The check never builds, starts, stops, restarts, restores, or deletes a service or database. It verifies that `db`, `backend`, and `frontend` are Docker-healthy, requests `/healthz` through the published Nginx proxy, creates a temporary custom-format dump, and verifies its restore catalog with `pg_restore --list`. The temporary dump is removed when the command exits. If Docker, Compose, the daemon, a service, or the proxy is unavailable, it exits non-zero with the relevant status and recent service logs.

Runtime validation checklist:

- Confirm `docker info` succeeds and the intended Compose project is already running.
- Run `./scripts/validate-runtime.sh` from the repository root.
- Investigate any reported service logs before attempting a deployment or restore.
- Test an actual restore only on a separate non-production Compose project or host, using the documented explicit confirmation.

The only published port is the frontend's loopback `APP_PORT`. Do not add a `ports` entry to `db` or bind the frontend to all interfaces; the TLS proxy should be the only Internet-facing component.

## Backups And Restore

Backups are PostgreSQL custom-format dumps written under the gitignored `backups/` directory. The directory and dumps are owner-only. The script writes to a temporary file first, so a failed dump never appears as a completed backup. Load the Compose environment first, then run:

```sh
set -a; . ./.env; set +a
./scripts/backup-postgres.sh
```

Test backups periodically on a separate non-production Compose project or host.

Restore replaces database objects and data. Stop the backend first so no request writes during the restore. The script validates that the selected file is a PostgreSQL archive before it performs destructive work, then requires an explicit confirmation. Run:

```sh
docker compose stop backend
set -a; . ./.env; set +a
RESTORE_CONFIRM=RESTORE ./scripts/restore-postgres.sh backups/mosquera-finance-YYYYMMDDTHHMMSSZ.dump
docker compose start backend
```

The scripts intentionally operate only on the `db` service of the current Compose project. Verify the selected `.env`, Compose project, and dump file before restoring.
