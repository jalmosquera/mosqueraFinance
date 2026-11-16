from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from rest_framework.exceptions import ValidationError

from apps.budgets.models import SavingsDistributionRule
from apps.budgets.services import (
    effective_allowances,
    effective_budget_total,
    latest_budget_for_month,
)
from apps.expenses.models import ExpenseForecast
from apps.incomes.models import IncomeForecast, Recurrence
from apps.savings.models import MatiasFund, SavingsGoal

ZERO = Decimal("0.00")
CENT = Decimal("0.01")


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


def _amount_changes(changes, identifier):
    return {change[identifier]: change["amount"] for change in changes}


def _ensure_visible_changes(changes, records, identifier, field):
    requested_ids = {change[identifier] for change in changes}
    visible_ids = {record.pk for record in records}
    if not requested_ids.issubset(visible_ids):
        raise ValidationError({field: "Changes can only target records visible to you."})


def project_scenario(*, user, family, start_month, income_changes, expense_changes, savings_changes):
    incomes = list(IncomeForecast.objects.visible_to(user).filter(family=family))
    expenses = list(ExpenseForecast.objects.visible_to(user).filter(family=family))
    savings_goals = list(SavingsGoal.objects.visible_to(user).filter(family=family))

    _ensure_visible_changes(income_changes, incomes, "forecast_id", "income_changes")
    _ensure_visible_changes(expense_changes, expenses, "forecast_id", "expense_changes")
    _ensure_visible_changes(savings_changes, savings_goals, "goal_id", "savings_changes")

    income_amounts = _amount_changes(income_changes, "forecast_id")
    expense_amounts = _amount_changes(expense_changes, "forecast_id")
    savings_overrides = {change["goal_id"]: change for change in savings_changes}
    savings_balances = {
        goal.pk: savings_overrides.get(goal.pk, {}).get("projected_balance", goal.projected_balance)
        for goal in savings_goals
    }

    months = []
    for offset in range(12):
        month = _add_months(start_month, offset)
        income = sum(
            (income_amounts.get(forecast.pk, forecast.amount) for forecast in incomes if _applies_in_month(forecast, month)),
            ZERO,
        )
        expense = sum(
            (expense_amounts.get(forecast.pk, forecast.amount) for forecast in expenses if _applies_in_month(forecast, month)),
            ZERO,
        )
        savings_contribution = sum(
            (
                savings_overrides.get(goal.pk, {}).get(
                    "projected_monthly_contribution", goal.projected_monthly_contribution
                )
                for goal in savings_goals
            ),
            ZERO,
        )
        for goal in savings_goals:
            savings_balances[goal.pk] += savings_overrides.get(goal.pk, {}).get(
                "projected_monthly_contribution", goal.projected_monthly_contribution
            )
        months.append(
            {
                "month": month.isoformat(),
                "income": _money(income),
                "expenses": _money(expense),
                "savings_contribution": _money(savings_contribution),
                "net_after_savings": _money(income - expense - savings_contribution),
                "projected_savings_balance": _money(sum(savings_balances.values(), ZERO)),
            }
        )
    return {"start_month": start_month.isoformat(), "months": months}


def _effective_rule(*, family, month):
    return (
        SavingsDistributionRule.objects.filter(family=family, effective_date__lte=month)
        .order_by("-effective_date", "-pk")
        .first()
    )


def _goal_summary(goals):
    annual_target = sum((goal.target_amount for goal in goals), ZERO)
    real_confirmed_balance = sum((goal.real_balance for goal in goals), ZERO)
    return {
        "annual_target": _money(annual_target),
        "real_confirmed_balance": _money(real_confirmed_balance),
        "progress_percent": _money(
            min(Decimal("100.00"), (real_confirmed_balance / annual_target) * 100)
            if annual_target > ZERO else ZERO
        ),
    }


def _owner_payload(owner):
    return {"id": owner.pk, "label": owner.first_name or owner.username}


def _matias_plan(fund):
    initial_contribution_total = fund.initial_contribution_total if fund else ZERO
    monthly_replenishment_total = fund.monthly_replenishment_total if fund else ZERO
    return {
        "target_amount": _money(fund.target_amount if fund else ZERO),
        "real_confirmed_balance": _money(fund.real_balance if fund else ZERO),
        "initial_contribution_total": _money(initial_contribution_total),
        "initial_contribution_per_parent": _money(initial_contribution_total / 2),
        "monthly_simulated_expenditure": _money(
            fund.monthly_simulated_expenditure if fund else ZERO
        ),
        "monthly_replenishment_total": _money(monthly_replenishment_total),
        "monthly_replenishment_per_parent": _money(monthly_replenishment_total / 2),
    }


