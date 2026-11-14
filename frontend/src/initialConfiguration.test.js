import { describe, expect, it } from "vitest";

import { createInitialConfigurationTemplate } from "./initialConfiguration";

describe("createInitialConfigurationTemplate", () => {
  it("creates the required shared Cigarettes plan for two active members", () => {
    const template = createInitialConfigurationTemplate([{ user_id: 3, is_active: true }, { user_id: 7, is_active: true }]);

    expect(template.expense_forecasts[0]).toMatchObject({ amount: "186.00", is_cigarettes: true, recurrence: "MONTHLY", allocations: [{ member_id: 3, amount: "93.00" }, { member_id: 7, amount: "93.00" }] });
    expect(template.budget.lines).toEqual([{ name: "Cigarettes", amount: "186.00" }]);
  });

  it("requires two active members before producing a configuration", () => {
    expect(createInitialConfigurationTemplate([{ user_id: 3, is_active: true }])).toBeNull();
  });
});
