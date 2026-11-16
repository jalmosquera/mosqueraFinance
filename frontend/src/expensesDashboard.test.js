import { describe, expect, it } from "vitest";

import { categoryIconName, isMemberDashboard } from "./expensesDashboard";

describe("expenses dashboard mapping", () => {
  it("maps category labels to presentation-only Lucide icons", () => {
    expect(categoryIconName("Alimentación")).toBe("ShoppingCart");
    expect(categoryIconName("Servicio no clasificado")).toBe("Ellipsis");
  });

  it("uses the server visibility role without inferring privacy scope", () => {
    expect(isMemberDashboard({ visibility: { role: "MEMBER" } })).toBe(true);
    expect(isMemberDashboard({ visibility: { role: "ADMIN" } })).toBe(false);
  });
});
