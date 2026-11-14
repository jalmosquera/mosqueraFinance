import axios from "axios";

const api = axios.create({
  baseURL: "/api/v1/",
  withCredentials: true,
  xsrfCookieName: "csrftoken",
  xsrfHeaderName: "X-CSRFToken"
});

export function getFamilies(signal) {
  return api.get("families/", { signal }).then((response) => response.data);
}

export async function getFamilyData(familyId, startMonth, signal) {
  const prefix = `families/${familyId}`;
  const matiasFund = api.get(`${prefix}/matias-fund/`, { signal }).catch((error) => {
    if (error.response?.status === 404) {
      return { data: null };
    }
    throw error;
  });

  const [
    accounts,
    categories,
    incomeForecasts,
    incomeMovements,
    expenseForecasts,
    expenseMovements,
    savingsGoals,
    savingsMovements,
    fund,
    projection
  ] = await Promise.all([
    api.get(`${prefix}/logical-accounts/`, { signal }),
    api.get(`${prefix}/categories/`, { signal }),
    api.get(`${prefix}/income-forecasts/`, { signal }),
    api.get(`${prefix}/income-movements/`, { signal }),
    api.get(`${prefix}/expense-forecasts/`, { signal }),
    api.get(`${prefix}/expense-movements/`, { signal }),
    api.get(`${prefix}/savings-goals/`, { signal }),
    api.get(`${prefix}/savings-movements/`, { signal }),
    matiasFund,
    api.post(`${prefix}/projections/scenario/`, { start_month: startMonth }, { signal })
  ]);

  return {
    accounts: accounts.data,
    categories: categories.data,
    incomeForecasts: incomeForecasts.data,
    incomeMovements: incomeMovements.data,
    expenseForecasts: expenseForecasts.data,
    expenseMovements: expenseMovements.data,
    savingsGoals: savingsGoals.data,
    savingsMovements: savingsMovements.data,
    matiasFund: fund.data,
    projection: projection.data
  };
}

export function isUnauthenticated(error) {
  return error.response?.status === 401;
}
