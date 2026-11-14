from decimal import Decimal

import pytest
from rest_framework import status

from apps.audit.models import AuditLog
from apps.budgets.models import (
    BudgetLine,
    FreeMoneyAllowance,
    MonthlyBudgetForecast,
    SavingsDistributionRule,
)
from apps.expenses.models import ExpenseForecast, ExpenseForecastAllocation
from apps.finance.models import Category, LogicalAccount
from apps.incomes.models import IncomeForecast
from apps.savings.models import (
    MatiasFund,
    MatiasFundMovement,
    SavingsGoal,
    SavingsMovement,
)

pytestmark = pytest.mark.django_db


@pytest.fixture
def configuration_records(family_factory, membership_factory, user_factory):
    admin = user_factory("administrator")
    member = user_factory("member")
    family = family_factory("Family")
    membership_factory(family, admin, role="ADMIN")
    membership_factory(family, member)
    return {"admin": admin, "member": member, "family": family}


def configuration_payload(member_id, other_member_id):
    return {
        "accounts": [{"key": "shared", "name": "Shared account", "owner_id": None}],
        "categories": [
            {"key": "income", "name": "Salary", "kind": "INCOME", "owner_id": None},
            {"key": "expense", "name": "Living", "kind": "EXPENSE", "owner_id": None},
        ],
        "income_forecasts": [
            {
                "account_key": "shared", "category_key": "income", "amount": "100.00",
                "occurred_on": "2026-01-01", "effective_date": "2026-01-01", "recurrence": "MONTHLY",
            }
        ],
        "expense_forecasts": [
            {
                "account_key": "shared", "category_key": "expense", "amount": "186.00",
                "occurred_on": "2026-01-01", "effective_date": "2026-01-01", "recurrence": "MONTHLY",
                "is_cigarettes": True,
                "allocations": [
                    {"member_id": member_id, "amount": "93.00"},
                    {"member_id": other_member_id, "amount": "93.00"},
                ],
            }
        ],
        "budget": {
            "month": "2026-01-01",
            "lines": [{"name": "Living", "amount": "80.00"}, {"name": "Cigarettes", "amount": "186.00"}],
        },
        "free_money_allowances": [
            {"owner_id": member_id, "amount": "10.00", "effective_date": "2026-01-01"}
        ],
        "savings_distribution": {
            "effective_date": "2026-01-01", "first_owner_id": member_id, "second_owner_id": other_member_id,
        },
        "matias_fund": {"target_amount": "500.00", "projected_balance": "25.00"},
    }


def test_initial_configuration_is_admin_only(api_client, configuration_records):
    data = configuration_records
    url = f"/api/v1/families/{data['family'].pk}/initial-forecast-configuration/"
    payload = configuration_payload(data["member"].pk, data["admin"].pk)

    anonymous = api_client.put(url, payload, format="json")
    api_client.force_authenticate(data["member"])
    non_admin = api_client.put(url, payload, format="json")

    assert anonymous.status_code == status.HTTP_403_FORBIDDEN
    assert non_admin.status_code == status.HTTP_403_FORBIDDEN
    assert IncomeForecast.objects.count() == 0


def test_initial_configuration_creates_only_planning_data_and_audits(api_client, configuration_records):
    data = configuration_records
    goal = SavingsGoal.objects.create(family=data["family"], name="Goal", target_amount="1000.00")
    url = f"/api/v1/families/{data['family'].pk}/initial-forecast-configuration/"
    payload = configuration_payload(data["member"].pk, data["admin"].pk)
    api_client.force_authenticate(data["admin"])

    response = api_client.put(url, payload, format="json")
    goal.refresh_from_db()

    assert response.status_code == status.HTTP_200_OK
    assert LogicalAccount.objects.count() == 1
    assert Category.objects.count() == 2
    assert IncomeForecast.objects.count() == 1
    assert ExpenseForecast.objects.get().is_cigarettes is True
    assert list(ExpenseForecastAllocation.objects.values_list("amount", flat=True)) == [Decimal("93.00"), Decimal("93.00")]
    assert MonthlyBudgetForecast.objects.count() == 1
    assert BudgetLine.objects.count() == 2
    assert FreeMoneyAllowance.objects.count() == 1
    assert SavingsDistributionRule.objects.count() == 1
    assert MatiasFund.objects.get().projected_balance == Decimal("25.00")
    assert SavingsMovement.objects.count() == 0
    assert MatiasFundMovement.objects.count() == 0
    assert goal.real_balance == Decimal("0.00")
    assert AuditLog.objects.filter(action="initial_forecast_configuration.updated").count() == 1


