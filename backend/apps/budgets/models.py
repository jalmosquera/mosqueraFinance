from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q


class MonthlyBudgetForecast(models.Model):
    family = models.ForeignKey("families.Family", on_delete=models.CASCADE, related_name="budget_forecasts")
    month = models.DateField()
    version = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-month", "-version", "-pk")
        constraints = [
            models.UniqueConstraint(fields=("family", "month", "version"), name="unique_budget_forecast_version"),
        ]

    def clean(self):
        super().clean()
        if self.month.day != 1:
            raise ValidationError({"month": "Budget month must be the first day of a month."})

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)


class BudgetLine(models.Model):
    class Kind(models.TextChoices):
        STANDARD = "STANDARD", "Standard"
        RECONCILIATION = "RECONCILIATION", "Reconciliation"

    forecast = models.ForeignKey(MonthlyBudgetForecast, on_delete=models.CASCADE, related_name="lines")
    name = models.CharField(max_length=120)
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    kind = models.CharField(max_length=14, choices=Kind.choices, default=Kind.STANDARD)
    replaces = models.OneToOneField(
        "self", null=True, blank=True, on_delete=models.PROTECT, related_name="replaced_by"
    )

    class Meta:
        ordering = ("pk",)
        constraints = [
            models.CheckConstraint(condition=Q(amount__gte=0), name="budget_line_amount_nonnegative"),
            models.UniqueConstraint(
                fields=("forecast",),
                condition=Q(kind="RECONCILIATION"),
                name="one_reconciliation_line_per_budget",
            ),
        ]

    def clean(self):
        super().clean()
        errors = {}
        if not self.name.strip():
            errors["name"] = "Name cannot be blank."
        if self.replaces_id:
            if self.replaces_id == self.pk:
                errors["replaces"] = "A budget line cannot replace itself."
            elif self.replaces.forecast_id != self.forecast_id:
                errors["replaces"] = "A replacement must belong to the same budget forecast."
            elif self.replaces.kind != self.Kind.RECONCILIATION:
                errors["replaces"] = "Only a reconciliation line can be replaced."
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)


class FreeMoneyAllowance(models.Model):
    family = models.ForeignKey("families.Family", on_delete=models.CASCADE, related_name="free_money_allowances")
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="free_money_allowances")
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    effective_date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("owner_id", "-effective_date", "-pk")
        constraints = [
            models.CheckConstraint(condition=Q(amount__gte=0), name="free_money_allowance_nonnegative"),
            models.UniqueConstraint(fields=("family", "owner", "effective_date"), name="unique_allowance_effective_date"),
        ]

    def clean(self):
        super().clean()
        if not self.family.memberships.filter(user_id=self.owner_id, is_active=True).exists():
            raise ValidationError({"owner": "Owner must be an active family member."})

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)


class SavingsDistributionRule(models.Model):
    family = models.ForeignKey("families.Family", on_delete=models.CASCADE, related_name="savings_distribution_rules")
    effective_date = models.DateField()
    first_owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="first_distribution_rules")
    second_owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="second_distribution_rules")
    created_at = models.DateTimeField(auto_now_add=True)

    FIRST_OWNER_PERCENTAGE = Decimal("0.25")
    SECOND_OWNER_PERCENTAGE = Decimal("0.25")
    MATIAS_PERCENTAGE = Decimal("0.50")

    class Meta:
        ordering = ("-effective_date", "-pk")
        constraints = [
            models.UniqueConstraint(fields=("family", "effective_date"), name="unique_distribution_rule_effective_date"),
            models.CheckConstraint(condition=~Q(first_owner=models.F("second_owner")), name="distribution_owners_differ"),
        ]

    def clean(self):
        super().clean()
        errors = {}
        if self.first_owner_id == self.second_owner_id:
            errors["second_owner"] = "Distribution owners must differ."
        for field, owner_id in (("first_owner", self.first_owner_id), ("second_owner", self.second_owner_id)):
            if not self.family.memberships.filter(user_id=owner_id, is_active=True).exists():
                errors[field] = "Owner must be an active family member."
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)
