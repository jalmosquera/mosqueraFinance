import { afterEach, describe, expect, it, vi } from "vitest";

import { browserPermission, clearLocalReminder, scheduleLocalReminder } from "./notifications";

const originalWindow = globalThis.window;
const originalNavigator = Object.getOwnPropertyDescriptor(globalThis, "navigator");

function setNotificationEnvironment(permission, showNotification = vi.fn()) {
  globalThis.window = {
    clearTimeout: globalThis.clearTimeout,
    setTimeout: globalThis.setTimeout,
    Notification: { permission }
  };
  Object.defineProperty(globalThis, "navigator", {
    configurable: true,
    value: { serviceWorker: { ready: Promise.resolve({ showNotification }) } }
  });
  return showNotification;
}

afterEach(() => {
  clearLocalReminder();
  vi.useRealTimers();

  if (originalWindow === undefined) delete globalThis.window;
  else globalThis.window = originalWindow;

  if (originalNavigator) Object.defineProperty(globalThis, "navigator", originalNavigator);
  else delete globalThis.navigator;
});

describe("local reminder scheduling", () => {
  it("does not schedule a reminder until browser permission is granted", () => {
    vi.useFakeTimers();
    setNotificationEnvironment("denied");

    scheduleLocalReminder("11:00");

    expect(browserPermission()).toBe("denied");
    expect(vi.getTimerCount()).toBe(0);
  });

  it("shows a generic reminder at the next configured time and schedules the following day", async () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2026-11-14T10:30:00"));
    const showNotification = setNotificationEnvironment("granted");

    scheduleLocalReminder("11:00");

    expect(vi.getTimerCount()).toBe(1);
    await vi.advanceTimersByTimeAsync(30 * 60 * 1000);
    expect(showNotification).toHaveBeenCalledWith("Mosquera Finance", {
      title: "Mosquera Finance",
      body: "Tenés un recordatorio pendiente.",
      data: { url: "/" },
      tag: "mosquera-finance-reminder"
    });
    expect(vi.getTimerCount()).toBe(1);
  });
});
