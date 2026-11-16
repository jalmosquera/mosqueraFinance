import calendar
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from django.db.models import Q, Sum
from django.utils import timezone

from apps.budgets.models import BudgetLine
from apps.budgets.services import effective_budget_total, latest_budget_for_month
from apps.families.models import FamilyMembership
from apps.incomes.models import MovementStatus, Recurrence
from apps.obligations.models import ObligationStatus, PaymentObligation

from .models import ExpenseForecast, ExpenseMovement

CENT = Decimal("0.01")
ZERO = Decimal("0.00")


def _money(value):
    return f"{value.quantize(CENT, rounding=ROUND_HALF_UP):.2f}"


def _next_month(month):
    return date(month.year + (month.month == 12), month.month % 12 + 1, 1)


def _applies_in_month(forecast, month):
    due_on = month.replace(
        day=min(forecast.occurred_on.day, calendar.monthrange(month.year, month.month)[1])
    )
    if forecast.recurrence == Recurrence.NONE:
        return month == forecast.occurred_on.replace(day=1) and due_on >= forecast.effective_date
    return due_on >= forecast.effective_date and due_on >= forecast.occurred_on


def _has_household_aggregate_authority(*, user, family):
    return FamilyMembership.objects.household_aggregate_authority_for(
        user, family
    ).exists()


def _visible_records(*, model, user, family, is_admin):
    queryset = model.objects.filter(family=family)
    if not is_admin:
        queryset = queryset.visible_to(user)
    return queryset


def _responsibilities(*, forecasts, user, is_admin):
    amounts = {}
    members = {}
    incomplete_shared_forecasts = False
    for forecast in forecasts:
        if forecast.owner_id is not None:
            amounts[forecast.owner_id] = amounts.get(forecast.owner_id, ZERO) + forecast.amount
            members[forecast.owner_id] = forecast.owner
            continue

        allocations = list(forecast.allocations.all())
        if sum((allocation.amount for allocation in allocations), ZERO) != forecast.amount:
            incomplete_shared_forecasts = True
            continue
        for allocation in allocations:
            amounts[allocation.member_id] = amounts.get(allocation.member_id, ZERO) + allocation.amount
            members[allocation.member_id] = allocation.member

    items = []
    for member_id, amount in sorted(amounts.items()):
        if is_admin:
            label = members[member_id].username
        elif member_id == user.pk:
            label = "You"
        else:
            continue
        items.append({"member": label, "amount": _money(amount)})
    return {"setup_required": incomplete_shared_forecasts, "items": items}


def _category_totals(forecasts):
    totals = {}
    for forecast in forecasts:
        totals[forecast.category.name] = totals.get(forecast.category.name, ZERO) + forecast.amount
    return [
        {"source": "FORECAST", "name": name, "amount": _money(amount)}
        for name, amount in sorted(totals.items())
    ]


def build_expense_dashboard(*, family, user, month):
    has_household_aggregate_authority = _has_household_aggregate_authority(
        user=user, family=family
    )
    forecasts = [
        forecast
        for forecast in _visible_records(
            model=ExpenseForecast,
            user=user,
            family=family,
            is_admin=has_household_aggregate_authority,
        ).select_related("owner", "category").prefetch_related("allocations__member")
        if _applies_in_month(forecast, month)
    ]
    movement_queryset = _visible_records(
        model=ExpenseMovement,
        user=user,
        family=family,
        is_admin=has_household_aggregate_authority,
    )
    confirmed_total = movement_queryset.filter(
        occurred_on__gte=month,
        occurred_on__lt=_next_month(month),
        status=MovementStatus.CONFIRMED,
        is_reversal=False,
        reversal__isnull=True,
    ).aggregate(total=Sum("amount"))["total"] or ZERO
    obligations = _visible_records(
        model=PaymentObligation,
        user=user,
        family=family,
        is_admin=has_household_aggregate_authority,
    ).filter(
        expense_forecast__isnull=False,
        source_period=month,
        status=ObligationStatus.PENDING,
        due_on__gte=timezone.localdate(),
    ).select_related("category")

    categories = _category_totals(forecasts)
    budget_utilization = None
    if has_household_aggregate_authority:
        budget = latest_budget_for_month(family=family, month=month)
        if budget is not None:
            budget_total = effective_budget_total(budget)
            budget_utilization = {
                "source": "MONTHLY_BUDGET_FORECAST",
                "budget_total": _money(budget_total),
                "confirmed_expense_total": _money(confirmed_total),
                "percent": _money(confirmed_total * Decimal(100) / budget_total)
                if budget_total
                else None,
            }
            categories.extend(
                {
                    "source": "BUDGET",
                    "name": line.name,
                    "amount": _money(line.amount),
                }
                for line in BudgetLine.objects.filter(forecast=budget).filter(
                    Q(kind=BudgetLine.Kind.STANDARD)
                    | Q(kind=BudgetLine.Kind.RECONCILIATION, replaced_by__isnull=True)
                )
            )

    return {
        "month": month.isoformat(),
        "visibility": {
            "role": "ADMIN" if has_household_aggregate_authority else "MEMBER",
            "scope": "HOUSEHOLD" if has_household_aggregate_authority else "OWN_AND_SHARED",
        },
        "forecast": {
            "label": "PLANNED_EXPENSES",
            "total": _money(sum((forecast.amount for forecast in forecasts), ZERO)),
        },
        "confirmed": {
            "label": "CONFIRMED_EXPENSES",
            "total": _money(confirmed_total),
        },
        "responsibility": _responsibilities(
            forecasts=forecasts,
            user=user,
            is_admin=has_household_aggregate_authority,
        ),
        "budget_utilization": budget_utilization,
        "categories": categories,
        "upcoming_obligations": [
            {
                "due_on": obligation.due_on.isoformat(),
                "category": obligation.category.name,
                "amount": _money(obligation.amount),
                "label": "PLANNED_OBLIGATION",
            }
            for obligation in obligations
        ],
    }
