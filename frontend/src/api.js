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

export async function bootstrapSession(signal) {
  await api.get("auth/csrf/", { signal });
  const response = await api.get("auth/me/", { signal });
  return response.data.user;
}

export async function login(username, password) {
  const response = await api.post("auth/login/", { username, password });
  return response.data.user;
}

export function logout() {
  return api.post("auth/logout/");
}

export function getMemberships(familyId, signal) {
  return api.get(`families/${familyId}/memberships/`, { signal }).then((response) => response.data);
}

export function createFamilyRecord(familyId, resource, payload) {
  return api.post(`families/${familyId}/${resource}/`, payload).then((response) => response.data);
}

export function updateFamilyRecord(familyId, resource, id, payload) {
  return api.patch(`families/${familyId}/${resource}/${id}/`, payload).then((response) => response.data);
}

export function deleteFamilyRecord(familyId, resource, id) {
  return api.delete(`families/${familyId}/${resource}/${id}/`);
}

export function getPaymentObligations(familyId, month, signal) {
  return api.get(`families/${familyId}/payment-obligations/`, { params: { month }, signal }).then((response) => response.data);
}

export function generatePaymentObligations(familyId, month) {
  return api.post(`families/${familyId}/payment-obligations/generate/`, { month }).then((response) => response.data);
}

export function settlePaymentObligation(familyId, obligationId, allocations) {
  return api.post(`families/${familyId}/payment-obligations/${obligationId}/settle/`, allocations ? { allocations } : {}).then((response) => response.data);
}

export function voidPaymentObligation(familyId, obligationId, reason) {
  return api.post(`families/${familyId}/payment-obligations/${obligationId}/void/`, { reason }).then((response) => response.data);
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
  return error.response?.status === 401 || error.response?.data?.detail === "Authentication credentials were not provided.";
}

export function isForbidden(error) {
  return error.response?.status === 403 || error.response?.status === 404;
}

export function apiErrorMessage(error) {
  if (isForbidden(error)) {
    return "No tenés autorización para ver o modificar esta información.";
  }
  const data = error.response?.data;
  if (typeof data?.detail === "string") {
    return data.detail;
  }
  if (data && typeof data === "object") {
    const message = Object.values(data).flat().find((value) => typeof value === "string");
    if (message) {
      return message;
    }
  }
  return "No se pudo guardar la información. Intentá nuevamente.";
}
