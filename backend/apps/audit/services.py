import json

from django.core.exceptions import ValidationError

from .models import AuditLog


def record_entity_mutation(*, actor, action, family, entity_type, entity_id, metadata):
    """Create an immutable audit record for a server-side entity mutation.

    The actor is accepted only from trusted server-side services, never serializers.
    """
    if not isinstance(metadata, dict):
        raise ValidationError("Audit metadata must be a JSON object.")

    # Round-tripping rejects non-JSON values and prevents mutable caller references.
    metadata_copy = json.loads(json.dumps(metadata))
    return AuditLog.objects._create_for_service(
        actor=actor,
        action=action,
        family=family,
        membership_target_id=entity_id if entity_type == "membership" else None,
        entity_type=entity_type,
        entity_id=entity_id,
        metadata=metadata_copy,
    )


def record_membership_mutation(*, actor, action, family, membership_target_id, metadata):
    """Compatibility wrapper for membership audit events."""
    return record_entity_mutation(
        actor=actor,
        action=action,
        family=family,
        entity_type="membership",
        entity_id=membership_target_id,
        metadata=metadata,
    )
