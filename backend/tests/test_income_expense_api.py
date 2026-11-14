from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError
from rest_framework import status

from apps.audit.models import AuditLog
from apps.expenses.models import ExpenseAllocation, ExpenseMovement
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


def test_correcting_confirmed_income_creates_immutable_reversal_and_replacement(
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
    direct_save = pytest.raises(ValidationError)
    with direct_save:
        movement.description = "Mutated"
        movement.save()
    correction_response = api_client.post(
        f"{base_url}correct/",
        {
            "reason": "Duplicate",
            "owner_id": data["jalberth"].pk,
            "account_id": data["account"].pk,
            "category_id": data["income_category"].pk,
            "amount": "120.00",
            "occurred_on": "2026-12-02",
            "description": "Corrected",
        },
        format="json",
    )
    movement.refresh_from_db()

    assert delete_response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED
    assert correction_response.status_code == status.HTTP_201_CREATED
    assert movement.description == ""
    reversal_id = correction_response.data["reversal"]["id"]
    replacement_id = correction_response.data["replacement"]["id"]
    assert IncomeMovement.objects.get(pk=reversal_id).reversal_of_id == movement.pk
    assert IncomeMovement.objects.get(pk=replacement_id).replaces_id == movement.pk
    assert AuditLog.objects.filter(
        action="income_movement.corrected",
        entity_id=movement.pk,
        metadata={"reason": "Duplicate", "reversal_id": reversal_id, "replacement_id": replacement_id},
    ).exists()


def test_correcting_expense_is_atomic_and_preserves_allocation_snapshots(api_client, finance_records):
    data = finance_records
    movement = ExpenseMovement.objects.create(
        family=data["family"],
        account=data["account"],
        category=data["expense_category"],
        amount=Decimal("186.00"),
        occurred_on="2026-12-01",
    )
    ExpenseAllocation.objects.create(
        movement=movement, member=data["jalberth"], amount=Decimal("93.00")
    )
    ExpenseAllocation.objects.create(
        movement=movement, member=data["raiza"], amount=Decimal("93.00")
    )
    api_client.force_authenticate(data["raiza"])
    url = f"/api/v1/families/{data['family'].pk}/expense-movements/{movement.pk}/correct/"
    payload = {
        "reason": "Wrong amount",
        "account_id": data["account"].pk,
        "category_id": data["expense_category"].pk,
        "amount": "200.00",
        "occurred_on": "2026-12-02",
        "allocations": [{"member_id": data["raiza"].pk, "amount": "200.00"}],
    }

    invalid_response = api_client.post(url, {**payload, "allocations": []}, format="json")

    assert invalid_response.status_code == status.HTTP_400_BAD_REQUEST
    assert ExpenseMovement.objects.count() == 1
    valid_response = api_client.post(url, payload, format="json")

    assert valid_response.status_code == status.HTTP_201_CREATED
    reversal = ExpenseMovement.objects.get(pk=valid_response.data["reversal"]["id"])
    replacement = ExpenseMovement.objects.get(pk=valid_response.data["replacement"]["id"])
    assert reversal.reversal_of_id == movement.pk
    assert replacement.replaces_id == movement.pk
    assert list(reversal.allocations.values_list("amount", flat=True)) == [Decimal("93.00"), Decimal("93.00")]


@pytest.mark.parametrize("model", [IncomeMovement, ExpenseMovement])
def test_confirmed_movements_reject_queryset_updates(model, finance_records):
    data = finance_records
    movement = model.objects.create(
        family=data["family"],
        owner=data["jalberth"],
        account=data["account"],
        category=data["income_category"] if model is IncomeMovement else data["expense_category"],
        amount=Decimal("100.00"),
        occurred_on="2026-12-01",
    )

    with pytest.raises(ValidationError):
        model.objects.filter(pk=movement.pk).update(amount=Decimal("101.00"))
