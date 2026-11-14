from datetime import date

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from rest_framework import status

from apps.accounts.models import User
from apps.audit.models import AuditLog
from apps.budgets.models import BudgetLine, BudgetMonthClose, MonthlyBudgetForecast
from apps.families.models import Family, FamilyMembership

pytestmark = pytest.mark.django_db


def test_staff_only_bootstrap_creates_jalberth_family_and_no_financial_values(api_client, user_factory):
    operator = user_factory("operator")
    operator.is_staff = True
    operator.save(update_fields=("is_staff",))
    api_client.force_authenticate(operator)

    response = api_client.post(
        "/api/v1/admin/family-bootstrap/",
        {"email": "jalberth@example.test", "password": "initial-password", "family_name": "Mosquera Alves"},
        format="json",
    )

    assert response.status_code == status.HTTP_201_CREATED
    jalberth = User.objects.get(username="jalberth")
    family = Family.objects.get(name="Mosquera Alves")
    assert FamilyMembership.objects.get(family=family, user=jalberth).role == FamilyMembership.Role.ADMIN
    assert MonthlyBudgetForecast.objects.count() == 0
    assert AuditLog.objects.filter(action="family.bootstrap_created", family=family).exists()


def test_bootstrap_rejects_non_staff_and_repeated_bootstraps(api_client, user_factory, family_factory):
    user = user_factory("member")
    api_client.force_authenticate(user)
    denied = api_client.post("/api/v1/admin/family-bootstrap/", {}, format="json")

    family_factory("Existing")
    user.is_staff = True
    user.save(update_fields=("is_staff",))
    repeated = api_client.post(
        "/api/v1/admin/family-bootstrap/",
        {"email": "jalberth@example.test", "password": "initial-password", "family_name": "Mosquera Alves"},
        format="json",
    )

    assert denied.status_code == status.HTTP_403_FORBIDDEN
    assert repeated.status_code == status.HTTP_400_BAD_REQUEST
    assert not User.objects.filter(username="jalberth").exists()


def test_bootstrap_management_command_is_one_time():
    call_command(
        "bootstrap_family",
        email="jalberth@example.test",
        password="initial-password",
        family_name="Mosquera Alves",
        noinput=True,
    )

    with pytest.raises(CommandError, match="Bootstrap is only available"):
        call_command(
            "bootstrap_family",
            email="jalberth@example.test",
            password="initial-password",
            family_name="Mosquera Alves",
            noinput=True,
        )


@pytest.fixture
def closed_budget(api_client, family_factory, membership_factory, user_factory):
    admin = user_factory("jalberth")
    member = user_factory("raiza")
    family = family_factory("Family")
    membership_factory(family, admin, role=FamilyMembership.Role.ADMIN)
    membership_factory(family, member)
    forecast = MonthlyBudgetForecast.objects.create(family=family, month=date(2026, 1, 1), version=1)
    BudgetLine.objects.create(forecast=forecast, name="Living", amount="100.00")
    api_client.force_authenticate(admin)
    close = api_client.post(
        f"/api/v1/families/{family.pk}/budget-forecasts/{forecast.pk}/close/", format="json"
    )
    return {"admin": admin, "member": member, "family": family, "forecast": forecast, "close": close}


def test_budget_close_snapshots_and_audits(closed_budget):
    data = closed_budget

    assert data["close"].status_code == status.HTTP_201_CREATED
    close = BudgetMonthClose.objects.get()
    assert close.snapshot == {
        "forecast_id": data["forecast"].pk,
        "month": "2026-01-01",
        "version": 1,
        "lines": [{"id": BudgetLine.objects.get().pk, "name": "Living", "amount": "100.00", "kind": "STANDARD", "replaces_id": None}],
    }
    assert AuditLog.objects.filter(action="budget_month.closed", entity_id=close.pk).exists()


def test_closed_month_rejects_ordinary_changes_and_requires_admin(api_client, closed_budget):
    data = closed_budget
    api_client.force_authenticate(data["member"])
    non_admin = api_client.post(
        f"/api/v1/families/{data['family'].pk}/budget-forecasts/{data['forecast'].pk}/historical-corrections/",
        {"reason": "Fix", "lines": [{"name": "Living", "amount": "110.00"}]},
        format="json",
    )
    api_client.force_authenticate(data["admin"])
    ordinary_forecast = api_client.post(
        f"/api/v1/families/{data['family'].pk}/budget-forecasts/",
        {"month": "2026-01-01", "version": 2, "lines": [{"name": "Living", "amount": "110.00"}]},
        format="json",
    )
    ordinary_line = api_client.post(
        f"/api/v1/families/{data['family'].pk}/budget-forecasts/{data['forecast'].pk}/lines/",
        {"name": "Unexpected", "amount": "1.00"},
        format="json",
    )

    assert non_admin.status_code == status.HTTP_403_FORBIDDEN
    assert ordinary_forecast.status_code == status.HTTP_400_BAD_REQUEST
    assert ordinary_line.status_code == status.HTTP_400_BAD_REQUEST


def test_historical_correction_requires_reason_and_creates_audited_version(api_client, closed_budget):
    data = closed_budget
    url = f"/api/v1/families/{data['family'].pk}/budget-forecasts/{data['forecast'].pk}/historical-corrections/"
    missing_reason = api_client.post(
        url, {"lines": [{"name": "Living", "amount": "110.00"}]}, format="json"
    )
    corrected = api_client.post(
        url,
        {"reason": "Corrected the January receipt", "lines": [{"name": "Living", "amount": "110.00"}]},
        format="json",
    )

    assert missing_reason.status_code == status.HTTP_400_BAD_REQUEST
    assert corrected.status_code == status.HTTP_201_CREATED
    correction = MonthlyBudgetForecast.objects.get(pk=corrected.data["id"])
    assert correction.version == 2
    assert list(correction.lines.values_list("amount", flat=True)) == [110]
    assert list(data["forecast"].lines.values_list("amount", flat=True)) == [100]
    assert AuditLog.objects.filter(
        action="budget_forecast.historically_corrected",
        entity_id=correction.pk,
        metadata__reason="Corrected the January receipt",
    ).exists()
