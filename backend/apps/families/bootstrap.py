from django.core.exceptions import ValidationError
from django.db import transaction

from apps.accounts.models import User
from apps.audit.services import record_entity_mutation

from .models import Family, FamilyMembership


@transaction.atomic
def bootstrap_jalberth(*, email, password, family_name, actor=None):
    if Family.objects.exists() or User.objects.filter(username="jalberth").exists() or User.objects.filter(email=email).exists():
        raise ValidationError("Bootstrap is only available before a family or Jalberth account exists.")
    user = User.objects.create_user(
        username="jalberth",
        email=email,
        password=password,
        first_name="Jalberth",
    )
    family = Family.objects.create(name=family_name)
    membership = FamilyMembership.objects.create(
        family=family, user=user, role=FamilyMembership.Role.ADMIN
    )
    record_entity_mutation(
        actor=actor or user,
        action="family.bootstrap_created",
        family=family,
        entity_type="family",
        entity_id=family.pk,
        metadata={"administrator_user_id": user.pk, "membership_id": membership.pk},
    )
    return user, family, membership
