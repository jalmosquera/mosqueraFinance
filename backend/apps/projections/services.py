from datetime import date
from decimal import Decimal

from rest_framework.exceptions import ValidationError

from apps.expenses.models import ExpenseForecast
from apps.incomes.models import IncomeForecast, Recurrence
from apps.savings.models import SavingsGoal

ZERO = Decimal("0.00")


def _money(value):
    return f"{value:.2f}"


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
