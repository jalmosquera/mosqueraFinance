import pytest
from rest_framework import status

from apps.audit.models import AuditLog
from apps.budgets.models import (
    BudgetLine,
    FreeMoneyAllowance,
    MonthlyBudgetForecast,
    SavingsDistributionRule,
)
from apps.finance.models import Category, LogicalAccount
from apps.incomes.models import IncomeForecast, Recurrence
from apps.savings.models import MatiasFund, SavingsGoal, SavingsMovement

pytestmark = pytest.mark.django_db


@pytest.fixture
def overview_records(family_factory, membership_factory, user_factory):
    jalberth = user_factory("jalberth")
    raiza = user_factory("raiza")
    family = family_factory("Family")
    membership_factory(family, jalberth, role="ADMIN")
    membership_factory(family, raiza)
    return {
        "jalberth": jalberth,
        "raiza": raiza,
        "family": family,
        "account": LogicalAccount.objects.create(family=family, name="Shared"),
        "category": Category.objects.create(family=family, name="Income", kind="INCOME"),
    }


def _configure_approved_planning(data):
    for owner, amount in ((data["jalberth"], "1290.00"), (data["raiza"], "1300.00")):
        IncomeForecast.objects.create(
            family=data["family"], owner=owner, account=data["account"], category=data["category"],
            amount=amount, occurred_on="2026-01-01", effective_date="2026-01-01",
            recurrence=Recurrence.MONTHLY,
        )
    for month in range(1, 13):
        forecast = MonthlyBudgetForecast.objects.create(
            family=data["family"], month=f"2026-{month:02d}-01", version=1
        )
        BudgetLine.objects.create(forecast=forecast, name="Budget", amount="1324.08")
    for owner in (data["jalberth"], data["raiza"]):
        FreeMoneyAllowance.objects.create(
            family=data["family"], owner=owner, amount="150.00", effective_date="2026-01-01"
        )
    SavingsDistributionRule.objects.create(
        family=data["family"], effective_date="2026-01-01",
        first_owner=data["jalberth"], second_owner=data["raiza"],
    )
    jalberth_goal = SavingsGoal.objects.create(
        family=data["family"], owner=data["jalberth"], name="Jalberth goal", target_amount="1000.00"
    )
    raiza_goal = SavingsGoal.objects.create(
        family=data["family"], owner=data["raiza"], name="Raiza goal", target_amount="1000.00"
    )
    family_goal = SavingsGoal.objects.create(
        family=data["family"], name="Family goal", target_amount="2000.00"
    )
    MatiasFund.objects.create(
        family=data["family"], target_amount="500.00", projected_balance="999.99",
        initial_contribution_total="100.00", monthly_simulated_expenditure="30.00",
        monthly_replenishment_total="30.00",
    )
    return jalberth_goal, raiza_goal, family_goal


def test_authority_overview_separates_confirmed_balances_from_approved_planning_and_has_no_side_effects(
    api_client, overview_records
):
    data = overview_records
    jalberth_goal, _, family_goal = _configure_approved_planning(data)
    SavingsMovement.objects.create(
        goal=jalberth_goal, kind="CONTRIBUTION", amount="100.00", occurred_on="2026-01-01"
    )
    SavingsMovement.objects.create(
        goal=family_goal, kind="CONTRIBUTION", amount="50.00", occurred_on="2026-01-01"
    )
    before = (SavingsMovement.objects.count(), AuditLog.objects.count())
    api_client.force_authenticate(data["jalberth"])

    response = api_client.get(f"/api/v1/families/{data['family'].pk}/savings/overview/", {"year": "2026"})

    assert response.status_code == status.HTTP_200_OK
    assert response["Cache-Control"] == "private, no-store"
    assert response.data["role"] == "HOUSEHOLD_AGGREGATE_AUTHORITY"
    assert response.data["capabilities"]["can_view_household_planning"] is True
    assert response.data["savings"]["annual_real_confirmed_total"] == "150.00"
    assert response.data["savings"]["annual_target"] == "3000.00"
    assert response.data["savings"]["progress_percent"] == "5.00"
    assert response.data["planning"]["available"] is True
    assert response.data["planning"]["contribution_plan"]["first_month"] == {
        "month": "2026-01-01",
        "total": "865.92",
        "personal_contributions": [
            {"owner_id": data["jalberth"].pk, "amount": "216.48"},
            {"owner_id": data["raiza"].pk, "amount": "216.48"},
        ],
        "family_contribution": "432.96",
    }
    assert response.data["planning"]["contribution_plan"]["months_2_to_12"][0]["total"] == "935.92"
    assert response.data["matias"] == {
        "configured": True,
        "target_amount": "500.00",
        "real_confirmed_balance": "0.00",
        "progress_percent": "0.00",
        "initial_contribution_total": "100.00",
        "initial_contribution_per_parent": "50.00",
        "monthly_simulated_expenditure": "30.00",
        "monthly_replenishment_total": "30.00",
        "monthly_replenishment_per_parent": "15.00",
    }
    assert (SavingsMovement.objects.count(), AuditLog.objects.count()) == before


