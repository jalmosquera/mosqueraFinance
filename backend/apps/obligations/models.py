from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q

from apps.finance.models import FamilyScopedManager


class ObligationStatus(models.TextChoices):
    PENDING = "PENDING", "Pending"
    PAID = "PAID", "Paid"
    VOIDED = "VOIDED", "Voided"


class PaymentObligation(models.Model):
    family = models.ForeignKey("families.Family", on_delete=models.CASCADE)
    income_forecast = models.ForeignKey(
        "incomes.IncomeForecast", null=True, blank=True, on_delete=models.PROTECT
    )
    expense_forecast = models.ForeignKey(
        "expenses.ExpenseForecast", null=True, blank=True, on_delete=models.PROTECT
    )
    source_period = models.DateField()
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT
    )
    account = models.ForeignKey("finance.LogicalAccount", on_delete=models.PROTECT)
    category = models.ForeignKey("finance.Category", on_delete=models.PROTECT)
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    due_on = models.DateField()
    description = models.CharField(max_length=255, blank=True)
    allocations = models.JSONField(default=list, blank=True)
    status = models.CharField(
        max_length=7, choices=ObligationStatus.choices, default=ObligationStatus.PENDING
    )
    income_movement = models.OneToOneField(
        "incomes.IncomeMovement", null=True, blank=True, on_delete=models.PROTECT
    )
    expense_movement = models.OneToOneField(
        "expenses.ExpenseMovement", null=True, blank=True, on_delete=models.PROTECT
    )
    void_reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = FamilyScopedManager()

    class Meta:
        ordering = ("due_on", "pk")
        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(income_forecast__isnull=False, expense_forecast__isnull=True)
                    | Q(income_forecast__isnull=True, expense_forecast__isnull=False)
                ),
                name="payment_obligation_one_forecast_source",
            ),
            models.UniqueConstraint(
                fields=("income_forecast", "source_period"),
                condition=Q(income_forecast__isnull=False),
                name="unique_income_obligation_period",
            ),
            models.UniqueConstraint(
                fields=("expense_forecast", "source_period"),
                condition=Q(expense_forecast__isnull=False),
                name="unique_expense_obligation_period",
            ),
        ]

    def clean(self):
        super().clean()
        errors = {}
        source = self.income_forecast or self.expense_forecast
        if bool(self.income_forecast_id) == bool(self.expense_forecast_id):
            errors["income_forecast"] = "An obligation must have exactly one forecast source."
        elif source and source.family_id != self.family_id:
            errors["family"] = "Forecast source must belong to the same family."
        if self.account_id and self.account.family_id != self.family_id:
            errors["account"] = "Account must belong to the same family."
        if self.category_id and self.category.family_id != self.family_id:
            errors["category"] = "Category must belong to the same family."
        if self.status == ObligationStatus.PAID:
            if bool(self.income_movement_id) == bool(self.expense_movement_id):
                errors["status"] = "Paid obligations must have exactly one settlement movement."
        elif self.income_movement_id or self.expense_movement_id:
            errors["status"] = "Only paid obligations can have a settlement movement."
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)
