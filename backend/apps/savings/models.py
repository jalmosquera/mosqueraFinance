from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Case, DecimalField, F, Q, Sum, Value, When
from django.db.models.functions import Coalesce

from apps.finance.models import FamilyScopedManager, FamilyScopedQuerySet
from apps.incomes.models import MovementStatus


class SavingsGoal(models.Model):
    family = models.ForeignKey("families.Family", on_delete=models.CASCADE)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT
    )
    name = models.CharField(max_length=120)
    target_amount = models.DecimalField(max_digits=14, decimal_places=2)
    projected_monthly_contribution = models.DecimalField(
        max_digits=14, decimal_places=2, default=Decimal("0.00")
    )
    projected_balance = models.DecimalField(
        max_digits=14, decimal_places=2, default=Decimal("0.00")
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = FamilyScopedManager()

    class Meta:
        ordering = ("name", "pk")
        constraints = [
            models.CheckConstraint(condition=Q(target_amount__gt=0), name="savings_goal_target_positive"),
            models.CheckConstraint(
                condition=Q(projected_monthly_contribution__gte=0),
                name="savings_goal_projected_monthly_nonnegative",
            ),
            models.CheckConstraint(
                condition=Q(projected_balance__gte=0), name="savings_goal_projected_balance_nonnegative"
            ),
        ]

    @property
    def real_balance(self):
        return self.movements.filter(status=MovementStatus.CONFIRMED).aggregate(
            balance=Coalesce(
                Sum(
                    Case(
                        When(kind=SavingsMovement.Kind.CONTRIBUTION, then=F("amount")),
                        When(kind=SavingsMovement.Kind.WITHDRAWAL, then=-F("amount")),
                        default=F("amount"),
                        output_field=DecimalField(max_digits=14, decimal_places=2),
                    )
                ),
                Value(Decimal("0.00")),
                output_field=DecimalField(max_digits=14, decimal_places=2),
            )
        )["balance"]

    def clean(self):
        super().clean()
        errors = {}
        if not self.name.strip():
            errors["name"] = "Name cannot be blank."
        if self.owner_id and not self.family.memberships.filter(
            user_id=self.owner_id, is_active=True
        ).exists():
            errors["owner"] = "Owner must be an active family member."
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)


class ImmutableMovementQuerySet(FamilyScopedQuerySet):
    def update(self, **kwargs):
        raise ValidationError("Confirmed movements cannot be updated; void or correct them instead.")

    def delete(self):
        raise ValidationError("Confirmed movements cannot be deleted; void them instead.")


class ImmutableMovementManager(models.Manager.from_queryset(ImmutableMovementQuerySet)):
    pass


class ImmutableAllocationQuerySet(models.QuerySet):
    def update(self, **kwargs):
        raise ValidationError("Fund allocations cannot be updated.")

    def delete(self):
        raise ValidationError("Fund allocations cannot be deleted.")


class ImmutableAllocationManager(models.Manager.from_queryset(ImmutableAllocationQuerySet)):
    pass


class SavingsMovement(models.Model):
    class Kind(models.TextChoices):
        CONTRIBUTION = "CONTRIBUTION", "Contribution"
        WITHDRAWAL = "WITHDRAWAL", "Withdrawal"
        ADJUSTMENT = "ADJUSTMENT", "Adjustment"

    goal = models.ForeignKey(SavingsGoal, on_delete=models.PROTECT, related_name="movements")
    kind = models.CharField(max_length=12, choices=Kind.choices)
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    occurred_on = models.DateField()
    description = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=9, choices=MovementStatus.choices, default=MovementStatus.CONFIRMED)
    void_reason = models.TextField(blank=True)
    voided_at = models.DateTimeField(null=True, blank=True)
    corrects = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.PROTECT, related_name="corrections"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    objects = ImmutableMovementManager()

    class Meta:
        ordering = ("-occurred_on", "-pk")
        constraints = [
            models.CheckConstraint(
                condition=(Q(kind="ADJUSTMENT") & ~Q(amount=0))
                | (~Q(kind="ADJUSTMENT") & Q(amount__gt=0)),
                name="savings_movement_amount_valid",
            ),
        ]

    def clean(self):
        super().clean()
        if self.kind == self.Kind.ADJUSTMENT and self.amount == 0:
            raise ValidationError({"amount": "An adjustment amount cannot be zero."})
        if self.kind != self.Kind.ADJUSTMENT and self.amount <= 0:
            raise ValidationError({"amount": "Contributions and withdrawals must be positive."})
        if self.corrects_id and self.corrects.goal_id != self.goal_id:
            raise ValidationError({"corrects": "A correction must belong to the same savings goal."})

    def save(self, *args, **kwargs):
        if not self._state.adding:
            allowed_fields = {"status", "void_reason", "voided_at"}
            updated_fields = set(kwargs.get("update_fields") or ())
            if not getattr(self, "_allow_void", False) or updated_fields != allowed_fields:
                raise ValidationError("Confirmed movements cannot be updated; void or correct them instead.")
        self.full_clean()
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("Confirmed movements cannot be deleted; void them instead.")


