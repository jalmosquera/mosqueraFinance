# Mosquera Finance

Private family-finance application for the Mosquera Alves family.

## Status

The repository structure and OpenCode multi-agent configuration are present. The backend provides users, family memberships, authorization boundaries, immutable audit logs, private/shared logical accounts, and categories. Financial movements and frontend functionality remain pending.

## Documentation

- `docs/architecture.md`: approved technical architecture and invariants.
- `docs/agent-workflow.md`: orchestration, agent boundaries, and integration workflow.
- `docs/deployment.md`: Docker Compose deployment foundation, configuration, and database recovery procedures.
- `.opencode/agents/`: local, ignored configuration for the seven specialized OpenCode subagents.
- `.opencode/skills/`: reusable project skills.

## Running The Compose Stack

Docker Compose is production-oriented and requires a TLS-terminating reverse proxy. Copy `.env.example` to `.env`, set strong database and Django secrets, and set `DJANGO_ALLOWED_HOSTS` to the public hostnames. Then start it with:

```sh
docker compose up -d
docker compose ps
```

The frontend binds only to `127.0.0.1:${APP_PORT:-8080}`; route public HTTPS traffic through a reverse proxy that sets `X-Forwarded-Proto: https`. See `docs/deployment.md` for health checks, backup, and restore procedures.
