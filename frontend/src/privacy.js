export function requiresPrivacyConfirmation(scope, confirmed) {
  return scope === "shared" && !confirmed;
}
