import { describe, expect, it } from "vitest";

import { isUnauthenticated } from "./api";

describe("isUnauthenticated", () => {
  it("recognizes HTTP 401 responses", () => {
    expect(isUnauthenticated({ response: { status: 401 } })).toBe(true);
  });

  it("recognizes DRF unauthenticated responses without a status", () => {
    expect(isUnauthenticated({ response: { data: { detail: "Authentication credentials were not provided." } } })).toBe(true);
  });

  it("does not classify forbidden responses as unauthenticated", () => {
    expect(isUnauthenticated({ response: { status: 403 } })).toBe(false);
  });
});
