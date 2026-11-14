from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.audit.services import record_entity_mutation

from .models import IncomeMovement, MovementStatus


@transaction.atomic
def void_income_movement(*, actor, movement, reason):
    movement = IncomeMovement.objects.select_for_update().get(pk=movement.pk)
    if movement.status != MovementStatus.CONFIRMED:
        raise ValidationError("Only confirmed movements can be voided.")
    movement.status = MovementStatus.VOIDED
    movement.void_reason = reason
    movement.voided_at = timezone.now()
    movement.save(update_fields=("status", "void_reason", "voided_at", "updated_at"))
    record_entity_mutation(
        actor=actor,
        action="income_movement.voided",
        family=movement.family,
        entity_type="income_movement",
        entity_id=movement.pk,
        metadata={"reason": reason},
    )
    return movement
