export function toCents(value) {
  const match = String(value).trim().match(/^(\d+)(?:[,.](\d{1,2}))?$/);
  if (!match) return null;
  return BigInt(match[1]) * 100n + BigInt((match[2] || "").padEnd(2, "0"));
}

export function hasExactAllocationTotal(amount, allocations) {
  const total = toCents(amount);
  return total !== null && allocations.length > 0 && allocations.every((allocation) => toCents(allocation.amount) !== null) && allocations.reduce((sum, allocation) => sum + toCents(allocation.amount), 0n) === total;
}
