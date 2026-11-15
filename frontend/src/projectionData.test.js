import { describe, expect, it } from "vitest";
import { getChartData, getProjectionSummary } from "./projectionData";

describe("projection data", () => {
  const months = [
    { month: "2026-01-01", income: "100.00", expenses: "20.00", savings_contribution: "10.00", projected_savings_balance: "60.00" },
    { month: "2026-02-01", income: "100.00", expenses: "20.00", savings_contribution: "10.00", projected_savings_balance: "70.00" }
  ];

  it("keeps real and projected savings separate", () => {
    expect(getProjectionSummary({ months }, [{ target_amount: "100.00", real_balance: "25.00" }])).toMatchObject({
      real: "25.00",
      projected: "70.00",
      projectedContribution: "20.00",
      progress: 70
    });
  });

  it("converts backend decimal strings into chart values", () => {
    expect(getChartData(months)[0]).toMatchObject({ income: 100, expenses: 20, savings: 10, balance: 60 });
  });
});
