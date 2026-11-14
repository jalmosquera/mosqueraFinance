from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q

from apps.finance.models import FamilyScopedManager, FamilyScopedQuerySet


class ForecastStatus(models.TextChoices):
    PLANNED = "PLANNED", "Planned"


class MovementStatus(models.TextChoices):
    CONFIRMED = "CONFIRMED", "Confirmed"
    VOIDED = "VOIDED", "Voided"


class Recurrence(models.TextChoices):
    NONE = "NONE", "Does not repeat"
    MONTHLY = "MONTHLY", "Monthly"


class ConfirmedMovementQuerySet(FamilyScopedQuerySet):
    def delete(self):
        raise ValidationError("Confirmed movements cannot be deleted; void them instead.")


class ConfirmedMovementManager(
    models.Manager.from_queryset(ConfirmedMovementQuerySet)
):
    pass


class IncomeRecord(models.Model):
    family = models.ForeignKey("families.Family", on_delete=models.CASCADE)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT
    )
    account = models.ForeignKey("finance.LogicalAccount", on_delete=models.PROTECT)
    category = models.ForeignKey("finance.Category", on_delete=models.PROTECT)
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    occurred_on = models.DateField()
    description = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = FamilyScopedManager()

    class Meta:
        abstract = True
        ordering = ("-occurred_on", "-pk")
        constraints = [
            models.CheckConstraint(
                condition=Q(amount__gt=0), name="%(app_label)s_%(class)s_amount_positive"
            )
        ]

    def clean(self):
        super().clean()
        errors = {}
        if self.account_id and self.account.family_id != self.family_id:
            errors["account"] = "Account must belong to the same family."
        if self.category_id and self.category.family_id != self.family_id:
            errors["category"] = "Category must belong to the same family."
        if self.category_id and self.category.kind != "INCOME":
            errors["category"] = "Income records require an income category."
        for field, reference in (("account", self.account), ("category", self.category)):
            if reference.owner_id != self.owner_id and reference.owner_id is not None:
                errors[field] = "Private references must have the same owner as the record."
        if self.owner_id and not self.family.memberships.filter(
            user_id=self.owner_id, is_active=True
        ).exists():
            errors["owner"] = "Owner must be an active family member."
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)


class IncomeForecast(IncomeRecord):
    status = models.CharField(
        max_length=8, choices=ForecastStatus.choices, default=ForecastStatus.PLANNED
    )
    recurrence = models.CharField(
        max_length=8, choices=Recurrence.choices, default=Recurrence.NONE
    )
    effective_date = models.DateField()


class IncomeMovement(IncomeRecord):
    status = models.CharField(
        max_length=9, choices=MovementStatus.choices, default=MovementStatus.CONFIRMED
    )
    void_reason = models.TextField(blank=True)
    voided_at = models.DateTimeField(null=True, blank=True)

    objects = ConfirmedMovementManager()

    def delete(self, *args, **kwargs):
        raise ValidationError("Confirmed movements cannot be deleted; void them instead.")
