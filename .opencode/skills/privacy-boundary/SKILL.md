---
name: privacy-boundary
description: Use when changing Mosquera Finance permissions, API querysets, serializers, projections, charts, exports, or shared ownership.
---

# Privacy Boundary

Backend filtering is mandatory. Every list, detail, graph, projection, export, and mutation must use the requesting family membership and permitted scope before serializing data.

Raiza may access her private data and authorized shared records. She must not receive or infer Jalberth private income, clients, expenses, savings, totals, or derivative projections. A private-to-shared ownership correction must present an explicit impact warning before confirmation.

Never rely on hidden React elements to protect data. Test direct URL and identifier access for IDOR.
