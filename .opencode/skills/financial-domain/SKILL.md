---
name: financial-domain
description: Use when changing Mosquera Finance money models, calculations, budgets, allocations, savings, Matias fund, recurrences, or corrections.
---

# Financial Domain

Use Decimal for all monetary values. Quantize only at defined monetary boundaries. Never use float arithmetic.

Before accepting a financial change, verify:

1. The record is a forecast, pending obligation, confirmed movement, or simulation.
2. Confirmed movements are corrected through audited reversal and replacement, not mutation or deletion.
3. Shared allocations sum exactly to the total.
4. Cigarettes are represented once as a 186.00 EUR shared budget item, initially allocated 93.00 EUR to each person.
5. The 126.11 EUR reconciliation line is reduced or replaced when detailed, never duplicated.
6. Real savings movements alone change savings balances and progress bars.
7. Matias fund spending and replenishment are distinct and do not double count consumption.
