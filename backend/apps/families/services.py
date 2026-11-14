from django.db import transaction
from django.http import Http404

from apps.audit.services import record_membership_mutation

from .models import FamilyMembership


def _locked_active_admin(*, actor, family):
    try:
        return (
            FamilyMembership.objects.select_for_update()
            .active_admin_for(actor, family)
            .get()
        )
    except FamilyMembership.DoesNotExist as error:
        raise Http404 from error


@transaction.atomic
def create_membership(*, actor, family, user, role, is_active=True):
    _locked_active_admin(actor=actor, family=family)
    membership = FamilyMembership.objects.create(
        family=family,
        user=user,
        role=role,
        is_active=is_active,
    )
    record_membership_mutation(
        actor=actor,
        action="membership.created",
        family=family,
        membership_target_id=membership.pk,
        metadata={"role": membership.role, "is_active": membership.is_active},
    )
    return membership


@transaction.atomic
def update_membership(*, actor, membership, role, is_active):
    _locked_active_admin(actor=actor, family=membership.family)
    membership = FamilyMembership.objects.select_for_update().get(pk=membership.pk)
    membership.role = role
    membership.is_active = is_active
    membership.save(update_fields=("role", "is_active", "updated_at"))
    record_membership_mutation(
        actor=actor,
        action="membership.updated",
        family=membership.family,
        membership_target_id=membership.pk,
        metadata={"role": membership.role, "is_active": membership.is_active},
    )
    return membership


@transaction.atomic
def delete_membership(*, actor, membership):
    _locked_active_admin(actor=actor, family=membership.family)
    membership = FamilyMembership.objects.select_for_update().get(pk=membership.pk)
    target_id = membership.pk
    family = membership.family
    metadata = {
        "role": membership.role,
        "is_active": membership.is_active,
        "user_id": membership.user_id,
    }
    membership.delete()
    # The target id is intentionally stored as a scalar so this record survives deletion.
    record_membership_mutation(
        actor=actor,
        action="membership.deleted",
        family=family,
        membership_target_id=target_id,
        metadata=metadata,
    )
