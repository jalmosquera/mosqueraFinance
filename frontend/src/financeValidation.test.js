import { describe, expect, it } from "vitest";

import { hasExactAllocationTotal, toCents } from "./financeValidation";

describe("allocation cent validation", () => {
  it("accepts values that sum exactly in cents", () => {
    expect(hasExactAllocationTotal("186,00", [{ amount: "93.0" }, { amount: "93.00" }])).toBe(true);
  });

  it("rejects fractional-cent precision and rounding differences", () => {
    expect(toCents("1.001")).toBeNull();
    expect(hasExactAllocationTotal("10.00", [{ amount: "3.33" }, { amount: "6.66" }])).toBe(false);
  });
});
