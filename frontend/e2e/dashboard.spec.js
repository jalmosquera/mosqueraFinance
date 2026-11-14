import { expect, test } from "@playwright/test";

import { captureScreenshot, mockEmptyFamilyApi } from "./support/api";

test("unauthenticated visitors only receive the login screen @e2e @auth @screenshot", async ({ page }, testInfo) => {
  const api = await mockEmptyFamilyApi(page);

  await page.goto("/");

  await expect(page.getByRole("heading", { name: "Tu espacio familiar" })).toBeVisible();
  await expect(page.getByLabel("Usuario")).toBeVisible();
  await expect(page.getByLabel("Contraseña")).toBeVisible();
  await expect(page.getByRole("button", { name: "Iniciar sesión" })).toBeVisible();
  expect(api.familyRequestCount()).toBe(0);
  await captureScreenshot(page, testInfo, "login");
});

test("a user can log in to an empty administrator dashboard @e2e @login @screenshot", async ({ page }, testInfo) => {
  await mockEmptyFamilyApi(page);

  await page.goto("/");
  await page.getByLabel("Usuario").fill("qa-user");
  await page.getByLabel("Contraseña").fill("not-a-real-password");
  await page.getByRole("button", { name: "Iniciar sesión" }).click();

  await expect(page.getByRole("heading", { name: "Familia de prueba" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Primero definí el plan, después registrá lo real" })).toBeVisible();
  await expect(page.getByText("Los pronósticos describen importes previstos")).toBeVisible();
  await captureScreenshot(page, testInfo, "empty-admin-dashboard");
});

test("an empty non-admin dashboard states its privacy boundary without exposing financial data @e2e @privacy @screenshot", async ({ page }, testInfo) => {
  await mockEmptyFamilyApi(page, { authenticated: true, role: "MEMBER" });

  await page.goto("/");

  await expect(page.getByRole("heading", { name: "La configuración inicial la administra Jalberth" })).toBeVisible();
  await expect(page.getByText("Los ingresos, gastos, ahorros, proyecciones y exportaciones privados de Jalberth no se muestran en tu cuenta.")).toBeVisible();
  await expect(page.getByText("Compartir resumen privado")).not.toBeVisible();
  await captureScreenshot(page, testInfo, "empty-member-dashboard");
});