class MatiasFund(models.Model):
    family = models.OneToOneField("families.Family", on_delete=models.CASCADE, related_name="matias_fund")
    target_amount = models.DecimalField(max_digits=14, decimal_places=2)
    projected_balance = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    initial_contribution_total = models.DecimalField(
        max_digits=14, decimal_places=2, default=Decimal("0.00")
    )
    monthly_simulated_expenditure = models.DecimalField(
        max_digits=14, decimal_places=2, default=Decimal("0.00")
    )
    monthly_replenishment_total = models.DecimalField(
        max_digits=14, decimal_places=2, default=Decimal("0.00")
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=Q(target_amount__gt=0), name="matias_fund_target_positive"),
            models.CheckConstraint(condition=Q(projected_balance__gte=0), name="matias_fund_projected_balance_nonnegative"),
            models.CheckConstraint(condition=Q(initial_contribution_total__gte=0), name="matias_fund_initial_contribution_nonnegative"),
            models.CheckConstraint(condition=Q(monthly_simulated_expenditure__gte=0), name="matias_fund_monthly_expenditure_nonnegative"),
            models.CheckConstraint(condition=Q(monthly_replenishment_total__gte=0), name="matias_fund_monthly_replenishment_nonnegative"),
        ]

    @property
    def real_balance(self):
        return self.movements.filter(status=MovementStatus.CONFIRMED).aggregate(
            balance=Coalesce(
                Sum(
                    Case(
                        When(kind=MatiasFundMovement.Kind.DISBURSEMENT, then=-F("amount")),
                        default=F("amount"),
                        output_field=DecimalField(max_digits=14, decimal_places=2),
                    )
                ),
                Value(Decimal("0.00")),
                output_field=DecimalField(max_digits=14, decimal_places=2),
            )
        )["balance"]

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)


class MatiasFundMovement(models.Model):
    class Kind(models.TextChoices):
        INITIAL_CONTRIBUTION = "INITIAL_CONTRIBUTION", "Initial contribution"
        DISBURSEMENT = "DISBURSEMENT", "Disbursement"
        REPLENISHMENT = "REPLENISHMENT", "Replenishment"

    fund = models.ForeignKey(MatiasFund, on_delete=models.PROTECT, related_name="movements")
    kind = models.CharField(max_length=20, choices=Kind.choices)
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    occurred_on = models.DateField()
    description = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=9, choices=MovementStatus.choices, default=MovementStatus.CONFIRMED)
    void_reason = models.TextField(blank=True)
    voided_at = models.DateTimeField(null=True, blank=True)
    corrects = models.ForeignKey("self", null=True, blank=True, on_delete=models.PROTECT, related_name="corrections")
    created_at = models.DateTimeField(auto_now_add=True)

    objects = ImmutableMovementManager()

    class Meta:
        ordering = ("-occurred_on", "-pk")
        constraints = [models.CheckConstraint(condition=Q(amount__gt=0), name="matias_movement_amount_positive")]

    def clean(self):
        super().clean()
        if self.corrects_id and self.corrects.fund_id != self.fund_id:
            raise ValidationError({"corrects": "A correction must belong to the same fund."})

    def save(self, *args, **kwargs):
        if not self._state.adding:
            allowed_fields = {"status", "void_reason", "voided_at"}
            updated_fields = set(kwargs.get("update_fields") or ())
            if not getattr(self, "_allow_void", False) or updated_fields != allowed_fields:
                raise ValidationError("Fund movements cannot be updated; void or correct them instead.")
        self.full_clean()
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("Fund movements cannot be deleted; void them instead.")


class MatiasFundAllocation(models.Model):
    movement = models.ForeignKey(MatiasFundMovement, on_delete=models.PROTECT, related_name="allocations")
    contributor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    amount = models.DecimalField(max_digits=14, decimal_places=2)

    objects = ImmutableAllocationManager()

    class Meta:
        constraints = [
            models.CheckConstraint(condition=Q(amount__gt=0), name="matias_allocation_amount_positive"),
            models.UniqueConstraint(fields=("movement", "contributor"), name="unique_matias_allocation_contributor"),
        ]

    def clean(self):
        super().clean()
        if self.movement_id and not self.movement.fund.family.memberships.filter(
            user_id=self.contributor_id, is_active=True
        ).exists():
            raise ValidationError({"contributor": "Contributor must be an active family member."})

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise ValidationError("Fund allocations cannot be updated.")
        self.full_clean()
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("Fund allocations cannot be deleted.")
