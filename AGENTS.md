# Mosquera Finance Agent Instructions

## Scope

Mosquera Finance is a private family-finance application. It uses a modular Django monolith, PostgreSQL, React with Vite and JavaScript, Tailwind, and Docker Compose. It must remain free of mandatory paid services.

## Financial Invariants

- Use Decimal for every monetary calculation. Never use binary floating point.
- Initial figures are configurable forecasts, not confirmed financial movements.
- Confirmed movements are never physically deleted. Correct them with audited reversals and replacements.
- Cigarettes are one shared monthly expense of 186.00 EUR, split 93.00 EUR each, and already included in the 1,324.08 EUR budget.
- Projected savings and real savings are different. Only confirmed savings movements change real balances and progress bars.
- The Matias fund is independent from family savings. A replenishment is not a second consumption expense.
- Shared allocations must sum exactly to the movement total.

## Privacy Invariants

- Jalberth is the family administrator.
- Raiza can manage her own private data and authorized shared data.
- Raiza must never receive Jalberth's private income, clients, expenses, savings, totals that reveal them, projections, or exports.
- Backend authorization is mandatory. React visibility is not authorization.
- A private-to-shared owner change requires an explicit privacy-impact confirmation.

## Delivery Rules

- Work on one owned task at a time and report changed files, verification, and risks.
- Do not deploy, publish, push, merge, delete confirmed financial data, or introduce paid services without explicit user approval.
- Do not add financial fixtures containing real movements. Initial forecasts are entered through an administrator-controlled configuration flow.
- Keep agent work isolated. Request orchestration when a task touches another agent's owned area.
