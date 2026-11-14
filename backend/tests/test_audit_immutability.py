import pytest
from django.core.exceptions import ValidationError

from apps.audit.models import AuditLog
from apps.audit.services import record_entity_mutation, record_membership_mutation
from apps.families.models import FamilyMembership

pytestmark = pytest.mark.django_db


def test_audit_logs_can_only_be_created_by_the_service(
    user_factory, family_factory, membership_factory
):
    actor = user_factory("actor")
    family = family_factory("Family")
    membership = membership_factory(family, actor, role=FamilyMembership.Role.ADMIN)

    with pytest.raises(ValidationError):
        AuditLog.objects.create(
            actor=actor,
            action="membership.created",
            family=family,
            membership_target_id=membership.pk,
            metadata={},
        )


def test_audit_logs_reject_normal_model_updates_and_deletes(
    user_factory, family_factory, membership_factory
):
    actor = user_factory("actor")
    family = family_factory("Family")
    membership = membership_factory(family, actor)
    audit_log = record_membership_mutation(
        actor=actor,
        action="membership.created",
        family=family,
        membership_target_id=membership.pk,
        metadata={"role": membership.role},
    )

    audit_log.action = "tampered"
    with pytest.raises(ValidationError):
        audit_log.save()
    with pytest.raises(ValidationError):
        audit_log.delete()
    with pytest.raises(ValidationError):
        AuditLog.objects.filter(pk=audit_log.pk).update(action="tampered")
    with pytest.raises(ValidationError):
        AuditLog.objects.filter(pk=audit_log.pk).delete()


def test_audit_logs_reject_bulk_creation(user_factory, family_factory, membership_factory):
    actor = user_factory("actor")
    family = family_factory("Family")
    membership = membership_factory(family, actor)

    with pytest.raises(ValidationError):
        AuditLog.objects.bulk_create(
            [
                AuditLog(
                    actor=actor,
                    action="membership.created",
                    family=family,
                    membership_target_id=membership.pk,
                    metadata={},
                )
            ]
        )


def test_generic_audit_events_preserve_membership_event_compatibility(
    user_factory, family_factory, membership_factory
):
    actor = user_factory("actor")
    family = family_factory("Family")
    membership = membership_factory(family, actor)

    membership_log = record_membership_mutation(
        actor=actor,
        action="membership.updated",
        family=family,
        membership_target_id=membership.pk,
        metadata={"is_active": True},
    )
    generic_log = record_entity_mutation(
        actor=actor,
        action="logical_account.created",
        family=family,
        entity_type="logical_account",
        entity_id=99,
        metadata={"scope": "shared"},
    )

    assert membership_log.membership_target_id == membership.pk
    assert membership_log.entity_type == "membership"
    assert membership_log.entity_id == membership.pk
    assert generic_log.membership_target_id is None
    assert generic_log.entity_type == "logical_account"
    assert generic_log.entity_id == 99
