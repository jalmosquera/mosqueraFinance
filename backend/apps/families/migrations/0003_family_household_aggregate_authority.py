from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def set_initial_household_aggregate_authorities(apps, schema_editor):
    Family = apps.get_model("families", "Family")
    FamilyMembership = apps.get_model("families", "FamilyMembership")
    database = schema_editor.connection.alias

    for family in Family.objects.using(database).filter(
        household_aggregate_authority__isnull=True
    ):
        initial_administrator = (
            FamilyMembership.objects.using(database)
            .filter(family_id=family.pk, role="ADMIN")
            .order_by("created_at", "pk")
            .first()
        )
        if initial_administrator is not None:
            family.household_aggregate_authority_id = initial_administrator.user_id
            family.save(update_fields=("household_aggregate_authority",))


class Migration(migrations.Migration):
    dependencies = [
        ("families", "0002_usernotificationpreference"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="family",
            name="household_aggregate_authority",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="household_aggregate_authority_families",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.RunPython(
            set_initial_household_aggregate_authorities,
            reverse_code=migrations.RunPython.noop,
        ),
    ]
