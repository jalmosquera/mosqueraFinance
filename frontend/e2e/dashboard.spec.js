import { expect, test } from "@playwright/test";

import { captureScreenshot, mockApprovedForecastApi, mockEmptyFamilyApi, mockExpenseDashboardApi } from "./support/api";

test("unauthenticated visitors only receive the login screen @e2e @auth @screenshot", async ({ page }, testInfo) => {
  const api = await mockEmptyFamilyApi(page);

  await page.goto("/");

  await expect(page.getByRole("heading", { name: "Tu espacio familiar" })).toBeVisible();
  await expect(page.getByLabel("Usuario")).toBeVisible();
  await expect(page.getByLabel("Contraseña")).toBeVisible();
  await expect(page.getByRole("button", { name: "Iniciar sesión" })).toBeVisible();
  await expect(page.locator(".mf-login-page")).toBeVisible();
  await expect(page.locator(".mf-login-card")).toHaveClass(/mf-card/);
  await expect(page.getByRole("button", { name: "Iniciar sesión" })).toHaveClass(/mf-button/);
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
  await expect(page.locator(".mf-onboarding")).toHaveClass(/mf-card--accent/);
  await expect(page.locator(".app-bottom-navigation")).toHaveClass(/mf-bottom-bar/);
  await captureScreenshot(page, testInfo, "empty-admin-dashboard");
});

test("initial onboarding keeps its final content clear of the fixed navigation on desktop and mobile @e2e @onboarding", async ({ page }) => {
  await mockEmptyFamilyApi(page, { authenticated: true });

  for (const viewport of [{ width: 1280, height: 720 }, { width: 390, height: 844 }]) {
    await page.setViewportSize(viewport);
    await page.goto("/");

    await expect(page.getByRole("heading", { name: "Primero definí el plan, después registrá lo real" })).toBeVisible();
    const [finalNote, bottomNav] = await Promise.all([
      page.locator(".mf-onboarding-note").boundingBox(),
      page.locator(".app-bottom-navigation").boundingBox()
    ]);
    expect(finalNote.y + finalNote.height).toBeLessThanOrEqual(bottomNav.y);
  }
});

test("settings keeps forms and the floating navigation in the shared finance visual system @e2e @settings", async ({ page }) => {
  await mockEmptyFamilyApi(page, { authenticated: true });
  await page.goto("/");
  await page.getByRole("button", { name: "Ajustes" }).click();

  await expect(page.getByRole("heading", { name: "Perfil y familia" })).toBeVisible();
  await expect(page.locator(".mf-chip-list")).toBeVisible();
  await expect(page.locator(".mf-settings .mf-panel")).toHaveCount(1);
  await expect(page.locator(".app-bottom-navigation")).toHaveClass(/mf-bottom-bar/);
  await expect(page.locator(".app-bottom-navigation")).toHaveCSS("border-top-width", "1px");
});

test("an empty non-admin dashboard states its privacy boundary without exposing financial data @e2e @privacy @screenshot", async ({ page }, testInfo) => {
  await mockEmptyFamilyApi(page, { authenticated: true, role: "MEMBER" });

  await page.goto("/");

  await expect(page.getByRole("heading", { name: "La configuración inicial la administra Jalberth" })).toBeVisible();
  await expect(page.getByText("Los ingresos, gastos, ahorros, proyecciones y exportaciones privados de Jalberth no se muestran en tu cuenta.")).toBeVisible();
  await expect(page.getByText("Compartir resumen privado")).not.toBeVisible();
  await captureScreenshot(page, testInfo, "empty-member-dashboard");
});

test("approved admin projection renders Matias values and keeps cards clear of the bottom navigation @e2e @projection", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await mockApprovedForecastApi(page);
  await page.goto("/");
  await page.getByRole("button", { name: "Proyección" }).click();

  await expect(page.getByRole("button", { name: "Proyección" })).toHaveAttribute("aria-current", "page");
  await expect(page.getByRole("heading", { name: "Proyección acumulada anual" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Progreso de ahorro" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Fondo Matías" })).toBeVisible();
  await expect(page.locator(".matias-plan")).toContainText("50,00 €");
  await expect(page.locator(".matias-plan")).toContainText("15,00 € / 30,00 €");
  await expect(page.locator(".recharts-surface")).toBeVisible();
  await expect(page.locator(".recharts-line-curve")).toHaveAttribute("stroke", "#ffb11b");
  await expect(page.locator(".recharts-line-curve")).toHaveAttribute("stroke-width", "4.5");
  const savingsCard = page.locator(".projection-savings");
  const finalCard = page.locator(".free-money-card");
  const bottomNav = page.locator(".projection-bottom-navigation");
  const initialSavingsBox = await savingsCard.boundingBox();
  expect(await page.evaluate(() => window.scrollY)).toBe(0);
  expect(initialSavingsBox.y).toBeGreaterThan(0);
  for (const endCard of [page.locator(".matias-plan"), finalCard]) {
    await endCard.scrollIntoViewIfNeeded();
    const endCardBox = await endCard.boundingBox();
    expect(endCardBox.y + endCardBox.height).toBeLessThanOrEqual((await bottomNav.boundingBox()).y);
  }
});