def test_member_overview_contains_only_own_and_shared_confirmed_savings(api_client, overview_records):
    data = overview_records
    _, raiza_goal, family_goal = _configure_approved_planning(data)
    secret_goal = SavingsGoal.objects.create(
        family=data["family"], owner=data["jalberth"], name="Jalberth secret", target_amount="888888.82"
    )
    SavingsMovement.objects.create(
        goal=secret_goal, kind="CONTRIBUTION", amount="999999.91", occurred_on="2026-01-01"
    )
    SavingsMovement.objects.create(
        goal=raiza_goal, kind="CONTRIBUTION", amount="100.00", occurred_on="2026-01-01"
    )
    SavingsMovement.objects.create(
        goal=family_goal, kind="CONTRIBUTION", amount="200.00", occurred_on="2026-01-01"
    )
    api_client.force_authenticate(data["raiza"])

    response = api_client.get(f"/api/v1/families/{data['family'].pk}/savings/overview/", {"year": "2026"})

    assert response.status_code == status.HTTP_200_OK
    assert response.data["role"] == "MEMBER"
    assert response.data["capabilities"] == {
        "can_manage_private_goals": True,
        "can_record_savings_movements": True,
        "can_manage_shared_goals": False,
        "can_manage_matias_fund": False,
        "can_manage_matias_movements": False,
        "can_view_household_planning": False,
    }
    assert response.data["savings"]["annual_real_confirmed_total"] == "300.00"
    assert response.data["savings"]["annual_target"] == "3000.00"
    assert [goal["name"] for goal in response.data["savings"]["personal_goals"]] == ["Raiza goal"]
    assert [goal["name"] for goal in response.data["savings"]["family_goals"]] == ["Family goal"]
    assert set(response.data) == {"year", "role", "capabilities", "savings", "matias"}
    assert b"Jalberth" not in response.content
    assert b"888888.82" not in response.content
    assert b"999999.91" not in response.content
    assert b"contribution_plan" not in response.content


def test_authority_overview_reports_incomplete_planning_without_fabricating_values(api_client, overview_records):
    data = overview_records
    SavingsGoal.objects.create(
        family=data["family"], owner=data["jalberth"], name="Private", target_amount="1000.00", projected_balance="900.00"
    )
    SavingsGoal.objects.create(
        family=data["family"], name="Family", target_amount="1000.00", projected_balance="800.00"
    )
    api_client.force_authenticate(data["jalberth"])

    response = api_client.get(f"/api/v1/families/{data['family'].pk}/savings/overview/", {"year": "2026"})

    assert response.status_code == status.HTTP_200_OK
    assert response.data["savings"]["annual_real_confirmed_total"] == "0.00"
    assert response.data["planning"] == {
        "available": False,
        "missing": {
            "budget_months": [f"2026-{month:02d}-01" for month in range(1, 13)],
            "income_months": [f"2026-{month:02d}-01" for month in range(1, 13)],
            "allowance_months": [f"2026-{month:02d}-01" for month in range(1, 13)],
            "distribution_months": [f"2026-{month:02d}-01" for month in range(1, 13)],
            "goal_types": [],
            "matias_fund": True,
        },
    }
    assert "contribution_plan" not in response.data["planning"]


def test_non_authority_admin_receives_member_capabilities(api_client, overview_records):
    data = overview_records
    membership = data["family"].memberships.get(user=data["raiza"])
    membership.role = "ADMIN"
    membership.save(update_fields=("role",))
    api_client.force_authenticate(data["raiza"])

    response = api_client.get(f"/api/v1/families/{data['family'].pk}/savings/overview/", {"year": "2026"})

    assert response.status_code == status.HTTP_200_OK
    assert response.data["role"] == "MEMBER"
    assert response.data["capabilities"]["can_manage_shared_goals"] is False
    assert response.data["capabilities"]["can_view_household_planning"] is False
