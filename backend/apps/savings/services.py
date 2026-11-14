from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.audit.services import record_entity_mutation
from apps.incomes.models import MovementStatus

from .models import MatiasFundAllocation, MatiasFundMovement, SavingsMovement


def _void_movement(*, actor, movement, reason, entity_type):
    if movement.status != MovementStatus.CONFIRMED:
        raise ValidationError("Only confirmed movements can be voided.")
    movement.status = MovementStatus.VOIDED
    movement.void_reason = reason
    movement.voided_at = timezone.now()
    movement._allow_void = True
    movement.save(update_fields=("status", "void_reason", "voided_at"))
    record_entity_mutation(
        actor=actor,
        action=f"{entity_type}.voided",
        family=movement.goal.family if entity_type == "savings_movement" else movement.fund.family,
        entity_type=entity_type,
        entity_id=movement.pk,
        metadata={"reason": reason},
    )
    return movement


@transaction.atomic
def void_savings_movement(*, actor, movement, reason):
    movement = SavingsMovement.objects.select_for_update().get(pk=movement.pk)
    return _void_movement(actor=actor, movement=movement, reason=reason, entity_type="savings_movement")


@transaction.atomic
def correct_savings_movement(*, actor, movement, reason, replacement_data):
    movement = SavingsMovement.objects.select_for_update().get(pk=movement.pk)
    _void_movement(actor=actor, movement=movement, reason=reason, entity_type="savings_movement")
    replacement = SavingsMovement.objects.create(
        goal=movement.goal, corrects=movement, **replacement_data
    )
    record_entity_mutation(
        actor=actor,
        action="savings_movement.corrected",
        family=movement.goal.family,
        entity_type="savings_movement",
        entity_id=replacement.pk,
        metadata={"corrects_id": movement.pk},
    )
    return replacement


@transaction.atomic
def create_matias_fund_movement(*, actor, fund, movement_data, allocations):
    allocation_total = sum((allocation["amount"] for allocation in allocations), Decimal("0.00"))
    if not allocations or allocation_total != movement_data["amount"]:
        raise ValidationError({"allocations": "Allocation amounts must equal the fund movement amount exactly."})
    movement = MatiasFundMovement.objects.create(fund=fund, **movement_data)
    for allocation in allocations:
        MatiasFundAllocation.objects.create(movement=movement, **allocation)
    record_entity_mutation(
        actor=actor,
        action="matias_fund_movement.created",
        family=fund.family,
        entity_type="matias_fund_movement",
        entity_id=movement.pk,
        metadata={"kind": movement.kind, "allocation_total": str(allocation_total)},
    )
    return movement


@transaction.atomic
def void_matias_fund_movement(*, actor, movement, reason):
    movement = MatiasFundMovement.objects.select_for_update().get(pk=movement.pk)
    return _void_movement(actor=actor, movement=movement, reason=reason, entity_type="matias_fund_movement")


@transaction.atomic
def correct_matias_fund_movement(*, actor, movement, reason, replacement_data, allocations):
    movement = MatiasFundMovement.objects.select_for_update().get(pk=movement.pk)
    _void_movement(actor=actor, movement=movement, reason=reason, entity_type="matias_fund_movement")
    replacement = create_matias_fund_movement(
        actor=actor,
        fund=movement.fund,
        movement_data={**replacement_data, "corrects": movement},
        allocations=allocations,
    )
    record_entity_mutation(
        actor=actor,
        action="matias_fund_movement.corrected",
        family=movement.fund.family,
        entity_type="matias_fund_movement",
        entity_id=replacement.pk,
        metadata={"corrects_id": movement.pk},
    )
    return replacement
