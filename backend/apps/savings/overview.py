from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from django.shortcuts import get_object_or_404
from rest_framework import serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.budgets.models import SavingsDistributionRule
from apps.budgets.services import (
    effective_allowances,
    effective_budget_total,
    latest_budget_for_month,
)
from apps.families.models import Family, FamilyMembership
from apps.incomes.models import IncomeForecast, Recurrence

from .models import MatiasFund, SavingsGoal

CENT = Decimal("0.01")
ZERO = Decimal("0.00")


def _money(value):
    return f"{value.quantize(CENT, rounding=ROUND_HALF_UP):.2f}"


def _add_months(month, count):
    month_index = month.month - 1 + count
    return date(month.year + month_index // 12, month_index % 12 + 1, 1)


def _month_end(month):
    return _add_months(month, 1) - date.resolution


def _applies_in_month(forecast, month):
    if forecast.effective_date > _month_end(month):
        return False
    if forecast.recurrence == Recurrence.MONTHLY:
        return True
    return forecast.occurred_on.year == month.year and forecast.occurred_on.month == month.month


def _progress(balance, target):
    if target <= ZERO:
        return ZERO
    return min(Decimal("100.00"), (balance / target) * 100)


def _goal_payload(goal):
    balance = goal.real_balance
    return {
        "id": goal.pk,
        "name": goal.name,
        "target_amount": _money(goal.target_amount),
        "real_confirmed_balance": _money(balance),
        "progress_percent": _money(_progress(balance, goal.target_amount)),
    }


def _savings_payload(goals, *, user, include_all_owners):
    personal_goals = [goal for goal in goals if goal.owner_id is not None]
    family_goals = [goal for goal in goals if goal.owner_id is None]
    real_total = sum((goal.real_balance for goal in goals), ZERO)
    target_total = sum((goal.target_amount for goal in goals), ZERO)
    personal = []
    for goal in personal_goals:
        payload = _goal_payload(goal)
        payload["owner_id"] = goal.owner_id if include_all_owners else user.pk
        personal.append(payload)
    return {
        "annual_real_confirmed_total": _money(real_total),
        "annual_target": _money(target_total),
        "progress_percent": _money(_progress(real_total, target_total)),
        "personal_goals": personal,
        "family_goals": [_goal_payload(goal) for goal in family_goals],
    }


def _matias_payload(fund, *, include_planning):
    if fund is None:
        return {"configured": False, "real_confirmed_balance": _money(ZERO)}
    balance = fund.real_balance
    payload = {
        "configured": True,
        "target_amount": _money(fund.target_amount),
        "real_confirmed_balance": _money(balance),
        "progress_percent": _money(_progress(balance, fund.target_amount)),
    }
    if include_planning:
        payload.update(
            {
                "initial_contribution_total": _money(fund.initial_contribution_total),
                "initial_contribution_per_parent": _money(fund.initial_contribution_total / 2),
                "monthly_simulated_expenditure": _money(fund.monthly_simulated_expenditure),
                "monthly_replenishment_total": _money(fund.monthly_replenishment_total),
                "monthly_replenishment_per_parent": _money(fund.monthly_replenishment_total / 2),
            }
        )
    return payload


def _planning_requirements(*, family, months, active_member_ids, goals, fund):
    incomes = list(IncomeForecast.objects.filter(family=family))
    missing = {
        "budget_months": [],
        "income_months": [],
        "allowance_months": [],
        "distribution_months": [],
        "goal_types": [],
        "matias_fund": fund is None,
    }
    rules = []
    budgets = []
    for month in months:
        budget = latest_budget_for_month(family=family, month=month)
        if budget is None:
            missing["budget_months"].append(month.isoformat())
        budgets.append(budget)
        if not any(_applies_in_month(income, month) for income in incomes):
            missing["income_months"].append(month.isoformat())
        if set(effective_allowances(family=family, month=month)) != active_member_ids:
            missing["allowance_months"].append(month.isoformat())
        rule = (
            SavingsDistributionRule.objects.filter(family=family, effective_date__lte=month)
            .order_by("-effective_date", "-pk")
            .first()
        )
        if rule is None:
            missing["distribution_months"].append(month.isoformat())
        rules.append(rule)
    if not any(goal.owner_id is not None for goal in goals):
        missing["goal_types"].append("personal")
    if not any(goal.owner_id is None for goal in goals):
        missing["goal_types"].append("family")
    return not any(missing.values()), missing, incomes, budgets, rules


def _contribution_plan(*, months, incomes, budgets, rules, family, fund):
    monthly = []
    for offset, month in enumerate(months):
        income = sum((item.amount for item in incomes if _applies_in_month(item, month)), ZERO)
        allowances = sum(effective_allowances(family=family, month=month).values(), ZERO)
        matias_reserve = fund.initial_contribution_total if offset == 0 else fund.monthly_replenishment_total
        total = income - effective_budget_total(budgets[offset]) - allowances - matias_reserve
        rule = rules[offset]
        first = (total * rule.FIRST_OWNER_PERCENTAGE).quantize(CENT, rounding=ROUND_HALF_UP)
        second = (total * rule.SECOND_OWNER_PERCENTAGE).quantize(CENT, rounding=ROUND_HALF_UP)
        family_amount = (total - first - second).quantize(CENT, rounding=ROUND_HALF_UP)
        monthly.append(
            {
                "month": month.isoformat(),
                "total": _money(total),
                "personal_contributions": [
                    {"owner_id": rule.first_owner_id, "amount": _money(first)},
                    {"owner_id": rule.second_owner_id, "amount": _money(second)},
                ],
                "family_contribution": _money(family_amount),
            }
        )
    return {"first_month": monthly[0], "months_2_to_12": monthly[1:]}


def savings_overview(*, user, family, year, has_household_aggregate_authority):
    """Return persisted real balances and, only for the authority, approved planning."""
    visible_goals = list(SavingsGoal.objects.visible_to(user).filter(family=family))
    is_authority = has_household_aggregate_authority
    response = {
        "year": year,
        "role": "HOUSEHOLD_AGGREGATE_AUTHORITY" if is_authority else "MEMBER",
        "capabilities": {
            "can_manage_private_goals": True,
            "can_record_savings_movements": True,
            "can_manage_shared_goals": is_authority,
            "can_manage_matias_fund": is_authority,
            "can_manage_matias_movements": is_authority,
            "can_view_household_planning": is_authority,
        },
        "savings": _savings_payload(visible_goals, user=user, include_all_owners=is_authority),
    }
    fund = MatiasFund.objects.filter(family=family).first()
    if not is_authority:
        response["matias"] = _matias_payload(fund, include_planning=False)
        return response

    response["matias"] = _matias_payload(fund, include_planning=True)
    months = [_add_months(date(year, 1, 1), offset) for offset in range(12)]
    active_member_ids = set(family.memberships.filter(is_active=True).values_list("user_id", flat=True))
    available, missing, incomes, budgets, rules = _planning_requirements(
        family=family,
        months=months,
        active_member_ids=active_member_ids,
        goals=visible_goals,
        fund=fund,
    )
    response["planning"] = {"available": available, "missing": missing}
    if available:
        response["planning"]["contribution_plan"] = _contribution_plan(
            months=months,
            incomes=incomes,
            budgets=budgets,
            rules=rules,
            family=family,
            fund=fund,
        )
    return response


class SavingsOverviewQuerySerializer(serializers.Serializer):
    year = serializers.IntegerField(min_value=2000, max_value=9999)


class SavingsOverviewView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request, family_pk):
        family = get_object_or_404(Family.objects.visible_to(request.user), pk=family_pk)
        serializer = SavingsOverviewQuerySerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        return Response(
            savings_overview(
                user=request.user,
                family=family,
                year=serializer.validated_data["year"],
                has_household_aggregate_authority=FamilyMembership.objects.household_aggregate_authority_for(
                    request.user, family
                ).exists(),
            ),
            headers={"Cache-Control": "private, no-store"},
        )
