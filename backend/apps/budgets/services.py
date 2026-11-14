from decimal import ROUND_HALF_UP, Decimal

from django.db.models import Q, Sum

from .models import (
    BudgetLine,
    FreeMoneyAllowance,
    MonthlyBudgetForecast,
    SavingsDistributionRule,
)

ZERO = Decimal("0.00")
CENT = Decimal("0.01")


def _money(value):
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


def latest_budget_for_month(*, family, month):
    return MonthlyBudgetForecast.objects.filter(family=family, month=month).order_by("-version", "-pk").first()


def effective_budget_total(forecast):
    if forecast is None:
        return ZERO
    return BudgetLine.objects.filter(forecast=forecast).filter(
        Q(kind=BudgetLine.Kind.STANDARD) | Q(kind=BudgetLine.Kind.RECONCILIATION, replaced_by__isnull=True)
    ).aggregate(total=Sum("amount"))["total"] or ZERO


def effective_allowances(*, family, month):
    allowances = {}
    for allowance in FreeMoneyAllowance.objects.filter(family=family, effective_date__lte=month).order_by("owner_id", "-effective_date", "-pk"):
        allowances.setdefault(allowance.owner_id, allowance.amount)
    return allowances


def distribution_for_month(*, family, month, available_savings):
    rule = SavingsDistributionRule.objects.filter(family=family, effective_date__lte=month).order_by("-effective_date", "-pk").first()
    if rule is None:
        return None
    first = _money(available_savings * rule.FIRST_OWNER_PERCENTAGE)
    second = _money(available_savings * rule.SECOND_OWNER_PERCENTAGE)
    return {
        "rule_id": rule.pk,
        "first_owner_id": rule.first_owner_id,
        "first_owner_amount": first,
        "second_owner_id": rule.second_owner_id,
        "second_owner_amount": second,
        # Assign any cent-rounding remainder to the 50% Matias allocation.
        "matias_amount": _money(available_savings - first - second),
    }


def calculate_projected_savings(*, family, month, projected_income):
    forecast = latest_budget_for_month(family=family, month=month)
    budget_total = effective_budget_total(forecast)
    allowances = effective_allowances(family=family, month=month)
    allowance_total = sum(allowances.values(), ZERO)
    available_savings = _money(projected_income - budget_total - allowance_total)
    return {
        "forecast_id": forecast.pk if forecast else None,
        "budget_total": _money(budget_total),
        "allowance_total": _money(allowance_total),
        "available_projected_savings": available_savings,
        "distribution": distribution_for_month(family=family, month=month, available_savings=available_savings),
    }
