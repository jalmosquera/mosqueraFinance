import { formatMonth } from "./formatDate";

function memberName(ownerId, memberships, currentUserId, role) {
  if (role === "MEMBER" && ownerId === currentUserId) return "Tu ahorro personal";
  const username = memberships.find((membership) => membership.user_id === ownerId)?.username;
  return username ? `${username[0].toUpperCase()}${username.slice(1)}` : "Ahorro personal";
}

export function mapApprovedForecast(forecast, { currentUserId, memberships = [] } = {}) {
  if (!forecast) return null;

  const personalSavings = (forecast.personal_savings || []).map((saving) => ({
    ...saving,
    label: saving.owner_label?.label || memberName(saving.owner_id, memberships, currentUserId, forecast.role)
  }));
  const chart = (forecast.chart || []).map((month) => ({
    ...month,
    label: formatMonth(month.month.slice(0, 7)).slice(0, 3)
  }));
  const freeMoney = (forecast.free_money || []).find((allowance) => allowance.owner_id === currentUserId) || null;

  return {
    role: forecast.role,
    visibility: forecast.visibility,
    summary: forecast.summary || null,
    chart,
    personalSavings,
    familySavings: forecast.family_savings ? { ...forecast.family_savings, label: forecast.family_savings.label || "Ahorro familiar" } : null,
    distribution: forecast.distribution || null,
    matiasPlan: forecast.matias_plan ? {
      ...forecast.matias_plan,
      initialContributionPerParent: forecast.matias_plan.initial_contribution_per_parent,
      monthlyReplenishmentPerParent: forecast.matias_plan.monthly_replenishment_per_parent
    } : null,
    freeMoney
  };
}
