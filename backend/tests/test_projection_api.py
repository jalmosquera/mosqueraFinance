from decimal import Decimal

import pytest
from rest_framework import status

from apps.budgets.models import (
    BudgetLine,
    FreeMoneyAllowance,
    MonthlyBudgetForecast,
    SavingsDistributionRule,
)
from apps.expenses.models import ExpenseForecast
from apps.finance.models import Category, LogicalAccount
from apps.incomes.models import IncomeForecast, Recurrence
from apps.savings.models import (
    MatiasFund,
    MatiasFundMovement,
    SavingsGoal,
    SavingsMovement,
)

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


def create_approved_forecast_records(data):
    create_income(data, owner=data["jalberth"], amount="1290.00")
    create_income(data, owner=data["raiza"], amount="1300.00")
    for offset in range(12):
        month = f"2026-{offset + 1:02d}-01"
        forecast = MonthlyBudgetForecast.objects.create(family=data["family"], month=month, version=1)
        BudgetLine.objects.create(
            forecast=forecast,
            name="Monthly expenses",
            amount="1324.08",
        )
    SavingsDistributionRule.objects.create(
        family=data["family"],
        effective_date="2026-01-01",
        first_owner=data["jalberth"],
        second_owner=data["raiza"],
    )
    SavingsGoal.objects.create(
        family=data["family"], owner=data["jalberth"], name="Jalberth goal", target_amount="1000.00"
    )
    SavingsGoal.objects.create(
        family=data["family"], owner=data["raiza"], name="Raiza goal", target_amount="1000.00"
    )
    SavingsGoal.objects.create(family=data["family"], name="Family goal", target_amount="2000.00")
    FreeMoneyAllowance.objects.create(
        family=data["family"], owner=data["jalberth"], amount="150.00", effective_date="2026-01-01"
    )
    FreeMoneyAllowance.objects.create(
        family=data["family"], owner=data["raiza"], amount="150.00", effective_date="2026-01-01"
    )
    MatiasFund.objects.create(
        family=data["family"],
        target_amount="500.00",
        initial_contribution_total="100.00",
        monthly_simulated_expenditure="30.00",
        monthly_replenishment_total="30.00",
    )


