from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction

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
def correct_expense_movement(*, actor, movement, reason, movement_data, allocations):
    movement = ExpenseMovement.objects.select_for_update().get(pk=movement.pk)
    if movement.status != MovementStatus.CONFIRMED:
        raise ValidationError("Only confirmed movements can be corrected.")
    if ExpenseMovement.objects.filter(reversal_of=movement).exists():
        raise ValidationError("This movement has already been corrected.")
    if movement_data.get("owner") != movement.owner:
        raise ValidationError({"owner_id": "A correction cannot change the movement owner."})
    reversal = ExpenseMovement.objects.create(
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
    for allocation in movement.allocations.all():
        ExpenseAllocation.objects.create(
            movement=reversal, member=allocation.member, amount=allocation.amount
        )
    replacement = create_expense_movement(
        actor=actor,
        family=movement.family,
        movement_data={
            **movement_data,
            "replaces": movement,
            "correction_reason": reason,
        },
        allocations=allocations,
    )
    record_entity_mutation(
        actor=actor,
        action="expense_movement.corrected",
        family=movement.family,
        entity_type="expense_movement",
        entity_id=movement.pk,
        metadata={
            "reason": reason,
            "reversal_id": reversal.pk,
            "replacement_id": replacement.pk,
        },
    )
    return reversal, replacement
