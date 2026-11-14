from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError
from rest_framework import status

from apps.audit.models import AuditLog
from apps.expenses.models import ExpenseMovement, MovementStatus
from apps.finance.models import Category, LogicalAccount
from apps.incomes.models import IncomeForecast, IncomeMovement

pytestmark = pytest.mark.django_db


@pytest.fixture
def finance_records(family_factory, membership_factory, user_factory):
    jalberth = user_factory("jalberth")
    raiza = user_factory("raiza")
    family = family_factory("Family")
    membership_factory(family, jalberth, role="ADMIN")
    membership_factory(family, raiza)
    shared_account = LogicalAccount.objects.create(family=family, name="Shared account")
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
        "account": shared_account,
        "income_category": income_category,
        "expense_category": expense_category,
    }


def test_raiza_cannot_list_or_retrieve_jalberth_private_income_forecast(
    api_client, finance_records
):
    data = finance_records
    forecast = IncomeForecast.objects.create(
        family=data["family"],
        owner=data["jalberth"],
        account=data["account"],
        category=data["income_category"],
        amount=Decimal("100.00"),
        occurred_on="2026-12-01",
        effective_date="2026-12-01",
    )
    api_client.force_authenticate(data["raiza"])

    list_response = api_client.get(f"/api/v1/families/{data['family'].pk}/income-forecasts/")
    detail_response = api_client.get(
        f"/api/v1/families/{data['family'].pk}/income-forecasts/{forecast.pk}/"
    )

    assert list_response.data == []
    assert detail_response.status_code == status.HTTP_404_NOT_FOUND


def test_income_forecast_crud_keeps_decimal_amount(api_client, finance_records):
    data = finance_records
    api_client.force_authenticate(data["jalberth"])
    url = f"/api/v1/families/{data['family'].pk}/income-forecasts/"
    payload = {
        "owner_id": data["jalberth"].pk,
        "account_id": data["account"].pk,
        "category_id": data["income_category"].pk,
        "amount": "123.45",
        "occurred_on": "2026-12-01",
        "effective_date": "2026-12-01",
        "recurrence": "MONTHLY",
    }

    create_response = api_client.post(url, payload, format="json")
    forecast_id = create_response.data["id"]
    update_response = api_client.patch(
        f"{url}{forecast_id}/", {"amount": "200.10"}, format="json"
    )

    assert create_response.status_code == status.HTTP_201_CREATED
    assert IncomeForecast.objects.get(pk=forecast_id).amount == Decimal("200.10")
    assert update_response.status_code == status.HTTP_200_OK
    delete_response = api_client.delete(f"{url}{forecast_id}/")
    assert delete_response.status_code == status.HTTP_204_NO_CONTENT


def test_shared_expense_requires_allocations_that_exactly_sum_to_amount(
    api_client, finance_records
):
    data = finance_records
    api_client.force_authenticate(data["raiza"])
    url = f"/api/v1/families/{data['family'].pk}/expense-movements/"
    payload = {
        "account_id": data["account"].pk,
        "category_id": data["expense_category"].pk,
        "amount": "186.00",
        "occurred_on": "2026-12-01",
        "allocations": [
            {"member_id": data["jalberth"].pk, "amount": "93.00"},
            {"member_id": data["raiza"].pk, "amount": "92.99"},
        ],
    }

    invalid_response = api_client.post(url, payload, format="json")
    payload["allocations"][1]["amount"] = "93.00"
    valid_response = api_client.post(url, payload, format="json")

    assert invalid_response.status_code == status.HTTP_400_BAD_REQUEST
    assert valid_response.status_code == status.HTTP_201_CREATED
    assert ExpenseMovement.objects.get(pk=valid_response.data["id"]).amount == Decimal("186.00")


def test_voiding_confirmed_movement_is_audited_and_never_deletes_it(
    api_client, finance_records
):
    data = finance_records
    movement = IncomeMovement.objects.create(
        family=data["family"],
        owner=data["jalberth"],
        account=data["account"],
        category=data["income_category"],
        amount=Decimal("100.00"),
        occurred_on="2026-12-01",
    )
    api_client.force_authenticate(data["jalberth"])
    base_url = f"/api/v1/families/{data['family'].pk}/income-movements/{movement.pk}/"

    delete_response = api_client.delete(base_url)
    with pytest.raises(ValidationError):
        IncomeMovement.objects.filter(pk=movement.pk).delete()
    void_response = api_client.post(f"{base_url}void/", {"reason": "Duplicate"}, format="json")
    movement.refresh_from_db()

    assert delete_response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED
    assert void_response.status_code == status.HTTP_200_OK
    assert movement.status == MovementStatus.VOIDED
    assert movement.void_reason == "Duplicate"
    assert AuditLog.objects.filter(
        action="income_movement.voided", entity_id=movement.pk, metadata={"reason": "Duplicate"}
    ).exists()
