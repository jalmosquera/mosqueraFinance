function firstDayOfCurrentMonth() {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-01`;
}

export function createInitialConfigurationTemplate(memberships) {
  const activeMemberIds = memberships
    .filter((membership) => membership.is_active)
    .map((membership) => membership.user_id);

  if (activeMemberIds.length < 2) return null;

  const month = firstDayOfCurrentMonth();
  return {
    accounts: [{ key: "shared-account", name: "Cuenta compartida", owner_id: null }],
    categories: [{ key: "cigarettes", name: "Cigarettes", kind: "EXPENSE", owner_id: null }],
    income_forecasts: [],
    expense_forecasts: [{ account_key: "shared-account", category_key: "cigarettes", amount: "186.00", occurred_on: month, effective_date: month, recurrence: "MONTHLY", description: "Cigarettes", is_cigarettes: true, allocations: activeMemberIds.slice(0, 2).map((member_id) => ({ member_id, amount: "93.00" })) }],
    budget: { month, lines: [{ name: "Cigarettes", amount: "186.00" }] },
    privacy_impact_confirmed: false
  };
}
