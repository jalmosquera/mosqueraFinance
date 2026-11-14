import json

from django.core.exceptions import ValidationError

from .models import AuditLog


def record_membership_mutation(
    *, actor, action, family, membership_target_id, metadata
):
    """Create an immutable audit record for a membership change.

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
        membership_target_id=membership_target_id,
        metadata=metadata_copy,
    )
