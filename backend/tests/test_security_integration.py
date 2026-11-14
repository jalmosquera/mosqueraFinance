from datetime import date
from decimal import Decimal

import pytest
from django.core.cache import cache
from django.test import Client, override_settings
from rest_framework import status

from apps.audit.models import AuditLog
from apps.expenses.models import ExpenseAllocation, ExpenseForecast, ExpenseMovement
from apps.finance.models import Category, LogicalAccount
from apps.incomes.models import IncomeForecast, IncomeMovement, Recurrence
from apps.obligations.models import PaymentObligation
from apps.savings.models import SavingsGoal, SavingsMovement

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def clear_login_attempts():
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def private_finance_records(family_factory, membership_factory, user_factory):
    jalberth = user_factory("jalberth")
    raiza = user_factory("raiza")
    family = family_factory("Family")
    membership_factory(family, jalberth, role="ADMIN")
    membership_factory(family, raiza)
    account = LogicalAccount.objects.create(family=family, name="Shared account")
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


def test_raiza_isolated_from_private_finance_endpoints(api_client, private_finance_records):
    data = private_finance_records
    private_account = LogicalAccount.objects.create(
        family=data["family"], owner=data["jalberth"], name="Jalberth account"
    )
    private_category = Category.objects.create(
        family=data["family"],
        owner=data["jalberth"],
        name="Jalberth income",
        kind=Category.Kind.INCOME,
    )
    income_forecast = IncomeForecast.objects.create(
        family=data["family"],
        owner=data["jalberth"],
        account=data["account"],
        category=data["income_category"],
        amount=Decimal("9000.00"),
        occurred_on=date(2026, 1, 1),
        effective_date=date(2026, 1, 1),
        recurrence=Recurrence.MONTHLY,
    )
    expense_forecast = ExpenseForecast.objects.create(
        family=data["family"],
        owner=data["jalberth"],
        account=data["account"],
        category=data["expense_category"],
        amount=Decimal("8000.00"),
        occurred_on=date(2026, 1, 1),
        effective_date=date(2026, 1, 1),
        recurrence=Recurrence.MONTHLY,
    )
    income_movement = IncomeMovement.objects.create(
        family=data["family"],
        owner=data["jalberth"],
        account=data["account"],
        category=data["income_category"],
        amount=Decimal("7000.00"),
        occurred_on=date(2026, 1, 1),
    )
    expense_movement = ExpenseMovement.objects.create(
        family=data["family"],
        owner=data["jalberth"],
        account=data["account"],
        category=data["expense_category"],
        amount=Decimal("6000.00"),
        occurred_on=date(2026, 1, 1),
    )
    private_goal = SavingsGoal.objects.create(
        family=data["family"],
        owner=data["jalberth"],
        name="Jalberth savings",
        target_amount=Decimal("10000.00"),
    )
    savings_movement = SavingsMovement.objects.create(
        goal=private_goal,
        kind=SavingsMovement.Kind.CONTRIBUTION,
        amount=Decimal("5000.00"),
        occurred_on=date(2026, 1, 1),
    )
    api_client.force_authenticate(data["raiza"])
    family_url = f"/api/v1/families/{data['family'].pk}/"

    endpoints = (
        ("logical-accounts/", private_account.pk),
        ("categories/", private_category.pk),
        ("income-forecasts/", income_forecast.pk),
        ("expense-forecasts/", expense_forecast.pk),
        ("income-movements/", income_movement.pk),
        ("expense-movements/", expense_movement.pk),
        ("savings-goals/", private_goal.pk),
        ("savings-movements/", savings_movement.pk),
    )
    for segment, record_id in endpoints:
        list_response = api_client.get(f"{family_url}{segment}")
        detail_response = api_client.get(f"{family_url}{segment}{record_id}/")

        assert list_response.status_code == status.HTTP_200_OK
        assert record_id not in [record["id"] for record in list_response.data]
        assert detail_response.status_code == status.HTTP_404_NOT_FOUND
        assert b"9000" not in list_response.content


