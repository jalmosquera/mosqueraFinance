import pytest
from rest_framework import status
from rest_framework.test import APIClient

from apps.audit.models import AuditLog
from apps.families.models import FamilyMembership

pytestmark = pytest.mark.django_db


def test_unauthenticated_family_list_is_rejected(api_client):
    response = api_client.get("/api/v1/families/")

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_family_list_and_direct_detail_are_scoped_to_caller(
    api_client, user_factory, family_factory, membership_factory
):
    caller = user_factory("caller")
    own_family = family_factory("Own family")
    other_family = family_factory("Other family")
    membership_factory(own_family, caller)
    membership_factory(other_family, user_factory("other"))
    api_client.force_authenticate(caller)

    list_response = api_client.get("/api/v1/families/")
    hidden_family_response = api_client.get(f"/api/v1/families/{other_family.pk}/")

    assert list_response.status_code == status.HTTP_200_OK
    assert [family["id"] for family in list_response.data] == [own_family.pk]
    assert hidden_family_response.status_code == status.HTTP_404_NOT_FOUND


def test_cross_family_membership_detail_is_not_enumerable(
    api_client, user_factory, family_factory, membership_factory
):
    caller = user_factory("caller")
    own_family = family_factory("Own family")
    other_family = family_factory("Other family")
    membership_factory(own_family, caller)
    hidden_membership = membership_factory(other_family, user_factory("other"))
    api_client.force_authenticate(caller)

    response = api_client.get(
        f"/api/v1/families/{other_family.pk}/memberships/{hidden_membership.pk}/"
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_non_admin_cannot_create_a_membership(
    api_client, user_factory, family_factory, membership_factory
):
    member = user_factory("member")
    family = family_factory("Family")
    membership_factory(family, member)
    api_client.force_authenticate(member)

    response = api_client.post(
        f"/api/v1/families/{family.pk}/memberships/",
        {"user_id": user_factory("target").pk, "role": FamilyMembership.Role.ADMIN},
        format="json",
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert FamilyMembership.objects.filter(family=family).count() == 1


def test_admin_membership_creation_is_audited_with_server_actor(
    api_client, user_factory, family_factory, membership_factory
):
    admin = user_factory("admin")
    target = user_factory("target")
    family = family_factory("Family")
    membership_factory(family, admin, role=FamilyMembership.Role.ADMIN)
    api_client.force_authenticate(admin)

    response = api_client.post(
        f"/api/v1/families/{family.pk}/memberships/",
        {
            "user_id": target.pk,
            "role": FamilyMembership.Role.MEMBER,
            "actor": target.pk,
        },
        format="json",
    )

    assert response.status_code == status.HTTP_201_CREATED
    membership = FamilyMembership.objects.get(family=family, user=target)
    audit_log = AuditLog.objects.get()
    assert audit_log.actor == admin
    assert audit_log.action == "membership.created"
    assert audit_log.family == family
    assert audit_log.membership_target_id == membership.pk


def test_session_mutation_requires_csrf_token(
    user_factory, family_factory, membership_factory
):
    admin = user_factory("admin")
    family = family_factory("Family")
    membership_factory(family, admin, role=FamilyMembership.Role.ADMIN)
    csrf_client = APIClient(enforce_csrf_checks=True)
    csrf_client.force_login(admin)

    response = csrf_client.post(
        f"/api/v1/families/{family.pk}/memberships/",
        {"user_id": user_factory("target").pk},
        format="json",
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.parametrize("method,payload", [("patch", {"role": "MEMBER"}), ("patch", {"is_active": False}), ("delete", None)])
def test_last_active_administrator_cannot_be_removed_or_demoted(
    api_client, user_factory, family_factory, membership_factory, method, payload
):
    admin = user_factory("admin")
    family = family_factory("Family")
    membership = membership_factory(family, admin, role=FamilyMembership.Role.ADMIN)
    api_client.force_authenticate(admin)
    url = f"/api/v1/families/{family.pk}/memberships/{membership.pk}/"

    response = getattr(api_client, method)(url, payload, format="json") if payload else api_client.delete(url)

    membership.refresh_from_db()
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert membership.role == FamilyMembership.Role.ADMIN
    assert membership.is_active is True
