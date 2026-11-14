from datetime import date
from decimal import Decimal

import pytest
from rest_framework import status

from apps.budgets.models import (
    BudgetLine,
    FreeMoneyAllowance,
    MonthlyBudgetForecast,
    SavingsDistributionRule,
)
from apps.budgets.services import calculate_projected_savings, effective_budget_total
from apps.savings.models import SavingsGoal, SavingsMovement

pytestmark = pytest.mark.django_db


@pytest.fixture
def budget_records(family_factory, membership_factory, user_factory):
    jalberth = user_factory("jalberth")
    raiza = user_factory("raiza")
    family = family_factory("Family")
    membership_factory(family, jalberth, role="ADMIN")
    membership_factory(family, raiza)
    return {"jalberth": jalberth, "raiza": raiza, "family": family}


def create_budget(family, month, version=1, standard_amount="0.00"):
    forecast = MonthlyBudgetForecast.objects.create(family=family, month=month, version=version)
    BudgetLine.objects.create(forecast=forecast, name="Monthly expenses", amount=standard_amount)
    return forecast


def test_cigarettes_are_included_once_and_reconciliation_replacement_is_not_double_counted(budget_records):
    data = budget_records
    forecast = create_budget(data["family"], date(2026, 1, 1), standard_amount="1138.08")
    provisional_cigarettes = BudgetLine.objects.create(
        forecast=forecast,
        name="Cigarettes provisional",
        amount="186.00",
        kind=BudgetLine.Kind.RECONCILIATION,
    )

    initial = calculate_projected_savings(
        family=data["family"], month=date(2026, 1, 1), projected_income=Decimal("2190.00")
    )
    BudgetLine.objects.create(
        forecast=forecast,
        name="Cigarettes confirmed",
        amount="186.00",
        replaces=provisional_cigarettes,
    )
    reconciled = calculate_projected_savings(
        family=data["family"], month=date(2026, 1, 1), projected_income=Decimal("2190.00")
    )

    assert effective_budget_total(forecast) == Decimal("1324.08")
    assert initial["budget_total"] == Decimal("1324.08")
    assert initial["available_projected_savings"] == Decimal("865.92")
    assert reconciled["budget_total"] == Decimal("1324.08")
    assert reconciled["available_projected_savings"] == Decimal("865.92")


def test_first_and_subsequent_month_scenarios_use_decimal_distribution_without_real_savings_changes(budget_records):
    data = budget_records
    first_month = create_budget(data["family"], date(2026, 1, 1), standard_amount="1324.08")
    create_budget(data["family"], date(2026, 2, 1), standard_amount="1254.08")
    SavingsDistributionRule.objects.create(
        family=data["family"],
        effective_date=date(2026, 1, 1),
        first_owner=data["jalberth"],
        second_owner=data["raiza"],
    )
    goal = SavingsGoal.objects.create(family=data["family"], name="Shared", target_amount="1000.00")
    real_balance_before = goal.real_balance

    first = calculate_projected_savings(
        family=data["family"], month=first_month.month, projected_income=Decimal("2190.00")
    )
    subsequent = calculate_projected_savings(
        family=data["family"], month=date(2026, 2, 1), projected_income=Decimal("2190.00")
    )
    goal.refresh_from_db()

    assert first["available_projected_savings"] == Decimal("865.92")
    assert first["distribution"] == {
        "rule_id": first["distribution"]["rule_id"],
        "first_owner_id": data["jalberth"].pk,
        "first_owner_amount": Decimal("216.48"),
        "second_owner_id": data["raiza"].pk,
        "second_owner_amount": Decimal("216.48"),
        "matias_amount": Decimal("432.96"),
    }
    assert subsequent["available_projected_savings"] == Decimal("935.92")
    assert subsequent["distribution"]["first_owner_amount"] == Decimal("233.98")
    assert subsequent["distribution"]["second_owner_amount"] == Decimal("233.98")
    assert subsequent["distribution"]["matias_amount"] == Decimal("467.96")
    assert goal.real_balance == real_balance_before == Decimal("0.00")
    assert SavingsMovement.objects.count() == 0


def test_calculation_uses_the_latest_version_for_the_same_month(budget_records):
    data = budget_records
    create_budget(data["family"], date(2026, 1, 1), version=1, standard_amount="1324.08")
    latest = create_budget(data["family"], date(2026, 1, 1), version=2, standard_amount="1254.08")

    calculation = calculate_projected_savings(
        family=data["family"], month=date(2026, 1, 1), projected_income=Decimal("2190.00")
    )

    assert calculation["forecast_id"] == latest.pk
    assert calculation["available_projected_savings"] == Decimal("935.92")


def test_allowance_api_scopes_private_values_and_configuration_to_owner_or_admin(api_client, budget_records):
    data = budget_records
    allowance_url = f"/api/v1/families/{data['family'].pk}/free-money-allowances/"
    rules_url = f"/api/v1/families/{data['family'].pk}/savings-distribution-rules/"
    summary_url = f"/api/v1/families/{data['family'].pk}/budgets/projected-savings/"
    FreeMoneyAllowance.objects.create(
        family=data["family"], owner=data["jalberth"], amount="700.00", effective_date="2026-01-01"
    )
    FreeMoneyAllowance.objects.create(
        family=data["family"], owner=data["raiza"], amount="100.00", effective_date="2026-01-01"
    )
    api_client.force_authenticate(data["raiza"])

    own_allowances = api_client.get(allowance_url)
    private_create = api_client.post(
        allowance_url,
        {"owner_id": data["jalberth"].pk, "amount": "1.00", "effective_date": "2026-02-01"},
        format="json",
    )
    rules_response = api_client.get(rules_url)
    summary_response = api_client.post(
        summary_url, {"month": "2026-01-01", "projected_income": "2190.00"}, format="json"
    )

    assert own_allowances.status_code == status.HTTP_200_OK
    assert [allowance["owner_id"] for allowance in own_allowances.data] == [data["raiza"].pk]
    assert b"700.00" not in own_allowances.content
    assert private_create.status_code == status.HTTP_403_FORBIDDEN
    assert rules_response.status_code == status.HTTP_403_FORBIDDEN
    assert summary_response.status_code == status.HTTP_403_FORBIDDEN


def test_admin_can_create_shared_budget_forecast_via_api(api_client, budget_records):
    data = budget_records
    api_client.force_authenticate(data["jalberth"])

    response = api_client.post(
        f"/api/v1/families/{data['family'].pk}/budget-forecasts/",
        {
            "month": "2026-01-01",
            "version": 1,
            "lines": [
                {"name": "Base", "amount": "1138.08", "kind": "STANDARD"},
                {"name": "Cigarettes", "amount": "186.00", "kind": "RECONCILIATION"},
            ],
        },
        format="json",
    )

    assert response.status_code == status.HTTP_201_CREATED
    assert MonthlyBudgetForecast.objects.count() == 1
    assert BudgetLine.objects.count() == 2
