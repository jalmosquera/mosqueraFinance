# Approved Architecture

## Implementation Status

The backend provides the custom user model, family memberships, authenticated family endpoints, server-enforced family scoping, immutable audit logs, and private/shared logical accounts and categories. Financial movements, budgets, savings, projections, frontend, and deployment infrastructure remain pending.

## System

Mosquera Finance is a modular Django monolith backed by PostgreSQL. A React/Vite PWA communicates with Django REST Framework through a same-origin, versioned REST API. A reverse proxy terminates HTTPS in deployment. PostgreSQL is private to the Docker network.

## Domain Boundaries

- `accounts`: authentication and user profile.
- `families`: family membership and roles.
- `finance`: Decimal money types, transactional invariants, and correction workflows.
- `incomes`: configurable forecasts, recurrences, occurrences, and real income movements.
- `expenses`: configurable forecasts, obligations, real expenses, categories, and allocations.
- `budgets`: versioned monthly budget snapshots and reconciliation lines.
- `savings`: goals, contributions, and confirmed savings movements.
- `matias_fund`: independent target fund, spending, and replenishment.
- `projections`: twelve-month read-only scenarios.
- `audit`: immutable business audit records.

## Temporal Rules

Recurring forecasts are versioned by effective date. A single occurrence can be overridden without changing its recurrence. Confirmed movements are corrected through a linked reversal and replacement in one database transaction. Closed budget months remain historical unless an explicit, audited correction is made.

## Authorization

Jalberth administers authorized family data. Raiza manages her own private data and authorized shared expenses, but cannot query or infer any private Jalberth data. The backend filters querysets before retrieving objects and enforces object-level checks for writes, projections, exports, and graphs.

## Initial Forecasts

Initial figures are configured in the database by an administrator after explicit confirmation. They are not hardcoded as confirmed income, paid expense, or saved money.
