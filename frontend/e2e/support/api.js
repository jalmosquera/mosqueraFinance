const testUser = {
  id: 1,
  username: "qa-user",
  email: "",
  first_name: "",
  last_name: ""
};

const emptyDashboardData = {
  accounts: [],
  categories: [],
  incomeForecasts: [],
  incomeMovements: [],
  expenseForecasts: [],
  expenseMovements: [],
  savingsGoals: [],
  savingsMovements: [],
  matiasFund: null,
  matiasFundMovements: [],
  projection: { months: [] }
};

export async function mockEmptyFamilyApi(page, { authenticated = false, role = "ADMIN" } = {}) {
  let hasSession = authenticated;
  let familyRequests = 0;

  await page.route("**/api/v1/**", async (route) => {
    const path = new URL(route.request().url()).pathname;
    const json = (body, status = 200) => route.fulfill({
      status,
      contentType: "application/json",
      body: JSON.stringify(body)
    });

    if (path.endsWith("/auth/csrf/")) {
      return json({ detail: "CSRF cookie set." });
    }
    if (path.endsWith("/auth/me/")) {
      return hasSession ? json({ user: testUser }) : json({ detail: "Authentication required." }, 401);
    }
    if (path.endsWith("/auth/login/")) {
      hasSession = true;
      return json({ user: testUser });
    }
    if (path.endsWith("/families/")) {
      familyRequests += 1;
      return json([{ id: 1, name: "Familia de prueba" }]);
    }
    if (path.endsWith("/families/1/memberships/")) {
      return json([{ user_id: testUser.id, is_active: true, role }]);
    }
    if (path.endsWith("/projections/scenario/")) {
      return json(emptyDashboardData.projection);
    }
    if (path.endsWith("/matias-fund/")) {
      return json(emptyDashboardData.matiasFund);
    }
    if (path.includes("/families/1/")) {
      const resource = path.split("/").filter(Boolean).at(-1);
      return json(emptyDashboardData[resource] || []);
    }

    return route.fallback();
  });

  return {
    familyRequestCount: () => familyRequests
  };
}

export async function captureScreenshot(page, testInfo, name) {
  if (process.env.CAPTURE_SCREENSHOTS) {
    const path = testInfo.outputPath(`${name}.png`);
    await page.screenshot({ path, fullPage: true });
    await testInfo.attach(name, { path, contentType: "image/png" });
  }
}
