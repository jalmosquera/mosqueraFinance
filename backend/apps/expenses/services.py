from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.audit.services import record_entity_mutation

from .models import ExpenseAllocation, ExpenseMovement, MovementStatus


@transaction.atomic
def create_expense_movement(*, actor, family, movement_data, allocations):
    allocation_total = sum((allocation["amount"] for allocation in allocations), Decimal(0))
    if movement_data.get("owner") is None:
        if not allocations or allocation_total != movement_data["amount"]:
            raise ValidationError(
                {"allocations": "Allocation amounts must equal the expense amount exactly."}
            )
    elif allocations:
        raise ValidationError({"allocations": "Private expenses cannot have allocations."})
    movement = ExpenseMovement.objects.create(family=family, **movement_data)
    for allocation in allocations:
        ExpenseAllocation.objects.create(movement=movement, **allocation)
    record_entity_mutation(
        actor=actor,
        action="expense_movement.created",
        family=family,
        entity_type="expense_movement",
        entity_id=movement.pk,
        metadata={"owner_id": movement.owner_id, "allocation_total": str(allocation_total)},
    )
    return movement


@transaction.atomic
def void_expense_movement(*, actor, movement, reason):
    movement = ExpenseMovement.objects.select_for_update().get(pk=movement.pk)
    if movement.status != MovementStatus.CONFIRMED:
        raise ValidationError("Only confirmed movements can be voided.")
    movement.status = MovementStatus.VOIDED
    movement.void_reason = reason
    movement.voided_at = timezone.now()
    movement.save(update_fields=("status", "void_reason", "voided_at", "updated_at"))
    record_entity_mutation(
        actor=actor,
        action="expense_movement.voided",
        family=movement.family,
        entity_type="expense_movement",
        entity_id=movement.pk,
        metadata={"reason": reason},
    )
    return movement
