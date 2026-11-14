from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError
from rest_framework import status

from apps.audit.models import AuditLog
from apps.expenses.models import ExpenseMovement
from apps.savings.models import (
    MatiasFund,
    MatiasFundAllocation,
    MatiasFundMovement,
    SavingsGoal,
    SavingsMovement,
)
from apps.savings.services import void_savings_movement

pytestmark = pytest.mark.django_db


@pytest.fixture
def savings_records(family_factory, membership_factory, user_factory):
    jalberth = user_factory("jalberth")
    raiza = user_factory("raiza")
    family = family_factory("Family")
    membership_factory(family, jalberth, role="ADMIN")
    membership_factory(family, raiza)
    return {"jalberth": jalberth, "raiza": raiza, "family": family}


def test_raiza_cannot_see_jalberth_private_savings_goal_or_movement(api_client, savings_records):
    data = savings_records
    private_goal = SavingsGoal.objects.create(
        family=data["family"], owner=data["jalberth"], name="Jalberth", target_amount="1000.00"
    )
    movement = SavingsMovement.objects.create(
        goal=private_goal, kind="CONTRIBUTION", amount="100.00", occurred_on="2026-12-01"
    )
    api_client.force_authenticate(data["raiza"])

    goals_url = f"/api/v1/families/{data['family'].pk}/savings-goals/"
    movements_url = f"/api/v1/families/{data['family'].pk}/savings-movements/"

    assert api_client.get(goals_url).data == []
    assert api_client.get(f"{goals_url}{private_goal.pk}/").status_code == status.HTTP_404_NOT_FOUND
    assert api_client.get(movements_url).data == []
    assert api_client.get(f"{movements_url}{movement.pk}/").status_code == status.HTTP_404_NOT_FOUND


def test_real_savings_balance_uses_only_confirmed_movements_and_simulation_is_not_persisted(api_client, savings_records):
    data = savings_records
    goal = SavingsGoal.objects.create(
        family=data["family"], name="Shared", target_amount="1000.00", projected_balance="800.00"
    )
    SavingsMovement.objects.create(goal=goal, kind="CONTRIBUTION", amount="100.00", occurred_on="2026-12-01")
    SavingsMovement.objects.create(goal=goal, kind="WITHDRAWAL", amount="25.00", occurred_on="2026-12-02")
    SavingsMovement.objects.create(goal=goal, kind="ADJUSTMENT", amount="-10.00", occurred_on="2026-12-03")
    voided = SavingsMovement.objects.create(goal=goal, kind="CONTRIBUTION", amount="200.00", occurred_on="2026-12-04")
    void_savings_movement(actor=data["jalberth"], movement=voided, reason="Test void")
    api_client.force_authenticate(data["raiza"])

    response = api_client.post(
        f"/api/v1/families/{data['family'].pk}/savings-goals/{goal.pk}/simulate/",
        {"projected_monthly_contribution": "50.00", "months": 3},
        format="json",
    )
    goal.refresh_from_db()

    assert goal.real_balance == Decimal("65.00")
    assert response.status_code == status.HTTP_200_OK
    assert Decimal(response.data["simulated_balance"]) == Decimal("215.00")
    assert goal.projected_balance == Decimal("800.00")


def test_savings_void_and_correction_are_audited_and_immutable(api_client, savings_records):
    data = savings_records
    goal = SavingsGoal.objects.create(family=data["family"], name="Shared", target_amount="1000.00")
    movement = SavingsMovement.objects.create(
        goal=goal, kind="CONTRIBUTION", amount="100.00", occurred_on="2026-12-01"
    )
    api_client.force_authenticate(data["raiza"])
    base_url = f"/api/v1/families/{data['family'].pk}/savings-movements/{movement.pk}/"

    delete_response = api_client.delete(base_url)
    correction = api_client.post(
        f"{base_url}correct/",
        {"reason": "Wrong amount", "kind": "CONTRIBUTION", "amount": "120.00", "occurred_on": "2026-12-01"},
        format="json",
    )
    movement.refresh_from_db()

    assert delete_response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED
    assert correction.status_code == status.HTTP_201_CREATED
    assert movement.status == "VOIDED"
    assert SavingsMovement.objects.get(pk=correction.data["id"]).corrects_id == movement.pk
    assert goal.real_balance == Decimal("120.00")
    assert AuditLog.objects.filter(action="savings_movement.voided", entity_id=movement.pk).exists()
    with pytest.raises(ValidationError):
        SavingsMovement.objects.filter(pk=movement.pk).update(amount="999.00")
    with pytest.raises(ValidationError):
        SavingsMovement.objects.filter(pk=movement.pk).delete()


def test_matias_fund_is_shared_and_replenishment_is_not_savings_or_consumption(api_client, savings_records):
    data = savings_records
    api_client.force_authenticate(data["jalberth"])
    fund_url = f"/api/v1/families/{data['family'].pk}/matias-fund/"
    create_response = api_client.post(fund_url, {"target_amount": "1000.00", "projected_balance": "500.00"}, format="json")
    fund = MatiasFund.objects.get(family=data["family"])
    movements_url = f"/api/v1/families/{data['family'].pk}/matias-fund-movements/"
    payload = {
        "kind": "REPLENISHMENT",
        "amount": "100.00",
        "occurred_on": "2026-12-01",
        "allocations": [
            {"contributor_id": data["jalberth"].pk, "amount": "50.00"},
            {"contributor_id": data["raiza"].pk, "amount": "50.00"},
        ],
    }
    movement_response = api_client.post(movements_url, payload, format="json")
    api_client.force_authenticate(data["raiza"])

    assert create_response.status_code == status.HTTP_201_CREATED
    assert movement_response.status_code == status.HTTP_201_CREATED
    assert api_client.get(fund_url).status_code == status.HTTP_200_OK
    assert api_client.get(movements_url).data[0]["kind"] == "REPLENISHMENT"
    assert fund.real_balance == Decimal("100.00")
    assert SavingsMovement.objects.count() == 0
    assert ExpenseMovement.objects.count() == 0
    allocation = MatiasFundAllocation.objects.filter(
        movement_id=movement_response.data["id"]
    ).first()
    assert allocation is not None
    with pytest.raises(ValidationError):
        allocation.delete()


def test_matias_fund_rejects_non_exact_contributor_allocations(api_client, savings_records):
    data = savings_records
    fund = MatiasFund.objects.create(family=data["family"], target_amount="1000.00")
    api_client.force_authenticate(data["raiza"])

    response = api_client.post(
        f"/api/v1/families/{data['family'].pk}/matias-fund-movements/",
        {
            "kind": "INITIAL_CONTRIBUTION",
            "amount": "100.00",
            "occurred_on": "2026-12-01",
            "allocations": [{"contributor_id": data["raiza"].pk, "amount": "99.99"}],
        },
        format="json",
    )

    assert fund.real_balance == Decimal("0.00")
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert MatiasFundMovement.objects.count() == 0
