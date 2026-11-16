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

export async function mockApprovedForecastApi(page, { role = "ADMIN", distribution = { first_owner_percentage: "25.00", second_owner_percentage: "25.00", family_percentage: "50.00" }, personalSavings, familySavings } = {}) {
  const user = { ...testUser, id: role === "ADMIN" ? 1 : 2, username: role === "ADMIN" ? "jalberth" : "raiza" };
  const authorizedDistribution = {
    first_owner: { id: 1, label: "Jalberth" },
    second_owner: { id: 2, label: "Raiza" },
    ...distribution
  };
  const adminForecast = {
    start_month: "2026-01-01", role: "ADMIN", visibility: "ALL_MEMBERS",
    summary: { annual_projected_savings: "11161.04", first_month_projected_savings: "865.92", subsequent_month_projected_savings: "935.92" },
    personal_savings: personalSavings || [
      { owner_id: 1, owner_label: { id: 1, label: "Jalberth" }, annual_target: "1000.00", real_confirmed_balance: "25.00", progress_percent: "2.50", annual_projected_savings: "2790.26" },
      { owner_id: 2, owner_label: { id: 2, label: "Raiza" }, annual_target: "1000.00", real_confirmed_balance: "10.00", progress_percent: "1.00", annual_projected_savings: "2790.26" }
    ],
    family_savings: familySavings || { label: "Ahorro familiar", annual_target: "2000.00", real_confirmed_balance: "30.00", progress_percent: "1.50", annual_projected_savings: "5580.52" },
    distribution: authorizedDistribution,
    chart: Array.from({ length: 12 }, (_, index) => ({ month: `2026-${String(index + 1).padStart(2, "0")}-01`, projected_savings: index ? "935.92" : "865.92", first_owner: { id: 1, label: "Jalberth" }, first_owner_amount: index ? "233.98" : "216.48", second_owner: { id: 2, label: "Raiza" }, second_owner_amount: index ? "233.98" : "216.48", family_amount: index ? "467.96" : "432.96", cumulative_projected_savings: ["865.92", "1801.84", "2737.76", "3673.68", "4609.60", "5545.52", "6481.44", "7417.36", "8353.28", "9289.20", "10225.12", "11161.04"][index] })),
    matias_plan: { target_amount: "500.00", real_confirmed_balance: "0.00", initial_contribution_total: "100.00", initial_contribution_per_parent: "50.00", monthly_simulated_expenditure: "30.00", monthly_replenishment_total: "30.00", monthly_replenishment_per_parent: "15.00" },
    free_money: [{ owner_id: 1, monthly_amounts: Array(12).fill("150.00") }, { owner_id: 2, monthly_amounts: Array(12).fill("150.00") }]
  };
  const memberForecast = {
    start_month: "2026-01-01", role: "MEMBER", visibility: "SELF_AND_SHARED",
    personal_savings: [{ owner_id: 2, owner_label: { id: 2, label: "Raiza" }, annual_target: "1000.00", real_confirmed_balance: "10.00", progress_percent: "1.00" }],
    family_savings: { label: "Ahorro familiar", annual_target: "2000.00", real_confirmed_balance: "30.00", progress_percent: "1.50" },
    distribution: authorizedDistribution, matias_plan: adminForecast.matias_plan,
    free_money: [{ owner_id: 2, monthly_amounts: Array(12).fill("150.00") }]
  };

  await page.route("**/api/v1/**", async (route) => {
    const path = new URL(route.request().url()).pathname;
    const json = (body) => route.fulfill({ contentType: "application/json", body: JSON.stringify(body) });
    if (path.endsWith("/auth/csrf/")) return json({});
    if (path.endsWith("/auth/me/")) return json({ user });
    if (path.endsWith("/families/")) return json([{ id: 1, name: "Familia Mosquera Alves" }]);
    if (path.endsWith("/memberships/")) return json([{ user_id: 1, username: "jalberth", is_active: true, role: "ADMIN" }, { user_id: 2, username: "raiza", is_active: true, role: "MEMBER" }]);
    if (path.endsWith("/approved-forecast/")) return json(role === "ADMIN" ? adminForecast : memberForecast);
    if (path.endsWith("/logical-accounts/")) return json([{ id: 1, name: "Compartida" }]);
    if (path.includes("/families/1/")) return json([]);
    return route.fallback();
  });
}

export async function mockExpenseDashboardApi(page, { role = "ADMIN" } = {}) {
  const user = { ...testUser, id: role === "ADMIN" ? 1 : 2, username: role === "ADMIN" ? "jalberth" : "raiza" };
  const richDashboard = {
    month: "2026-11-01",
    visibility: { role, scope: role === "ADMIN" ? "HOUSEHOLD" : "OWN_AND_SHARED" },
    forecast: { label: "PLANNED_EXPENSES", total: role === "ADMIN" ? "872.99" : "206.00" },
    confirmed: { label: "CONFIRMED_EXPENSES", total: role === "ADMIN" ? "300.00" : "80.00" },
    responsibility: { setup_required: false, items: role === "ADMIN" ? [{ member: "jalberth", amount: "436.50" }, { member: "raiza", amount: "436.49" }] : [{ member: "You", amount: "113.00" }] },
    budget_utilization: role === "ADMIN" ? { source: "MONTHLY_BUDGET_FORECAST", budget_total: "1200.00", confirmed_expense_total: "300.00", percent: "25.00" } : null,
    categories: role === "ADMIN" ? [{ source: "FORECAST", name: "Alimentación", amount: "300.00" }, { source: "BUDGET", name: "Jalberth confidential expense", amount: "777.00" }] : [{ source: "FORECAST", name: "Alimentación", amount: "186.00" }, { source: "FORECAST", name: "Raiza private expense", amount: "20.00" }],
    upcoming_obligations: [{ due_on: "2026-11-20", category: "Alimentación", amount: "186.00", label: "PLANNED_OBLIGATION" }]
  };
  const familyData = { ...emptyDashboardData, accounts: [{ id: 1, name: "Compartida" }], categories: [{ id: 1, name: "Alimentación", kind: "EXPENSE" }] };
  const requests = [];

  await page.route("**/api/v1/**", async (route) => {
    const url = new URL(route.request().url());
    const path = url.pathname;
    const json = (body) => route.fulfill({ contentType: "application/json", body: JSON.stringify(body) });
    if (path.endsWith("/auth/csrf/")) return json({});
    if (path.endsWith("/auth/me/")) return json({ user });
    if (path.endsWith("/families/")) return json([{ id: 1, name: "Familia Mosquera Alves" }]);
    if (path.endsWith("/memberships/")) return json([{ user_id: 1, username: "jalberth", is_active: true, role: "ADMIN" }, { user_id: 2, username: "raiza", is_active: true, role: "MEMBER" }]);
    if (path.endsWith("/expenses/dashboard/")) { requests.push(url.searchParams.get("month")); return json(richDashboard); }
    if (path.endsWith("/matias-fund/")) return json(null);
    if (path.includes("/families/1/")) { const resource = path.split("/").filter(Boolean).at(-1); return json(familyData[resource] || []); }
    return route.fallback();
  });
  return { requests };
}
