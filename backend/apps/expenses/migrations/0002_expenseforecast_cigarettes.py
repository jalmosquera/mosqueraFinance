from django.db import migrations, models
from django.db.models import Q


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0001_initial"),
        ("expenses", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="expenseforecast",
            name="is_cigarettes",
            field=models.BooleanField(default=False),
        ),
        migrations.AddConstraint(
            model_name="expenseforecast",
            constraint=models.UniqueConstraint(
                condition=Q(("is_cigarettes", True), ("owner__isnull", True)),
                fields=("family",),
                name="one_shared_cigarettes_forecast_per_family",
            ),
        ),
        migrations.CreateModel(
            name="ExpenseForecastAllocation",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("amount", models.DecimalField(decimal_places=2, max_digits=14)),
                (
                    "forecast",
                    models.ForeignKey(
                        on_delete=models.deletion.CASCADE,
                        related_name="allocations",
                        to="expenses.expenseforecast",
                    ),
                ),
                (
                    "member",
                    models.ForeignKey(
                        on_delete=models.deletion.PROTECT,
                        to="accounts.user",
                    ),
                ),
            ],
        ),
        migrations.AddConstraint(
            model_name="expenseforecastallocation",
            constraint=models.CheckConstraint(
                condition=Q(("amount__gt", 0)),
                name="expense_forecast_allocation_amount_positive",
            ),
        ),
        migrations.AddConstraint(
            model_name="expenseforecastallocation",
            constraint=models.UniqueConstraint(
                fields=("forecast", "member"),
                name="unique_expense_forecast_allocation_member",
            ),
        ),
    ]
