import pytest
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.families.models import Family, FamilyMembership


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def user_factory(db):
    def create_user(username):
        return User.objects.create_user(
            username=username,
            email=f"{username}@example.test",
            password="test-password",
        )

    return create_user


@pytest.fixture
def family_factory(db):
    def create_family(name):
        return Family.objects.create(name=name)

    return create_family


@pytest.fixture
def membership_factory(db):
    def create_membership(
        family, user, role=FamilyMembership.Role.MEMBER, is_active=True
    ):
        membership = FamilyMembership.objects.create(
            family=family,
            user=user,
            role=role,
            is_active=is_active,
        )
        if role == FamilyMembership.Role.ADMIN and family.household_aggregate_authority_id is None:
            family.household_aggregate_authority = user
            family.save(update_fields=("household_aggregate_authority",))
        return membership

    return create_membership