def test_approved_forecast_uses_persisted_planning_data_without_creating_movements(
    api_client, projection_records
):
    data = projection_records
    create_approved_forecast_records(data)
    api_client.force_authenticate(data["jalberth"])

    response = api_client.get(
        f"/api/v1/families/{data['family'].pk}/projections/approved-forecast/",
        {"start_month": "2026-01-01"},
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.data["role"] == "ADMIN"
    assert response.data["summary"] == {
        "annual_projected_savings": "11161.04",
        "first_month_projected_savings": "865.92",
        "subsequent_month_projected_savings": "935.92",
    }
    assert response.data["family_savings"]["annual_projected_savings"] == "5580.52"
    assert response.data["distribution"]["family_percentage"] == "50.00"
    assert response.data["chart"][0]["projected_savings"] == "865.92"
    assert response.data["chart"][0]["personal_amount"] == "216.48"
    assert response.data["chart"][0]["first_owner"] == {
        "id": data["jalberth"].pk, "label": "jalberth"
    }
    assert response.data["chart"][0]["first_owner_amount"] == "216.48"
    assert response.data["chart"][0]["second_owner"] == {
        "id": data["raiza"].pk, "label": "raiza"
    }
    assert response.data["chart"][0]["second_owner_amount"] == "216.48"
    assert response.data["chart"][0]["family_amount"] == "432.96"
    assert response.data["distribution"]["first_owner"] == response.data["chart"][0]["first_owner"]
    assert response.data["distribution"]["second_owner"] == response.data["chart"][0]["second_owner"]
    assert all(month["projected_savings"] == "935.92" for month in response.data["chart"][1:])
    assert response.data["matias_plan"] == {
        "target_amount": "500.00",
        "real_confirmed_balance": "0.00",
        "initial_contribution_total": "100.00",
        "initial_contribution_per_parent": "50.00",
        "monthly_simulated_expenditure": "30.00",
        "monthly_replenishment_total": "30.00",
        "monthly_replenishment_per_parent": "15.00",
    }
    assert MatiasFundMovement.objects.count() == 0
    assert SavingsMovement.objects.count() == 0


def test_approved_forecast_response_prevents_private_caching(api_client, projection_records):
    data = projection_records
    create_approved_forecast_records(data)
    api_client.force_authenticate(data["raiza"])

    response = api_client.get(
        f"/api/v1/families/{data['family'].pk}/projections/approved-forecast/",
        {"start_month": "2026-01-01"},
    )

    assert response.status_code == status.HTTP_200_OK
    assert response["Cache-Control"] == "private, no-store"


def test_approved_forecast_lists_each_missing_budget_month(api_client, projection_records):
    data = projection_records
    create_income(data, amount="2190.00")
    SavingsDistributionRule.objects.create(
        family=data["family"], effective_date="2026-01-01",
        first_owner=data["jalberth"], second_owner=data["raiza"],
    )
    api_client.force_authenticate(data["jalberth"])

    response = api_client.get(
        f"/api/v1/families/{data['family'].pk}/projections/approved-forecast/",
        {"start_month": "2026-01-01"},
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.data["missing_budget_months"] == [f"2026-{month:02d}-01" for month in range(1, 13)]


def test_raiza_approved_forecast_excludes_jalberth_private_markers(api_client, projection_records):
    data = projection_records
    create_approved_forecast_records(data)
    create_income(data, owner=data["jalberth"], amount="999999.91")
    SavingsGoal.objects.create(
        family=data["family"], owner=data["jalberth"], name="Jalberth private", target_amount="888888.82"
    )
    FreeMoneyAllowance.objects.create(
        family=data["family"], owner=data["jalberth"], amount="666666.64", effective_date="2026-02-01"
    )
    api_client.force_authenticate(data["raiza"])

    response = api_client.get(
        f"/api/v1/families/{data['family'].pk}/projections/approved-forecast/",
        {"start_month": "2026-01-01"},
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.data["role"] == "MEMBER"
    assert response.data["visibility"] == "SELF_AND_SHARED"
    assert response.data["personal_savings"] == [
        {
            "owner_id": data["raiza"].pk,
            "owner_label": "raiza",
            "annual_target": "1000.00",
            "real_confirmed_balance": "0.00",
            "progress_percent": "0.00",
        }
    ]
    assert response.data["family_savings"] == {
        "label": "Family",
        "annual_target": "2000.00",
        "real_confirmed_balance": "0.00",
        "progress_percent": "0.00",
    }
    assert [allowance["owner_id"] for allowance in response.data["free_money"]] == [data["raiza"].pk]
    assert response.data["free_money"][0]["monthly_amounts"] == ["150.00"] * 12
    assert set(response.data) == {
        "start_month", "role", "visibility", "personal_savings", "family_savings", "matias_plan", "free_money"
    }
    assert b"999999.91" not in response.content
    assert b"888888.82" not in response.content
    assert b"666666.64" not in response.content
    assert b"Jalberth" not in response.content
    assert "summary" not in response.data
    assert "chart" not in response.data
    assert "distribution" not in response.data


def test_non_founder_admin_approved_forecast_excludes_private_data(
    api_client, projection_records
):
    data = projection_records
    create_approved_forecast_records(data)
    create_income(data, owner=data["jalberth"], amount="999999.91")
    SavingsGoal.objects.create(
        family=data["family"],
        owner=data["jalberth"],
        name="Jalberth private",
        target_amount="888888.82",
    )
    FreeMoneyAllowance.objects.create(
        family=data["family"],
        owner=data["jalberth"],
        amount="666666.64",
        effective_date="2026-02-01",
    )
    membership = data["family"].memberships.get(user=data["raiza"])
    membership.role = "ADMIN"
    membership.save(update_fields=("role",))
    api_client.force_authenticate(data["raiza"])

    response = api_client.get(
        f"/api/v1/families/{data['family'].pk}/projections/approved-forecast/",
        {"start_month": "2026-01-01"},
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.data["role"] == "MEMBER"
    assert response.data["visibility"] == "SELF_AND_SHARED"
    assert b"999999.91" not in response.content
    assert b"888888.82" not in response.content
    assert b"666666.64" not in response.content
    assert b"Jalberth" not in response.content
    assert "summary" not in response.data
    assert "chart" not in response.data
    assert "distribution" not in response.data


def test_approved_forecast_progress_uses_confirmed_balances_and_is_clamped(
    api_client, projection_records
):
    data = projection_records
    create_approved_forecast_records(data)
    raiza_goal = SavingsGoal.objects.get(family=data["family"], owner=data["raiza"])
    shared_goal = SavingsGoal.objects.get(family=data["family"], owner__isnull=True)
    SavingsMovement.objects.create(
        goal=raiza_goal,
        kind="CONTRIBUTION",
        amount="1500.00",
        occurred_on="2026-01-01",
    )
    SavingsMovement.objects.create(
        goal=shared_goal,
        kind="CONTRIBUTION",
        amount="500.00",
        occurred_on="2026-01-01",
    )
    api_client.force_authenticate(data["raiza"])

    response = api_client.get(
        f"/api/v1/families/{data['family'].pk}/projections/approved-forecast/",
        {"start_month": "2026-01-01"},
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.data["personal_savings"][0]["real_confirmed_balance"] == "1500.00"
    assert response.data["personal_savings"][0]["progress_percent"] == "100.00"
    assert response.data["family_savings"]["real_confirmed_balance"] == "500.00"
    assert response.data["family_savings"]["progress_percent"] == "25.00"