def approved_forecast(
    *, user, family, membership, has_household_aggregate_authority, start_month
):
    """Build a read-only forecast from persisted planning inputs, never movements."""
    is_admin = has_household_aggregate_authority
    visible_goals = list(SavingsGoal.objects.visible_to(user).filter(family=family))
    fund = MatiasFund.objects.filter(family=family).first()
    missing_months = [
        _add_months(start_month, offset).isoformat()
        for offset in range(12)
        if latest_budget_for_month(family=family, month=_add_months(start_month, offset)) is None
    ]
    if missing_months:
        raise ValidationError({"missing_budget_months": missing_months})

    personal_goals = [goal for goal in visible_goals if goal.owner_id == user.pk]
    shared_goals = [goal for goal in visible_goals if goal.owner_id is None]
    if not is_admin:
        return {
            "start_month": start_month.isoformat(),
            "role": "MEMBER",
            "visibility": "SELF_AND_SHARED",
            "personal_savings": [
                {
                    "owner_id": user.pk,
                    "owner_label": _owner_payload(user)["label"],
                    **_goal_summary(personal_goals),
                }
            ],
            "family_savings": {"label": "Family", **_goal_summary(shared_goals)},
            "matias_plan": _matias_plan(fund),
            "free_money": [
                {
                    "owner_id": user.pk,
                    "monthly_amounts": [
                        _money(effective_allowances(family=family, month=_add_months(start_month, offset)).get(user.pk, ZERO))
                        for offset in range(12)
                    ],
                }
            ],
        }

    incomes = list(IncomeForecast.objects.filter(family=family))
    active_members_by_id = {
        member.user_id: member.user
        for member in family.memberships.filter(is_active=True).select_related("user")
    }
    authorized_owner_ids = list(active_members_by_id)
    monthly = []
    owner_savings = {}
    family_savings = ZERO
    annual_savings = ZERO
    cumulative_savings = ZERO
    allowance_series = {owner_id: [] for owner_id in authorized_owner_ids}
    for offset in range(12):
        month = _add_months(start_month, offset)
        rule = _effective_rule(family=family, month=month)
        if rule is None:
            raise ValidationError({"missing_distribution_months": [month.isoformat()]})
        income = sum((forecast.amount for forecast in incomes if _applies_in_month(forecast, month)), ZERO)
        budget_total = effective_budget_total(latest_budget_for_month(family=family, month=month))
        allowances = effective_allowances(family=family, month=month)
        for owner_id in authorized_owner_ids:
            allowance_series[owner_id].append(_money(allowances.get(owner_id, ZERO)))
        allowance_total = sum(allowances.values(), ZERO)
        matias_contribution = (
            fund.initial_contribution_total if fund and offset == 0 else
            fund.monthly_replenishment_total if fund else ZERO
        )
        available = income - budget_total - allowance_total - matias_contribution
        first = (available * rule.FIRST_OWNER_PERCENTAGE).quantize(CENT, rounding=ROUND_HALF_UP)
        second = (available * rule.SECOND_OWNER_PERCENTAGE).quantize(CENT, rounding=ROUND_HALF_UP)
        family_amount = (available - first - second).quantize(CENT, rounding=ROUND_HALF_UP)
        owner_savings[rule.first_owner_id] = owner_savings.get(rule.first_owner_id, ZERO) + first
        owner_savings[rule.second_owner_id] = owner_savings.get(rule.second_owner_id, ZERO) + second
        family_savings += family_amount
        annual_savings += available
        cumulative_savings += available
        monthly.append(
            {
                "month": month.isoformat(),
                "projected_savings": _money(available),
                "first_owner": _owner_payload(active_members_by_id[rule.first_owner_id]),
                "first_owner_amount": _money(first),
                "second_owner": _owner_payload(active_members_by_id[rule.second_owner_id]),
                "second_owner_amount": _money(second),
                "personal_amount": _money(
                    (first if rule.first_owner_id == user.pk else ZERO)
                    + (second if rule.second_owner_id == user.pk else ZERO)
                ),
                "family_amount": _money(family_amount),
                "cumulative_projected_savings": _money(cumulative_savings),
            }
        )

    personal_goals_by_owner = {}
    for goal in visible_goals:
        if goal.owner_id is not None:
            personal_goals_by_owner.setdefault(goal.owner_id, []).append(goal)
    personal = [
        {
            "owner_id": owner_id,
            "owner_label": _owner_payload(goals[0].owner)["label"],
            **_goal_summary(goals),
            "annual_projected_savings": _money(owner_savings.get(owner_id, ZERO)),
        }
        for owner_id, goals in personal_goals_by_owner.items()
    ]
    if is_admin:
        existing_owner_ids = {card["owner_id"] for card in personal}
        personal.extend(
            {
                "owner_id": owner_id,
                "owner_label": _owner_payload(active_members_by_id[owner_id])["label"],
                "annual_target": _money(ZERO),
                "real_confirmed_balance": _money(ZERO),
                "progress_percent": _money(ZERO),
                "annual_projected_savings": _money(owner_savings.get(owner_id, ZERO)),
            }
            for owner_id in owner_savings
            if owner_id not in existing_owner_ids
        )
    response = {
        "start_month": start_month.isoformat(),
        "role": "ADMIN",
        "visibility": "ALL_MEMBERS",
        "personal_savings": personal,
        "family_savings": {
            "label": "Family",
            **_goal_summary(shared_goals),
            "annual_projected_savings": _money(family_savings),
        },
        "distribution": {
            "first_owner_percentage": _money(SavingsDistributionRule.FIRST_OWNER_PERCENTAGE * 100),
            "second_owner_percentage": _money(SavingsDistributionRule.SECOND_OWNER_PERCENTAGE * 100),
            "family_percentage": _money(SavingsDistributionRule.FAMILY_PERCENTAGE * 100),
            "first_owner": monthly[0]["first_owner"],
            "second_owner": monthly[0]["second_owner"],
        },
        "matias_plan": _matias_plan(fund),
        "free_money": [
            {"owner_id": owner_id, "monthly_amounts": amounts}
            for owner_id, amounts in allowance_series.items()
        ],
        "chart": monthly,
    }
    if is_admin:
        response["summary"] = {
            "annual_projected_savings": _money(annual_savings),
            "first_month_projected_savings": monthly[0]["projected_savings"],
            "subsequent_month_projected_savings": monthly[1]["projected_savings"],
        }
    return response
