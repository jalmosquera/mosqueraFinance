import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("workbox-precaching", () => ({
  cleanupOutdatedCaches: vi.fn(),
  precacheAndRoute: vi.fn(),
  createHandlerBoundToURL: vi.fn()
}));
vi.mock("workbox-routing", () => ({
  NavigationRoute: vi.fn(),
  registerRoute: vi.fn()
}));

describe("service worker notification clicks", () => {
  let notificationClick;
  let openWindow;

  beforeEach(async () => {
    notificationClick = undefined;
    openWindow = vi.fn();
    globalThis.self = {
      __WB_MANIFEST: [],
      addEventListener: vi.fn((type, listener) => {
        if (type === "notificationclick") notificationClick = listener;
      })
    };
    globalThis.clients = { openWindow };
    vi.resetModules();
    await import("./sw.js");
  });

  it("ignores notification payload URLs and always opens the generic app entry", async () => {
    let work;
    const notification = {
      close: vi.fn(),
      data: { url: "/private-income?amount=12345" }
    };

    notificationClick({
      notification,
      waitUntil: (promise) => {
        work = promise;
      }
    });
    await work;

    expect(notification.close).toHaveBeenCalledOnce();
    expect(openWindow).toHaveBeenCalledWith("/");
  });
});
