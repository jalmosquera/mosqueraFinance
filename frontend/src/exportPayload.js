const PRIVATE_COLLECTIONS = [
  "accounts",
  "categories",
  "incomeForecasts",
  "incomeMovements",
  "expenseForecasts",
  "expenseMovements",
  "savingsGoals"
];

function isRecipient(username, recipient) {
  return username.trim().toLocaleLowerCase() === recipient.toLocaleLowerCase();
}

function visibleRecords(records, includePrivate, userId) {
  return records.filter((record) => includePrivate || String(record.owner_id) !== String(userId));
}

/**
 * Keeps a recipient card limited to shared data unless that recipient is the
 * authenticated user. This prevents a card from crossing private ownership.
 */
export function createExportPayload(data, sessionUser, recipient) {
  const includePrivate = isRecipient(sessionUser.username, recipient);
  const payload = { recipient, matiasFund: data.matiasFund };

  for (const collection of PRIVATE_COLLECTIONS) {
    payload[collection] = visibleRecords(data[collection] || [], includePrivate, sessionUser.id);
  }

  const visibleGoalIds = new Set(payload.savingsGoals.map((goal) => goal.id));
  payload.savingsMovements = (data.savingsMovements || []).filter((movement) => visibleGoalIds.has(movement.goal_id));

  // A projection is an aggregate and cannot be safely decomposed client-side.
  payload.projection = includePrivate ? data.projection : null;
  return payload;
}
