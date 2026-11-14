from decimal import ROUND_HALF_UP, Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q, Sum

from apps.audit.services import record_entity_mutation

from .models import (
    BudgetLine,
    BudgetMonthClose,
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


def _snapshot(forecast):
    return {
        "forecast_id": forecast.pk,
        "month": forecast.month.isoformat(),
        "version": forecast.version,
        "lines": [
            {
                "id": line.pk,
                "name": line.name,
                "amount": str(line.amount),
                "kind": line.kind,
                "replaces_id": line.replaces_id,
            }
            for line in forecast.lines.order_by("pk")
        ],
    }


def require_open_budget_month(*, family, month):
    if BudgetMonthClose.objects.filter(family=family, month=month).exists():
        raise ValidationError("Closed budget months can only be changed through a historical correction.")


@transaction.atomic
def close_budget_month(*, actor, forecast):
    forecast = MonthlyBudgetForecast.objects.select_for_update().get(pk=forecast.pk)
    if BudgetMonthClose.objects.filter(family=forecast.family, month=forecast.month).exists():
        raise ValidationError("This budget month is already closed.")
    latest = (
        MonthlyBudgetForecast.objects.select_for_update()
        .filter(family=forecast.family, month=forecast.month)
        .order_by("-version", "-pk")
        .first()
    )
    if latest.pk != forecast.pk:
        raise ValidationError("Only the latest budget forecast version can be closed.")
    snapshot = _snapshot(forecast)
    close = BudgetMonthClose.objects.create(
        family=forecast.family,
        month=forecast.month,
        forecast=forecast,
        closed_by=actor,
        snapshot=snapshot,
    )
    record_entity_mutation(
        actor=actor,
        action="budget_month.closed",
        family=forecast.family,
        entity_type="budget_month_close",
        entity_id=close.pk,
        metadata={"month": forecast.month.isoformat(), "forecast_id": forecast.pk, "snapshot": snapshot},
    )
    return close


@transaction.atomic
def create_historical_correction(*, actor, forecast, reason, lines):
    forecast = MonthlyBudgetForecast.objects.select_for_update().get(pk=forecast.pk)
    try:
        close = BudgetMonthClose.objects.select_for_update().get(
            family=forecast.family, month=forecast.month
        )
    except BudgetMonthClose.DoesNotExist as error:
        raise ValidationError("Only closed budget months can receive a historical correction.") from error

    latest = (
        MonthlyBudgetForecast.objects.select_for_update()
        .filter(family=forecast.family, month=forecast.month)
        .order_by("-version", "-pk")
        .first()
    )
    if latest.pk != forecast.pk:
        raise ValidationError("Historical corrections must replace the latest budget forecast version.")
    corrected = MonthlyBudgetForecast(
        family=forecast.family,
        month=forecast.month,
        version=latest.version + 1,
    )
    corrected._allow_closed_month_write = True
    corrected.save()
    for line_data in lines:
        line = BudgetLine(forecast=corrected, **line_data)
        line._allow_closed_month_write = True
        line.save()
    snapshot = _snapshot(corrected)
    record_entity_mutation(
        actor=actor,
        action="budget_forecast.historically_corrected",
        family=forecast.family,
        entity_type="budget_forecast",
        entity_id=corrected.pk,
        metadata={
            "reason": reason,
            "closed_month_id": close.pk,
            "replaces_forecast_id": forecast.pk,
            "snapshot": snapshot,
        },
    )
    return corrected
