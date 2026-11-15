import { formatMonth } from "./formatDate";

function cents(value) {
  const normalized = String(value ?? "");
  const match = normalized.match(/^(-?)(\d+)(?:\.(\d{1,2}))?$/);
  if (!match) return 0n;
  const [, sign, integer, decimal = ""] = match;
  return BigInt(`${sign}${integer}${decimal.padEnd(2, "0")}`);
}

function money(value) {
  const negative = value < 0n;
  const absolute = negative ? -value : value;
  return `${negative ? "-" : ""}${absolute / 100n}.${String(absolute % 100n).padStart(2, "0")}`;
}

// Chart coordinates are visual-only; all financial totals remain exact cents.
function chartValue(value) {
  return Number(cents(value)) / 100;
}

export function getProjectionSummary(projection, savingsGoals) {
  const months = projection?.months || [];
  const lastMonth = months.at(-1);
  const targetCents = savingsGoals.reduce((total, goal) => total + cents(goal.target_amount), 0n);
  const realCents = savingsGoals.reduce((total, goal) => total + cents(goal.real_balance), 0n);
  const projectedCents = cents(lastMonth?.projected_savings_balance);
  const contributionCents = months.reduce((total, month) => total + cents(month.savings_contribution), 0n);

  return {
    months,
    target: money(targetCents),
    real: money(realCents),
    projected: money(projectedCents),
    projectedContribution: money(contributionCents),
    progress: targetCents > 0n ? Math.min(Number((projectedCents * 10000n) / targetCents) / 100, 100) : 0
  };
}

export function getChartData(months) {
  return months.map((month) => ({
    label: formatMonth(month.month.slice(0, 7)).slice(0, 3),
    income: chartValue(month.income),
    expenses: chartValue(month.expenses),
    savings: chartValue(month.savings_contribution),
    balance: chartValue(month.projected_savings_balance)
  }));
}
