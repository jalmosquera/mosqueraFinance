# Multi-Agent Workflow

## Roles

The seven project agents are real OpenCode subagents registered locally under `.opencode/agents/`. Their instructions are intentionally excluded from Git and are loaded by OpenCode after restart.

| Agent | Owns | Cannot Do |
|---|---|---|
| Architect | architecture, contracts, ADRs | implement product features |
| Backend | Django, DRF, PostgreSQL, services | redefine approved financial rules |
| Frontend | React, UX, PWA, exports | rely on UI-only authorization |
| Finance | invariants, rounding, projections | change data models without review |
| Security | threat review, permissions, audit | approve untested authorization |
| QA | test design, regression verification | mark incomplete work complete |
| DevOps | Compose, HTTPS, backup procedures | deploy or expose services without approval |

## Delegation

1. The orchestrator reads the relevant agent instructions and creates a real subagent task.
2. Architect, Finance, and Security review contracts before implementation begins.
3. Backend and Frontend receive non-overlapping files and API contracts.
4. QA verifies each integrated increment. Security reviews privacy-sensitive changes independently.
5. DevOps works only after runtime contracts are stable.
6. The orchestrator integrates changes and runs cross-cutting verification.

## Required Agent Report

Every delegated task returns:

1. Scope completed.
2. Files changed or reviewed.
3. Validation performed.
4. Financial, privacy, or operational risks.
5. Dependencies or handoff target.

## Conflict Prevention

No two agents edit the same file concurrently. Work is assigned by module and contract. Any change across module boundaries is escalated to Architect and Finance before implementation.

## Approval Gates

Only the user can authorize deployments, public exposure, merges, pushes, destructive operations, or changes to approved financial rules.
