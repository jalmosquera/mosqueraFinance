import calendar
from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.audit.services import record_entity_mutation
from apps.expenses.models import (
    ExpenseForecast,
    ExpenseForecastAllocation,
)
from apps.expenses.services import create_expense_movement
from apps.incomes.models import IncomeForecast, IncomeMovement, Recurrence

from .models import ObligationStatus, PaymentObligation


def _month_start(value):
    return value.replace(day=1)


def _next_month(month):
    return date(month.year + (month.month == 12), month.month % 12 + 1, 1)


def _due_date(forecast, month):
    return month.replace(day=min(forecast.occurred_on.day, calendar.monthrange(month.year, month.month)[1]))


def _allocation_snapshot(forecast):
    if not isinstance(forecast, ExpenseForecast):
        return []
    return [
        {"member_id": allocation.member_id, "amount": str(allocation.amount)}
        for allocation in ExpenseForecastAllocation.objects.filter(forecast=forecast)
    ]


def _create_obligation(forecast, period):
    due_on = _due_date(forecast, period)
    if due_on < forecast.effective_date or due_on < forecast.occurred_on:
        return None
    defaults = {
        "family": forecast.family,
        "owner": forecast.owner,
        "account": forecast.account,
        "category": forecast.category,
        "amount": forecast.amount,
        "due_on": due_on,
        "description": forecast.description,
        "allocations": _allocation_snapshot(forecast),
    }
    lookup = (
        {"income_forecast": forecast, "source_period": period}
        if isinstance(forecast, IncomeForecast)
        else {"expense_forecast": forecast, "source_period": period}
    )
    obligation, _ = PaymentObligation.objects.get_or_create(**lookup, defaults=defaults)
    return obligation


def materialize_forecast_occurrences(*, forecast, start, end):
    """Snapshot each applicable monthly forecast once; existing snapshots never change."""
    period = _month_start(start)
    final_period = _month_start(end)
    obligations = []
    while period <= final_period:
        if forecast.recurrence == Recurrence.NONE and period != _month_start(forecast.occurred_on):
            period = _next_month(period)
            continue
        obligation = _create_obligation(forecast, period)
        if obligation is not None:
            obligations.append(obligation)
        if forecast.recurrence == Recurrence.NONE:
            break
        period = _next_month(period)
    return obligations


def materialize_family_occurrences(*, family, user, start, end):
    obligations = []
    forecasts = list(
        IncomeForecast.objects.visible_to(user).filter(family=family)
    ) + list(ExpenseForecast.objects.visible_to(user).filter(family=family))
    for forecast in forecasts:
        obligations.extend(
            materialize_forecast_occurrences(forecast=forecast, start=start, end=end)
        )
    return obligations


def preserve_historical_occurrences_before_forecast_edit(*, forecast):
    """Persist the pre-edit template through today, then refresh only future pending rows."""
    today = timezone.localdate()
    materialize_forecast_occurrences(
        forecast=forecast, start=_month_start(forecast.occurred_on), end=today
    )
    source_filter = (
        {"income_forecast": forecast}
        if isinstance(forecast, IncomeForecast)
        else {"expense_forecast": forecast}
    )
    PaymentObligation.objects.filter(
        **source_filter,
        status=ObligationStatus.PENDING,
        due_on__gt=today,
    ).delete()


@transaction.atomic
def settle_obligation(*, actor, obligation, allocations=None):
    obligation = PaymentObligation.objects.select_for_update().get(pk=obligation.pk)
    if obligation.status != ObligationStatus.PENDING:
        raise ValidationError("Only pending obligations can be settled.")
    if obligation.income_movement_id or obligation.expense_movement_id:
        raise ValidationError("This obligation has already been settled.")
    if obligation.income_forecast_id:
        movement = IncomeMovement.objects.create(
            family=obligation.family,
            owner=obligation.owner,
            account=obligation.account,
            category=obligation.category,
            amount=obligation.amount,
            occurred_on=obligation.due_on,
            description=obligation.description,
        )
        obligation.income_movement = movement
    else:
        allocation_data = allocations if allocations is not None else obligation.allocations
        normalized_allocations = [
            {"member_id": allocation["member_id"], "amount": Decimal(str(allocation["amount"]))}
            for allocation in allocation_data
        ]
        movement = create_expense_movement(
            actor=actor,
            family=obligation.family,
            movement_data={
                "owner": obligation.owner,
                "account": obligation.account,
                "category": obligation.category,
                "amount": obligation.amount,
                "occurred_on": obligation.due_on,
                "description": obligation.description,
            },
            allocations=normalized_allocations,
        )
        obligation.expense_movement = movement
    obligation.status = ObligationStatus.PAID
    obligation.save(update_fields=("status", "income_movement", "expense_movement", "updated_at"))
    record_entity_mutation(
        actor=actor,
        action="payment_obligation.settled",
        family=obligation.family,
        entity_type="payment_obligation",
        entity_id=obligation.pk,
        metadata={"movement_id": movement.pk},
    )
    return obligation


@transaction.atomic
def void_obligation(*, actor, obligation, reason):
    obligation = PaymentObligation.objects.select_for_update().get(pk=obligation.pk)
    if obligation.status != ObligationStatus.PENDING:
        raise ValidationError("Only pending obligations can be voided.")
    obligation.status = ObligationStatus.VOIDED
    obligation.void_reason = reason
    obligation.save(update_fields=("status", "void_reason", "updated_at"))
    record_entity_mutation(
        actor=actor,
        action="payment_obligation.voided",
        family=obligation.family,
        entity_type="payment_obligation",
        entity_id=obligation.pk,
        metadata={"reason": reason},
    )
    return obligation
