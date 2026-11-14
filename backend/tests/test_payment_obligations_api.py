from datetime import date
from decimal import Decimal

import pytest
from django.utils import timezone
from rest_framework import status

from apps.finance.models import Category, LogicalAccount
from apps.incomes.models import IncomeForecast, IncomeMovement
from apps.obligations.models import ObligationStatus, PaymentObligation

pytestmark = pytest.mark.django_db


@pytest.fixture
def obligation_records(family_factory, membership_factory, user_factory):
    first_member = user_factory("first-member")
    second_member = user_factory("second-member")
    family = family_factory("Test family")
    membership_factory(family, first_member, role="ADMIN")
    membership_factory(family, second_member)
    account = LogicalAccount.objects.create(family=family, name="Checking")
    income_category = Category.objects.create(
        family=family, name="Salary", kind=Category.Kind.INCOME
    )
    return {
        "first_member": first_member,
        "second_member": second_member,
        "family": family,
        "account": account,
        "income_category": income_category,
    }


def month_start(value):
    return value.replace(day=1)


def next_month(value):
    return date(value.year + (value.month == 12), value.month % 12 + 1, 1)


def test_calendar_materializes_monthly_occurrences_after_effective_date(
    api_client, obligation_records
):
    data = obligation_records
    effective_date = date(2030, 1, 20)
    forecast = IncomeForecast.objects.create(
        family=data["family"],
        owner=data["first_member"],
        account=data["account"],
        category=data["income_category"],
        amount=Decimal("10.00"),
        occurred_on=date(2030, 1, 15),
        effective_date=effective_date,
        recurrence="MONTHLY",
    )
    api_client.force_authenticate(data["first_member"])
    url = f"/api/v1/families/{data['family'].pk}/payment-obligations/"

    january = api_client.post(url + "generate/", {"month": "2030-01-01"}, format="json")
    february = api_client.post(url + "generate/", {"month": "2030-02-01"}, format="json")

    assert january.status_code == status.HTTP_200_OK
    assert january.data == []
    assert february.status_code == status.HTTP_200_OK
    assert february.data[0]["income_forecast_id"] == forecast.pk
    assert february.data[0]["due_on"] == "2030-02-15"
    assert february.data[0]["status"] == ObligationStatus.PENDING


def test_forecast_edits_preserve_historical_obligation_snapshot(
    api_client, obligation_records
):
    data = obligation_records
    today = timezone.localdate()
    historical_month = month_start(today.replace(year=today.year - 1))
    future_month = next_month(month_start(today))
    forecast = IncomeForecast.objects.create(
        family=data["family"],
        owner=data["first_member"],
        account=data["account"],
        category=data["income_category"],
        amount=Decimal("10.00"),
        occurred_on=historical_month.replace(day=1),
        effective_date=historical_month,
        recurrence="MONTHLY",
    )
    api_client.force_authenticate(data["first_member"])
    base_url = f"/api/v1/families/{data['family'].pk}/payment-obligations/"
    api_client.post(base_url + "generate/", {"month": historical_month.isoformat()}, format="json")
    api_client.post(base_url + "generate/", {"month": future_month.isoformat()}, format="json")

    update_response = api_client.patch(
        f"/api/v1/families/{data['family'].pk}/income-forecasts/{forecast.pk}/",
        {"amount": "25.00"},
        format="json",
    )
    future = api_client.post(
        base_url + "generate/", {"month": future_month.isoformat()}, format="json"
    )
    historical = PaymentObligation.objects.get(
        income_forecast=forecast, source_period=historical_month
    )

    assert update_response.status_code == status.HTTP_200_OK
    assert historical.amount == Decimal("10.00")
    assert future.data[0]["amount"] == "25.00"


def test_listing_obligations_never_materializes_forecasts(api_client, obligation_records):
    data = obligation_records
    month = date(2030, 2, 1)
    IncomeForecast.objects.create(
        family=data["family"], owner=data["first_member"], account=data["account"],
        category=data["income_category"], amount=Decimal("10.00"), occurred_on=month,
        effective_date=month, recurrence="MONTHLY",
    )
    api_client.force_authenticate(data["first_member"])

    response = api_client.get(
        f"/api/v1/families/{data['family'].pk}/payment-obligations/", {"month": month.isoformat()}
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.data == []
    assert not PaymentObligation.objects.exists()


def test_settlement_marks_paid_and_rejects_a_second_settlement(api_client, obligation_records):
    data = obligation_records
    month = next_month(month_start(timezone.localdate()))
    forecast = IncomeForecast.objects.create(
        family=data["family"],
        owner=data["first_member"],
        account=data["account"],
        category=data["income_category"],
        amount=Decimal("10.00"),
        occurred_on=month.replace(day=1),
        effective_date=month,
        recurrence="MONTHLY",
    )
    api_client.force_authenticate(data["first_member"])
    list_url = f"/api/v1/families/{data['family'].pk}/payment-obligations/"
    generated = api_client.post(list_url + "generate/", {"month": month.isoformat()}, format="json")
    obligation_url = f"{list_url}{generated.data[0]['id']}/settle/"

    settled = api_client.post(obligation_url, {}, format="json")
    repeated = api_client.post(obligation_url, {}, format="json")
    obligation = PaymentObligation.objects.get(income_forecast=forecast, source_period=month)

    assert settled.status_code == status.HTTP_200_OK
    assert settled.data["status"] == ObligationStatus.PAID
    assert obligation.income_movement_id is not None
    assert IncomeMovement.objects.filter(pk=obligation.income_movement_id).count() == 1
    assert repeated.status_code == status.HTTP_400_BAD_REQUEST


def test_private_obligations_are_not_exposed_to_other_family_members(
    api_client, obligation_records
):
    data = obligation_records
    month = next_month(month_start(timezone.localdate()))
    forecast = IncomeForecast.objects.create(
        family=data["family"],
        owner=data["first_member"],
        account=data["account"],
        category=data["income_category"],
        amount=Decimal("10.00"),
        occurred_on=month.replace(day=1),
        effective_date=month,
        recurrence="MONTHLY",
    )
    base_url = f"/api/v1/families/{data['family'].pk}/payment-obligations/"
    api_client.force_authenticate(data["first_member"])
    generated = api_client.post(base_url + "generate/", {"month": month.isoformat()}, format="json")
    obligation_id = generated.data[0]["id"]
    api_client.force_authenticate(data["second_member"])

    list_response = api_client.get(base_url, {"month": month.isoformat()})
    detail_response = api_client.get(f"{base_url}{obligation_id}/")

    assert forecast.pk
    assert list_response.status_code == status.HTTP_200_OK
    assert list_response.data == []
    assert detail_response.status_code == status.HTTP_404_NOT_FOUND
