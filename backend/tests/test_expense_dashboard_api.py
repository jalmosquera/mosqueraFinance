from datetime import date
from decimal import Decimal

import pytest

from apps.budgets.models import BudgetLine, MonthlyBudgetForecast
from apps.expenses.models import (
    ExpenseAllocation,
    ExpenseForecast,
    ExpenseForecastAllocation,
    ExpenseMovement,
)
from apps.finance.models import Category, LogicalAccount
from apps.obligations.models import PaymentObligation

pytestmark = pytest.mark.django_db


@pytest.fixture
def dashboard_records(family_factory, membership_factory, user_factory):
    jalberth = user_factory("jalberth")
    raiza = user_factory("raiza")
    family = family_factory("Family")
    membership_factory(family, jalberth, role="ADMIN")
    membership_factory(family, raiza)
    shared_account = LogicalAccount.objects.create(family=family, name="Shared")
    jalberth_account = LogicalAccount.objects.create(
        family=family, owner=jalberth, name="Jalberth private"
    )
    raiza_account = LogicalAccount.objects.create(
        family=family, owner=raiza, name="Raiza private"
    )
    shared_category = Category.objects.create(
        family=family, name="Cigarettes", kind=Category.Kind.EXPENSE
    )
    jalberth_category = Category.objects.create(
        family=family,
        owner=jalberth,
        name="Jalberth confidential expense",
        kind=Category.Kind.EXPENSE,
    )
    raiza_category = Category.objects.create(
        family=family,
        owner=raiza,
        name="Raiza private expense",
        kind=Category.Kind.EXPENSE,
    )
    return {
        "jalberth": jalberth,
        "raiza": raiza,
        "family": family,
        "shared_account": shared_account,
        "jalberth_account": jalberth_account,
        "raiza_account": raiza_account,
        "shared_category": shared_category,
        "jalberth_category": jalberth_category,
        "raiza_category": raiza_category,
    }


def _create_dashboard_data(data, month):
    cigarettes = ExpenseForecast.objects.create(
        family=data["family"],
        account=data["shared_account"],
        category=data["shared_category"],
        amount=Decimal("186.00"),
        occurred_on=month.replace(day=10),
        effective_date=month,
        recurrence="MONTHLY",
        is_cigarettes=True,
    )
    ExpenseForecastAllocation.objects.create(
        forecast=cigarettes, member=data["jalberth"], amount=Decimal("93.00")
    )
    ExpenseForecastAllocation.objects.create(
        forecast=cigarettes, member=data["raiza"], amount=Decimal("93.00")
    )
    raiza_forecast = ExpenseForecast.objects.create(
        family=data["family"],
        owner=data["raiza"],
        account=data["raiza_account"],
        category=data["raiza_category"],
        amount=Decimal("20.00"),
        occurred_on=month.replace(day=12),
        effective_date=month,
    )
    jalberth_forecast = ExpenseForecast.objects.create(
        family=data["family"],
        owner=data["jalberth"],
        account=data["jalberth_account"],
        category=data["jalberth_category"],
        amount=Decimal("777.00"),
        occurred_on=month.replace(day=13),
        effective_date=month,
    )
    shared_movement = ExpenseMovement.objects.create(
        family=data["family"],
        account=data["shared_account"],
        category=data["shared_category"],
        amount=Decimal("50.00"),
        occurred_on=month.replace(day=14),
    )
    ExpenseAllocation.objects.create(
        movement=shared_movement, member=data["jalberth"], amount=Decimal("25.00")
    )
    ExpenseAllocation.objects.create(
        movement=shared_movement, member=data["raiza"], amount=Decimal("25.00")
    )
    ExpenseMovement.objects.create(
        family=data["family"],
        owner=data["raiza"],
        account=data["raiza_account"],
        category=data["raiza_category"],
        amount=Decimal("30.00"),
        occurred_on=month.replace(day=15),
    )
    ExpenseMovement.objects.create(
        family=data["family"],
        owner=data["jalberth"],
        account=data["jalberth_account"],
        category=data["jalberth_category"],
        amount=Decimal("999.00"),
        occurred_on=month.replace(day=16),
    )
    PaymentObligation.objects.create(
        family=data["family"],
        expense_forecast=cigarettes,
        source_period=month,
        account=data["shared_account"],
        category=data["shared_category"],
        amount=Decimal("186.00"),
        due_on=month.replace(day=20),
    )
    PaymentObligation.objects.create(
        family=data["family"],
        expense_forecast=jalberth_forecast,
        source_period=month,
        owner=data["jalberth"],
        account=data["jalberth_account"],
        category=data["jalberth_category"],
        amount=Decimal("777.00"),
        due_on=month.replace(day=21),
    )
    budget = MonthlyBudgetForecast.objects.create(
        family=data["family"], month=month, version=1
    )
    BudgetLine.objects.create(forecast=budget, name="Household plan", amount=Decimal("1000.00"))
    return cigarettes, raiza_forecast, jalberth_forecast


