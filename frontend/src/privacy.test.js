import { describe, expect, it } from "vitest";

import "./App.jsx";
import { requiresPrivacyConfirmation } from "./privacy";

describe("privacy confirmation UI helper", () => {
  it("requires explicit confirmation for shared records only", () => {
    expect(requiresPrivacyConfirmation("shared", false)).toBe(true);
    expect(requiresPrivacyConfirmation("shared", true)).toBe(false);
    expect(requiresPrivacyConfirmation("private", false)).toBe(false);
  });
});
