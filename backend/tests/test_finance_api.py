import pytest
from rest_framework import status

from apps.finance.models import Category, LogicalAccount

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize(
    ("model", "url_segment", "payload"),
    [
        (LogicalAccount, "logical-accounts", {"name": "Jalberth account"}),
        (
            Category,
            "categories",
            {"name": "Jalberth category", "kind": Category.Kind.EXPENSE},
        ),
    ],
)
def test_member_cannot_retrieve_another_members_private_finance_record(
    api_client, user_factory, family_factory, membership_factory, model, url_segment, payload
):
    jalberth = user_factory("jalberth")
    raiza = user_factory("raiza")
    family = family_factory("Family")
    membership_factory(family, jalberth, role="ADMIN")
    membership_factory(family, raiza)
    private_record = model.objects.create(family=family, owner=jalberth, **payload)
    api_client.force_authenticate(raiza)

    list_response = api_client.get(f"/api/v1/families/{family.pk}/{url_segment}/")
    detail_response = api_client.get(
        f"/api/v1/families/{family.pk}/{url_segment}/{private_record.pk}/"
    )

    assert list_response.status_code == status.HTTP_200_OK
    assert list_response.data == []
    assert detail_response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.parametrize(
    ("url_segment", "payload"),
    [
        ("logical-accounts", {"name": "Spoofed account"}),
        (
            "categories",
            {"name": "Spoofed category", "kind": Category.Kind.INCOME},
        ),
    ],
)
def test_member_cannot_spoof_another_private_owner(
    api_client, user_factory, family_factory, membership_factory, url_segment, payload
):
    jalberth = user_factory("jalberth")
    raiza = user_factory("raiza")
    family = family_factory("Family")
    membership_factory(family, jalberth, role="ADMIN")
    membership_factory(family, raiza)
    api_client.force_authenticate(raiza)

    response = api_client.post(
        f"/api/v1/families/{family.pk}/{url_segment}/",
        {**payload, "owner_id": jalberth.pk},
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.data["owner_id"] == ["Private records can only be owned by you."]


@pytest.mark.parametrize(
    ("model", "url_segment", "payload"),
    [
        (LogicalAccount, "logical-accounts", {"name": "Shared account"}),
        (
            Category,
            "categories",
            {"name": "Shared category", "kind": Category.Kind.EXPENSE},
        ),
    ],
)
def test_shared_finance_records_are_visible_to_active_family_members(
    api_client, user_factory, family_factory, membership_factory, model, url_segment, payload
):
    jalberth = user_factory("jalberth")
    raiza = user_factory("raiza")
    family = family_factory("Family")
    membership_factory(family, jalberth, role="ADMIN")
    membership_factory(family, raiza)
    shared_record = model.objects.create(family=family, **payload)
    api_client.force_authenticate(raiza)

    response = api_client.get(f"/api/v1/families/{family.pk}/{url_segment}/")

    assert response.status_code == status.HTTP_200_OK
    assert [record["id"] for record in response.data] == [shared_record.pk]
    assert response.data[0]["owner_id"] is None