test("projection keeps the requested responsive dashboard composition @e2e @projection @responsive", async ({ page }, testInfo) => {
  const viewports = [
    { width: 375, height: 812 }, { width: 390, height: 844 }, { width: 393, height: 852 },
    { width: 402, height: 874 }, { width: 430, height: 932 }, { width: 440, height: 956 },
    { width: 768, height: 1024 }, { width: 820, height: 1180 }, { width: 1366, height: 768 },
    { width: 1440, height: 900 }, { width: 1920, height: 1080 }, { width: 3440, height: 1440 },
    { width: 5120, height: 1440 }
  ];

  await mockApprovedForecastApi(page);

  for (const viewport of viewports) {
    await page.setViewportSize(viewport);
    await page.goto("/");
    await page.getByRole("button", { name: "Proyección" }).click();

    await expect(page.getByRole("heading", { name: "Proyección acumulada anual" })).toBeVisible();
    await expect(page.locator(".projection-savings")).toBeVisible();
    await expect(page.locator(".recharts-surface")).toBeVisible();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);

    const isDesktop = viewport.width >= 1024;
    if (isDesktop) {
      await expect(page.locator(".projection-sidebar")).toBeVisible();
      await expect(page.locator(".projection-bottom-navigation")).toBeHidden();
    } else {
      await expect(page.locator(".projection-sidebar")).toBeHidden();
      await expect(page.locator(".projection-bottom-navigation")).toBeVisible();
    }

    if (viewport.width === 390 && viewport.height === 844) {
      const [chartBox, savingsBox, navBox] = await Promise.all([
        page.locator(".projection-chart-card").boundingBox(),
        page.locator(".projection-savings").boundingBox(),
        page.locator(".projection-bottom-navigation").boundingBox()
      ]);
      expect(chartBox.y + chartBox.height).toBeLessThanOrEqual(navBox.y);
      expect(savingsBox.y).toBeGreaterThanOrEqual(navBox.y + navBox.height);
      expect(savingsBox.y - (chartBox.y + chartBox.height)).toBeLessThanOrEqual(navBox.height + 24);
    }

    if (viewport.width === 5120) {
      const [pageBox, chartBox] = await Promise.all([
        page.locator(".projection-page").boundingBox(),
        page.locator(".projection-chart-card").boundingBox()
      ]);
      expect(pageBox.width).toBeGreaterThanOrEqual(3000);
      expect(pageBox.width).toBeLessThanOrEqual(3200);
      expect(chartBox.width).toBeGreaterThanOrEqual(1400);
      expect(chartBox.height).toBeGreaterThanOrEqual(496);
    }

    const finalCard = page.locator(".free-money-card");
    await finalCard.scrollIntoViewIfNeeded();
    const finalBox = await finalCard.boundingBox();
    if (!isDesktop) {
      const navBox = await page.locator(".projection-bottom-navigation").boundingBox();
      expect(finalBox.y + finalBox.height).toBeLessThanOrEqual(navBox.y);
    } else {
      expect(finalBox.y + finalBox.height).toBeLessThanOrEqual(viewport.height);
    }
    await captureScreenshot(page, testInfo, `projection-${viewport.width}x${viewport.height}`);
  }
});

test("desktop projection keeps monthly forecasts before the server-defined distribution @e2e @projection", async ({ page }) => {
  await mockApprovedForecastApi(page, { distribution: { first_owner_percentage: "30.00", second_owner_percentage: "30.00", family_percentage: "40.00" } });
  await page.goto("/");
  await page.getByRole("button", { name: "Proyección" }).click();

  await expect(page.getByRole("heading", { name: "30,00 % / 30,00 % / 40,00 %" })).toBeVisible();
  await expect(page.getByLabel("Distribución autorizada del ahorro")).toHaveText("30,00 %30,00 %40,00 %");
  await expect(page.getByText("Jalberth", { exact: true }).last()).toBeVisible();
  await expect(page.getByText("Raiza", { exact: true }).last()).toBeVisible();
  await expect(page.locator(".distribution-months")).toContainText("233,98 €");
  await expect(page.locator(".distribution-months")).toContainText("467,96 €");
  await expect(page.locator(".projection-month-card").last()).toContainText("935,92 €");
  await expect(page.locator(".later-months")).toHaveCount(0);
  const projectionText = await page.locator(".projection-page").textContent();
  expect(projectionText.indexOf("Ahorro previsto")).toBeLessThan(projectionText.indexOf("Distribución prevista"));
  expect(projectionText.indexOf("Meses 2-12")).toBeLessThan(projectionText.indexOf("Distribución prevista"));
});

