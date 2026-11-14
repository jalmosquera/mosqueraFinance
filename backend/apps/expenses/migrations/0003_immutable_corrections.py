from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("expenses", "0002_expenseforecast_cigarettes")]

    operations = [
        migrations.AddField(
            model_name="expensemovement",
            name="correction_reason",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="expensemovement",
            name="is_reversal",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="expensemovement",
            name="replaces",
            field=models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="replacement", to="expenses.expensemovement"),
        ),
        migrations.AddField(
            model_name="expensemovement",
            name="reversal_of",
            field=models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="reversal", to="expenses.expensemovement"),
        ),
    ]
