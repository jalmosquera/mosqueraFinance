const GENERIC_REMINDER = {
  title: "Mosquera Finance",
  body: "Tenés un recordatorio pendiente.",
  data: { url: "/" },
  tag: "mosquera-finance-reminder"
};

let reminderTimer;

export function browserPermission() {
  if (!("Notification" in window)) return "unsupported";
  return window.Notification.permission;
}

export function preferencePermission(permission) {
  return permission === "granted" || permission === "denied"
    ? permission.toUpperCase()
    : "DEFAULT";
}

export async function requestBrowserPermission() {
  if (!("Notification" in window)) return "unsupported";
  return window.Notification.requestPermission();
}

async function showReminder() {
  const registration = await navigator.serviceWorker.ready;
  await registration.showNotification(GENERIC_REMINDER.title, GENERIC_REMINDER);
}

export function scheduleLocalReminder(reminderTime) {
  window.clearTimeout(reminderTimer);
  if (!reminderTime || browserPermission() !== "granted") return;

  const [hours, minutes] = reminderTime.split(":").map(Number);
  const next = new Date();
  next.setHours(hours, minutes, 0, 0);
  if (next <= new Date()) next.setDate(next.getDate() + 1);

  reminderTimer = window.setTimeout(async () => {
    await showReminder();
    scheduleLocalReminder(reminderTime);
  }, next.getTime() - Date.now());
}

export function clearLocalReminder() {
  window.clearTimeout(reminderTimer);
}
