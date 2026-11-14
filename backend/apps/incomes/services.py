from django.core.exceptions import ValidationError
from django.db import transaction

from apps.audit.services import record_entity_mutation

from .models import IncomeMovement, MovementStatus


@transaction.atomic
def correct_income_movement(*, actor, movement, reason, movement_data):
    movement = IncomeMovement.objects.select_for_update().get(pk=movement.pk)
    if movement.status != MovementStatus.CONFIRMED:
        raise ValidationError("Only confirmed movements can be corrected.")
    if IncomeMovement.objects.filter(reversal_of=movement).exists():
        raise ValidationError("This movement has already been corrected.")
    if movement_data.get("owner") != movement.owner:
        raise ValidationError({"owner_id": "A correction cannot change the movement owner."})
    reversal = IncomeMovement.objects.create(
        family=movement.family,
        owner=movement.owner,
        account=movement.account,
        category=movement.category,
        amount=movement.amount,
        occurred_on=movement.occurred_on,
        description=movement.description,
        is_reversal=True,
        reversal_of=movement,
        correction_reason=reason,
    )
    replacement = IncomeMovement.objects.create(
        family=movement.family,
        **movement_data,
        replaces=movement,
        correction_reason=reason,
    )
    record_entity_mutation(
        actor=actor,
        action="income_movement.corrected",
        family=movement.family,
        entity_type="income_movement",
        entity_id=movement.pk,
        metadata={
            "reason": reason,
            "reversal_id": reversal.pk,
            "replacement_id": replacement.pk,
        },
    )
    return reversal, replacement
