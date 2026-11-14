from decimal import Decimal

import pytest
from rest_framework import status

from apps.expenses.models import ExpenseForecast
from apps.finance.models import Category, LogicalAccount
from apps.incomes.models import IncomeForecast, Recurrence
from apps.savings.models import SavingsGoal, SavingsMovement

pytestmark = pytest.mark.django_db


@pytest.fixture
def projection_records(family_factory, membership_factory, user_factory):
    jalberth = user_factory("jalberth")
    raiza = user_factory("raiza")
    family = family_factory("Family")
    membership_factory(family, jalberth, role="ADMIN")
    membership_factory(family, raiza)
    account = LogicalAccount.objects.create(family=family, name="Shared")
    income_category = Category.objects.create(
        family=family, name="Income", kind=Category.Kind.INCOME
    )
    expense_category = Category.objects.create(
        family=family, name="Expense", kind=Category.Kind.EXPENSE
    )
    return {
        "jalberth": jalberth,
        "raiza": raiza,
        "family": family,
        "account": account,
        "income_category": income_category,
        "expense_category": expense_category,
    }


def create_income(data, *, owner=None, amount="100.00"):
    return IncomeForecast.objects.create(
        family=data["family"],
        owner=owner,
        account=data["account"],
        category=data["income_category"],
        amount=amount,
        occurred_on="2026-01-01",
        effective_date="2026-01-01",
        recurrence=Recurrence.MONTHLY,
    )


def create_expense(data, *, owner=None, amount="20.00"):
    return ExpenseForecast.objects.create(
        family=data["family"],
        owner=owner,
        account=data["account"],
        category=data["expense_category"],
        amount=amount,
        occurred_on="2026-01-01",
        effective_date="2026-01-01",
        recurrence=Recurrence.MONTHLY,
    )


def test_scenario_applies_explicit_changes_without_persisting_balances(
    api_client, projection_records
):
    data = projection_records
    income = create_income(data, amount="100.00")
    create_expense(data, amount="20.00")
    goal = SavingsGoal.objects.create(
        family=data["family"],
        name="Shared goal",
        target_amount="1000.00",
        projected_balance="50.00",
        projected_monthly_contribution="10.00",
    )
    SavingsMovement.objects.create(
        goal=goal, kind="CONTRIBUTION", amount="25.00", occurred_on="2026-01-01"
    )
    api_client.force_authenticate(data["raiza"])

    response = api_client.post(
        f"/api/v1/families/{data['family'].pk}/projections/scenario/",
        {
            "start_month": "2026-01-01",
            "income_changes": [{"forecast_id": income.pk, "amount": "120.00"}],
            "savings_changes": [
                {"goal_id": goal.pk, "projected_monthly_contribution": "15.00"}
            ],
        },
        format="json",
    )
    income.refresh_from_db()
    goal.refresh_from_db()

    assert response.status_code == status.HTTP_200_OK
    assert len(response.data["months"]) == 12
    assert response.data["months"][0] == {
        "month": "2026-01-01",
        "income": "120.00",
        "expenses": "20.00",
        "savings_contribution": "15.00",
        "net_after_savings": "85.00",
        "projected_savings_balance": "65.00",
    }
    assert income.amount == Decimal("100.00")
    assert goal.projected_monthly_contribution == Decimal("10.00")
    assert goal.projected_balance == Decimal("50.00")
    assert goal.real_balance == Decimal("25.00")
    assert SavingsMovement.objects.count() == 1


def test_raiza_projection_excludes_jalberth_private_values(api_client, projection_records):
    data = projection_records
    create_income(data, amount="100.00")
    create_income(data, owner=data["jalberth"], amount="9000.00")
    create_expense(data, amount="20.00")
    create_expense(data, owner=data["jalberth"], amount="8000.00")
    SavingsGoal.objects.create(
        family=data["family"],
        name="Shared goal",
        target_amount="1000.00",
        projected_balance="50.00",
        projected_monthly_contribution="10.00",
    )
    SavingsGoal.objects.create(
        family=data["family"],
        owner=data["jalberth"],
        name="Private goal",
        target_amount="10000.00",
        projected_balance="7000.00",
        projected_monthly_contribution="6000.00",
    )
    api_client.force_authenticate(data["raiza"])

    response = api_client.post(
        f"/api/v1/families/{data['family'].pk}/projections/scenario/",
        {"start_month": "2026-01-01"},
        format="json",
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.data["months"][0] == {
        "month": "2026-01-01",
        "income": "100.00",
        "expenses": "20.00",
        "savings_contribution": "10.00",
        "net_after_savings": "70.00",
        "projected_savings_balance": "60.00",
    }
    assert b"9000" not in response.content
    assert b"8000" not in response.content
    assert b"6000" not in response.content