def _url(data, month):
    return f"/api/v1/families/{data['family'].pk}/expenses/dashboard/?month={month.isoformat()}"


def test_admin_dashboard_returns_authorized_household_plan_and_confirmed_totals(
    api_client, dashboard_records
):
    month = date(2030, 2, 1)
    data = dashboard_records
    _create_dashboard_data(data, month)
    api_client.force_authenticate(data["jalberth"])

    response = api_client.get(_url(data, month))

    assert response.status_code == 200
    assert response.data["visibility"] == {"role": "ADMIN", "scope": "HOUSEHOLD"}
    assert response.data["forecast"] == {"label": "PLANNED_EXPENSES", "total": "983.00"}
    assert response.data["confirmed"] == {"label": "CONFIRMED_EXPENSES", "total": "1079.00"}
    assert response.data["responsibility"] == {
        "setup_required": False,
        "items": [
            {"member": "jalberth", "amount": "870.00"},
            {"member": "raiza", "amount": "113.00"},
        ],
    }
    assert response.data["budget_utilization"] == {
        "source": "MONTHLY_BUDGET_FORECAST",
        "budget_total": "1000.00",
        "confirmed_expense_total": "1079.00",
        "percent": "107.90",
    }
    assert {item["source"] for item in response.data["categories"]} == {"FORECAST", "BUDGET"}
    assert response.data["upcoming_obligations"] == [
        {"due_on": "2030-02-20", "category": "Cigarettes", "amount": "186.00", "label": "PLANNED_OBLIGATION"},
        {"due_on": "2030-02-21", "category": "Jalberth confidential expense", "amount": "777.00", "label": "PLANNED_OBLIGATION"},
    ]


def test_raiza_dashboard_excludes_jalberth_private_sentinel_data_and_budget(
    api_client, dashboard_records
):
    month = date(2030, 2, 1)
    data = dashboard_records
    _create_dashboard_data(data, month)
    api_client.force_authenticate(data["raiza"])

    response = api_client.get(_url(data, month))

    assert response.status_code == 200
    assert response.data["visibility"] == {"role": "MEMBER", "scope": "OWN_AND_SHARED"}
    assert response.data["forecast"]["total"] == "206.00"
    assert response.data["confirmed"]["total"] == "80.00"
    assert response.data["responsibility"] == {
        "setup_required": False,
        "items": [{"member": "You", "amount": "113.00"}],
    }
    assert response.data["budget_utilization"] is None
    assert response.data["upcoming_obligations"] == [
        {"due_on": "2030-02-20", "category": "Cigarettes", "amount": "186.00", "label": "PLANNED_OBLIGATION"}
    ]
    assert "Jalberth confidential expense" not in str(response.data)
    assert "777.00" not in str(response.data)
    assert "999.00" not in str(response.data)
    assert "member_id" not in str(response.data)


def test_non_founder_admin_dashboard_excludes_founder_private_data(
    api_client, dashboard_records
):
    month = date(2030, 2, 1)
    data = dashboard_records
    _create_dashboard_data(data, month)
    membership = data["family"].memberships.get(user=data["raiza"])
    membership.role = "ADMIN"
    membership.save(update_fields=("role",))
    api_client.force_authenticate(data["raiza"])

    response = api_client.get(_url(data, month))

    assert response.status_code == 200
    assert response.data["visibility"] == {"role": "MEMBER", "scope": "OWN_AND_SHARED"}
    assert response.data["forecast"]["total"] == "206.00"
    assert response.data["confirmed"]["total"] == "80.00"
    assert response.data["budget_utilization"] is None
    assert "Jalberth confidential expense" not in str(response.data)
    assert "777.00" not in str(response.data)
    assert "999.00" not in str(response.data)


def test_dashboard_reads_only_materialized_obligations_without_side_effects(
    api_client, dashboard_records
):
    month = date(2030, 2, 1)
    data = dashboard_records
    _create_dashboard_data(data, month)
    before = {
        "forecasts": ExpenseForecast.objects.count(),
        "movements": ExpenseMovement.objects.count(),
        "obligations": PaymentObligation.objects.count(),
    }
    api_client.force_authenticate(data["raiza"])

    response = api_client.get(_url(data, month))

    assert response.status_code == 200
    assert before == {
        "forecasts": ExpenseForecast.objects.count(),
        "movements": ExpenseMovement.objects.count(),
        "obligations": PaymentObligation.objects.count(),
    }