test("projection renders savings progress values supplied by the server @e2e @projection", async ({ page }) => {
  await mockApprovedForecastApi(page, {
    personalSavings: [{ owner_id: 1, owner_label: { id: 1, label: "Meta propia QA" }, annual_target: "800.00", real_confirmed_balance: "98.72", progress_percent: "12.34" }],
    familySavings: { label: "Meta común QA", annual_target: "999.00", real_confirmed_balance: "567.20", progress_percent: "56.78" }
  });
  await page.goto("/");
  await page.getByRole("button", { name: "Proyección" }).click();

  await expect(page.getByText("Meta propia QA")).toBeVisible();
  await expect(page.getByText("12,34 %")).toBeVisible();
  await expect(page.getByRole("heading", { name: "Meta común QA" })).toBeVisible();
  await expect(page.getByText("56,78 %")).toBeVisible();
  await expect(page.locator(".saving-progress span").first()).toHaveAttribute("style", "--mf-progress: 12.34%;");
});

test("member projection never exposes Jalberth private forecast values @e2e @projection @privacy", async ({ page }) => {
  await mockApprovedForecastApi(page, { role: "MEMBER" });
  await page.goto("/");
  await page.getByRole("button", { name: "Proyección" }).click();

  await expect(page.getByText("Tu vista privada")).toBeVisible();
  await expect(page.getByText("Proyección acumulada anual")).not.toBeVisible();
  await expect(page.getByText("11.161,04")).not.toBeVisible();
  await expect(page.getByText("25,00")).not.toBeVisible();
});

test("admin expenses dashboard renders the server-authorized rich composition and reloads its month @e2e @expenses", async ({ page }) => {
  const api = await mockExpenseDashboardApi(page);
  await page.goto("/");
  await page.getByRole("button", { name: "Gastos" }).click();

  await expect(page.getByRole("heading", { name: /Gastos de/i })).toBeVisible();
  await expect(page.locator(".expenses-hero").getByText("Previsto, no confirmado")).toBeVisible();
  await expect(page.getByText("Confirmado este mes:")).toBeVisible();
  await expect(page.getByLabel("Uso del presupuesto")).toBeVisible();
  const privateCategory = page.getByText("Jalberth confidential expense");
  await privateCategory.scrollIntoViewIfNeeded();
  await expect(privateCategory).toBeVisible();
  await page.getByLabel("Mes de gastos").fill("2026-10");
  await expect.poll(() => api.requests).toContain("2026-10-01");
});

test("member expenses omit budget and Jalberth privacy sentinels @e2e @expenses @privacy", async ({ page }) => {
  await mockExpenseDashboardApi(page, { role: "MEMBER" });
  await page.goto("/");
  await page.getByRole("button", { name: "Gastos" }).click();

  await expect(page.getByText("Uso del presupuesto")).not.toBeVisible();
  await expect(page.getByText("Jalberth confidential expense")).not.toBeVisible();
  await expect(page.getByText("777,00 €")).not.toBeVisible();
  await expect(page.getByText("You")).toBeVisible();
});

test("expenses actions open the real movement flow and the fixed navigation remains clear @e2e @expenses", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await mockExpenseDashboardApi(page);
  await page.goto("/");
  await page.getByRole("button", { name: "Gastos" }).click();
  await expect(page.getByRole("button", { name: "Gastos" })).toHaveAttribute("aria-current", "page");
  await page.getByRole("button", { name: "Añadir gasto" }).click();
  await expect(page.getByRole("heading", { name: "Gastos confirmados" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Confirmar movimiento" })).toBeVisible();

  await page.getByRole("button", { name: "Gastos" }).click();
  const finalActions = page.locator(".expenses-actions");
  await finalActions.scrollIntoViewIfNeeded();
  const [actionsBox, navBox] = await Promise.all([finalActions.boundingBox(), page.locator(".app-bottom-navigation").boundingBox()]);
  expect(actionsBox.y + actionsBox.height).toBeLessThanOrEqual(navBox.y);
  await page.getByRole("button", { name: "Ver movimientos" }).click();
  await expect(page.getByRole("heading", { name: "Gastos confirmados" })).toBeVisible();
});

test("expenses keeps the black responsive composition clear of the floating navigation @e2e @expenses @screenshot", async ({ page }, testInfo) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await mockExpenseDashboardApi(page);
  await page.goto("/");
  await page.getByRole("button", { name: "Gastos" }).click();

  await expect(page.locator(".expenses-page")).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  await expect(page.locator("main")).toHaveCSS("background-color", "rgb(0, 0, 0)");
  const initialHero = await page.locator(".expenses-hero").boundingBox();
  const nav = page.locator(".expenses-bottom-navigation");
  const navBox = await nav.boundingBox();
  expect(initialHero.y + initialHero.height).toBeLessThanOrEqual(navBox.y);
  const categories = page.locator(".expenses-categories");
  await categories.scrollIntoViewIfNeeded();
  const categoryBox = await categories.boundingBox();
  expect(categoryBox.y + categoryBox.height).toBeLessThanOrEqual((await nav.boundingBox()).y);
  await captureScreenshot(page, testInfo, "expenses-mobile");

  await page.setViewportSize({ width: 1440, height: 960 });
  const expensesPage = await page.locator(".expenses-page").boundingBox();
  expect(expensesPage.width).toBeGreaterThan(900);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  await captureScreenshot(page, testInfo, "expenses-desktop");
});