def test_raiza_cannot_access_private_obligations_or_financial_projections(
    api_client, private_finance_records
):
    data = private_finance_records
    month = date(2026, 2, 1)
    forecast = IncomeForecast.objects.create(
        family=data["family"],
        owner=data["jalberth"],
        account=data["account"],
        category=data["income_category"],
        amount=Decimal("9000.00"),
        occurred_on=month,
        effective_date=month,
        recurrence=Recurrence.MONTHLY,
    )
    obligation = PaymentObligation.objects.create(
        family=data["family"],
        income_forecast=forecast,
        source_period=month,
        owner=data["jalberth"],
        account=data["account"],
        category=data["income_category"],
        amount=forecast.amount,
        due_on=month,
    )
    api_client.force_authenticate(data["raiza"])
    obligations_url = f"/api/v1/families/{data['family'].pk}/payment-obligations/"

    list_response = api_client.get(obligations_url, {"month": month.isoformat()})
    detail_response = api_client.get(f"{obligations_url}{obligation.pk}/")
    projection_response = api_client.post(
        f"/api/v1/families/{data['family'].pk}/projections/scenario/",
        {"start_month": month.isoformat()},
        format="json",
    )
    projected_savings_response = api_client.post(
        f"/api/v1/families/{data['family'].pk}/budgets/projected-savings/",
        {"month": month.isoformat(), "projected_income": "9000.00"},
        format="json",
    )

    assert list_response.data == []
    assert detail_response.status_code == status.HTTP_404_NOT_FOUND
    assert projection_response.status_code == status.HTTP_200_OK
    assert b"9000" not in projection_response.content
    assert projected_savings_response.status_code == status.HTTP_403_FORBIDDEN


def test_voided_confirmed_expense_retains_allocations_and_audit_record(
    api_client, private_finance_records
):
    data = private_finance_records
    movement = ExpenseMovement.objects.create(
        family=data["family"],
        account=data["account"],
        category=data["expense_category"],
        amount=Decimal("186.00"),
        occurred_on=date(2026, 1, 1),
    )
    allocation = ExpenseAllocation.objects.create(
        movement=movement, member=data["raiza"], amount=Decimal("186.00")
    )
    api_client.force_authenticate(data["raiza"])

    response = api_client.post(
        f"/api/v1/families/{data['family'].pk}/expense-movements/{movement.pk}/void/",
        {"reason": "Duplicate"},
        format="json",
    )
    movement.refresh_from_db()

    assert response.status_code == status.HTTP_200_OK
    assert movement.status == "VOIDED"
    assert ExpenseAllocation.objects.get(pk=allocation.pk).movement_id == movement.pk
    assert AuditLog.objects.filter(
        actor=data["raiza"],
        action="expense_movement.voided",
        entity_id=movement.pk,
        metadata={"reason": "Duplicate"},
    ).exists()


def test_shared_expense_rejects_duplicate_or_non_member_allocations(
    api_client, private_finance_records, user_factory
):
    data = private_finance_records
    outsider = user_factory("outsider")
    api_client.force_authenticate(data["raiza"])
    url = f"/api/v1/families/{data['family'].pk}/expense-movements/"
    payload = {
        "account_id": data["account"].pk,
        "category_id": data["expense_category"].pk,
        "amount": "186.00",
        "occurred_on": "2026-01-01",
        "allocations": [
            {"member_id": data["raiza"].pk, "amount": "93.00"},
            {"member_id": data["raiza"].pk, "amount": "93.00"},
        ],
    }

    duplicate_response = api_client.post(url, payload, format="json")
    payload["allocations"][1]["member_id"] = outsider.pk
    outsider_response = api_client.post(url, payload, format="json")

    assert duplicate_response.status_code == status.HTTP_400_BAD_REQUEST
    assert outsider_response.status_code == status.HTTP_400_BAD_REQUEST
    assert ExpenseMovement.objects.count() == 0


@override_settings(LOGIN_ATTEMPT_LIMIT=1, LOGIN_ATTEMPT_WINDOW_SECONDS=60)
def test_session_login_requires_csrf_and_rate_limits_case_insensitively(user_factory):
    user_factory("raiza")
    client = Client(enforce_csrf_checks=True)
    missing_token = client.post(
        "/api/v1/auth/login/",
        data={"username": "raiza", "password": "wrong-password"},
        content_type="application/json",
    )
    client.get("/api/v1/auth/csrf/")
    csrf_token = client.cookies["csrftoken"].value
    first_attempt = client.post(
        "/api/v1/auth/login/",
        data={"username": "RAIZA", "password": "wrong-password"},
        content_type="application/json",
        HTTP_X_CSRFTOKEN=csrf_token,
    )
    blocked_attempt = client.post(
        "/api/v1/auth/login/",
        data={"username": "raiza", "password": "wrong-password"},
        content_type="application/json",
        HTTP_X_CSRFTOKEN=csrf_token,
    )

    assert missing_token.status_code == status.HTTP_403_FORBIDDEN
    assert first_attempt.status_code == status.HTTP_400_BAD_REQUEST
    assert blocked_attempt.status_code == status.HTTP_429_TOO_MANY_REQUESTS


def test_health_endpoint_only_allows_get(api_client):
    healthy = api_client.get("/healthz")
    rejected_method = api_client.post("/healthz", format="json")

    assert healthy.status_code == status.HTTP_200_OK
    assert healthy.json() == {"status": "ok"}
    assert rejected_method.status_code == status.HTTP_405_METHOD_NOT_ALLOWED
