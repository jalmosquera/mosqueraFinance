import { describe, expect, it } from "vitest";

import { createExportPayload } from "./exportPayload";

const data = {
  accounts: [{ id: 1, owner_id: null }, { id: 2, owner_id: 9 }],
  categories: [{ id: 1, owner_id: null }, { id: 2, owner_id: 9 }],
  incomeForecasts: [{ id: 1, owner_id: null }, { id: 2, owner_id: 9 }],
  incomeMovements: [{ id: 1, owner_id: null }, { id: 2, owner_id: 9 }],
  expenseForecasts: [{ id: 1, owner_id: null }, { id: 2, owner_id: 9 }],
  expenseMovements: [{ id: 1, owner_id: null }, { id: 2, owner_id: 9 }],
  savingsGoals: [{ id: 1, owner_id: null }, { id: 2, owner_id: 9 }],
  savingsMovements: [{ id: 1, goal_id: 1 }, { id: 2, goal_id: 2 }],
  matiasFund: { id: 1 },
  projection: { private_total: "100.00" }
};

describe("createExportPayload", () => {
  it("does not export the authenticated user's private records to another recipient", () => {
    const payload = createExportPayload(data, { id: 9, username: "Jalberth" }, "Raiza");

    expect(payload.accounts).toEqual([{ id: 1, owner_id: null }]);
    expect(payload.savingsGoals).toEqual([{ id: 1, owner_id: null }]);
    expect(payload.savingsMovements).toEqual([{ id: 1, goal_id: 1 }]);
    expect(payload.projection).toBeNull();
  });

  it("allows a recipient to receive their own private records case-insensitively", () => {
    const payload = createExportPayload(data, { id: 9, username: "Jalberth" }, "jalberth");

    expect(payload.incomeMovements).toHaveLength(2);
    expect(payload.projection).toEqual(data.projection);
  });
});
