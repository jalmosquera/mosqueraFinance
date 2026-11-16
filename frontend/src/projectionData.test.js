import { describe, expect, it } from "vitest";
import { formatMoney } from "./formatMoney";
import { mapApprovedForecast } from "./projectionData";

describe("approved forecast mapping", () => {
  const adminForecast = {
    role: "ADMIN",
    visibility: "ALL_MEMBERS",
    summary: { annual_projected_savings: "11161.04", first_month_projected_savings: "865.92", subsequent_month_projected_savings: "935.92" },
    chart: [{ month: "2026-01-01", projected_savings: "865.92", personal_amount: "216.48", family_amount: "432.96", cumulative_projected_savings: "865.92" }],
    personal_savings: [{ owner_id: 1, owner_label: { id: 1, label: "Jalberth desde servidor" }, annual_target: "1000.00", real_confirmed_balance: "25.00", progress_percent: "2.50", annual_projected_savings: "2790.26" }],
    family_savings: { label: "Compartido desde servidor", annual_target: "2000.00", real_confirmed_balance: "30.00", progress_percent: "1.50", annual_projected_savings: "5580.52" },
    distribution: { first_owner_percentage: "25.00", second_owner_percentage: "25.00", family_percentage: "50.00" },
    matias_plan: { target_amount: "500.00", real_confirmed_balance: "10.00", initial_contribution_total: "100.00", initial_contribution_per_parent: "50.00", monthly_simulated_expenditure: "30.00", monthly_replenishment_total: "30.00", monthly_replenishment_per_parent: "15.00" },
    free_money: [{ owner_id: 1, monthly_amounts: ["150.00"] }]
  };

  it("maps server amounts without recalculating them", () => {
    const projection = mapApprovedForecast(adminForecast, { currentUserId: 1, memberships: [{ user_id: 1, username: "jalberth" }] });

    expect(projection.summary.annual_projected_savings).toBe("11161.04");
    expect(projection.chart[0]).toMatchObject({ label: "ene", cumulative_projected_savings: "865.92" });
    expect(projection.personalSavings[0]).toMatchObject({ label: "Jalberth desde servidor", progress_percent: "2.50" });
    expect(projection.familySavings).toMatchObject({ label: "Compartido desde servidor", real_confirmed_balance: "30.00", progress_percent: "1.50" });
    expect(projection.matiasPlan).toMatchObject({ initialContributionPerParent: "50.00", monthlyReplenishmentPerParent: "15.00" });
  });

  it("keeps a member response limited to self and shared data", () => {
    const projection = mapApprovedForecast({
      role: "MEMBER",
      visibility: "SELF_AND_SHARED",
      personal_savings: [{ owner_id: 2, owner_label: { id: 2, label: "Raiza" }, annual_target: "1000.00", real_confirmed_balance: "0.00", progress_percent: "0.00" }],
      family_savings: { label: "Fondo compartido", annual_target: "2000.00", real_confirmed_balance: "0.00", progress_percent: "0.00" },
      free_money: [{ owner_id: 2, monthly_amounts: ["150.00"] }]
    }, { currentUserId: 2 });

    expect(projection.chart).toEqual([]);
    expect(projection.summary).toBeNull();
    expect(projection.personalSavings).toHaveLength(1);
    expect(projection.personalSavings[0].label).toBe("Raiza");
    expect(projection.familySavings.label).toBe("Fondo compartido");
    expect(projection.freeMoney.monthly_amounts).toEqual(["150.00"]);
  });
});

describe("formatMoney", () => {
  it("formats server decimal strings through es-ES EUR Intl formatting", () => {
    expect(formatMoney("11161.04")).toBe("11.161,04 €");
  });
});