def test_initial_configuration_updates_existing_records_without_duplicates(api_client, configuration_records):
    data = configuration_records
    url = f"/api/v1/families/{data['family'].pk}/initial-forecast-configuration/"
    payload = configuration_payload(data["member"].pk, data["admin"].pk)
    api_client.force_authenticate(data["admin"])
    initial = api_client.put(url, payload, format="json")

    update = configuration_payload(data["member"].pk, data["admin"].pk)
    update["accounts"][0]["id"] = initial.data["account_ids"][0]
    update["categories"][0]["id"] = initial.data["category_ids"][0]
    update["categories"][1]["id"] = initial.data["category_ids"][1]
    update["income_forecasts"][0]["id"] = initial.data["income_forecast_ids"][0]
    update["expense_forecasts"][0]["id"] = initial.data["expense_forecast_ids"][0]
    update["budget"]["lines"][0]["id"] = BudgetLine.objects.get(name="Living").pk
    update["budget"]["lines"][1]["id"] = BudgetLine.objects.get(name="Cigarettes").pk
    update["free_money_allowances"][0]["id"] = initial.data["free_money_allowance_ids"][0]
    update["savings_distribution"]["id"] = initial.data["savings_distribution_id"]
    update["income_forecasts"][0]["amount"] = "150.00"
    update["budget"]["lines"][0]["amount"] = "90.00"

    response = api_client.put(url, update, format="json")

    assert response.status_code == status.HTTP_200_OK
    assert IncomeForecast.objects.count() == 1
    assert ExpenseForecast.objects.count() == 1
    assert MonthlyBudgetForecast.objects.count() == 1
    assert IncomeForecast.objects.get().amount == Decimal("150.00")
    assert list(ExpenseForecastAllocation.objects.values_list("amount", flat=True)) == [Decimal("93.00"), Decimal("93.00")]
    assert BudgetLine.objects.get(name="Living").amount == Decimal("90.00")


def test_configuration_rejects_duplicate_cigarettes_and_budget_totals(api_client, configuration_records):
    data = configuration_records
    url = f"/api/v1/families/{data['family'].pk}/initial-forecast-configuration/"
    payload = configuration_payload(data["member"].pk, data["admin"].pk)
    payload["expense_forecasts"].append(payload["expense_forecasts"][0].copy())
    payload["budget"]["lines"].append({"name": "cigarettes", "amount": "20.00"})
    api_client.force_authenticate(data["admin"])

    response = api_client.put(url, payload, format="json")

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert ExpenseForecast.objects.count() == 0
    assert MonthlyBudgetForecast.objects.count() == 0


def test_configuration_requires_fixed_cigarettes_values_and_single_budget_line(api_client, configuration_records):
    data = configuration_records
    url = f"/api/v1/families/{data['family'].pk}/initial-forecast-configuration/"
    api_client.force_authenticate(data["admin"])
    payload = configuration_payload(data["member"].pk, data["admin"].pk)
    payload["expense_forecasts"][0]["amount"] = "185.99"

    amount_response = api_client.put(url, payload, format="json")
    payload = configuration_payload(data["member"].pk, data["admin"].pk)
    payload["expense_forecasts"][0]["allocations"][1]["amount"] = "92.99"
    allocation_response = api_client.put(url, payload, format="json")
    payload = configuration_payload(data["member"].pk, data["admin"].pk)
    payload["budget"]["lines"][1]["amount"] = "185.99"
    budget_response = api_client.put(url, payload, format="json")

    assert amount_response.status_code == status.HTTP_400_BAD_REQUEST
    assert allocation_response.status_code == status.HTTP_400_BAD_REQUEST
    assert budget_response.status_code == status.HTTP_400_BAD_REQUEST
    assert ExpenseForecast.objects.count() == 0


def test_configuration_requires_and_audits_private_to_shared_confirmation(api_client, configuration_records):
    data = configuration_records
    account = LogicalAccount.objects.create(
        family=data["family"], owner=data["admin"], name="Private account"
    )
    url = f"/api/v1/families/{data['family'].pk}/initial-forecast-configuration/"
    api_client.force_authenticate(data["admin"])
    payload = configuration_payload(data["member"].pk, data["admin"].pk)
    payload["accounts"][0] = {"id": account.pk, "key": "shared", "name": "Shared account", "owner_id": None}

    rejected = api_client.put(url, payload, format="json")
    account.refresh_from_db()
    assert account.owner_id == data["admin"].pk
    payload = configuration_payload(data["member"].pk, data["admin"].pk)
    payload["accounts"][0] = {"id": account.pk, "key": "shared", "name": "Shared account", "owner_id": None}
    payload["privacy_impact_confirmed"] = True
    accepted = api_client.put(url, payload, format="json")
    account.refresh_from_db()

    assert rejected.status_code == status.HTTP_400_BAD_REQUEST
    assert accepted.status_code == status.HTTP_200_OK
    assert account.owner_id is None
    assert AuditLog.objects.filter(
        action="initial_forecast_configuration.updated",
        metadata__privacy_impact_confirmed=True,
        metadata__private_to_shared_transitions=[{"entity_type": "logicalaccount", "entity_id": account.pk}],
    ).exists()


def test_configuration_rejects_replayed_budget_lines_without_ids(api_client, configuration_records):
    data = configuration_records
    url = f"/api/v1/families/{data['family'].pk}/initial-forecast-configuration/"
    payload = configuration_payload(data["member"].pk, data["admin"].pk)
    api_client.force_authenticate(data["admin"])

    initial = api_client.put(url, payload, format="json")
    replay = configuration_payload(data["member"].pk, data["admin"].pk)
    replay["accounts"][0]["id"] = initial.data["account_ids"][0]
    replay["categories"][0]["id"] = initial.data["category_ids"][0]
    replay["categories"][1]["id"] = initial.data["category_ids"][1]
    replay["income_forecasts"][0]["id"] = initial.data["income_forecast_ids"][0]
    replay["expense_forecasts"][0]["id"] = initial.data["expense_forecast_ids"][0]
    replay["free_money_allowances"][0]["id"] = initial.data["free_money_allowance_ids"][0]
    replay["savings_distribution"]["id"] = initial.data["savings_distribution_id"]
    replay = api_client.put(url, replay, format="json")

    assert initial.status_code == status.HTTP_200_OK
    assert replay.status_code == status.HTTP_400_BAD_REQUEST
    assert "budget" in replay.data
    assert BudgetLine.objects.count() == 2
