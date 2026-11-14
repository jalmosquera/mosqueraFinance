from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("incomes", "0001_initial")]

    operations = [
        migrations.AddField(
            model_name="incomemovement",
            name="correction_reason",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="incomemovement",
            name="is_reversal",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="incomemovement",
            name="replaces",
            field=models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="replacement", to="incomes.incomemovement"),
        ),
        migrations.AddField(
            model_name="incomemovement",
            name="reversal_of",
            field=models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="reversal", to="incomes.incomemovement"),
        ),
    ]
