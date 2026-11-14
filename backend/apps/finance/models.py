import unicodedata

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q


def normalize_name(value):
    return unicodedata.normalize("NFKC", value).strip().casefold()


class FamilyScopedQuerySet(models.QuerySet):
    def visible_to(self, user):
        """Records shared with the caller or privately owned by the caller."""
        return (
            self.filter(
                family__memberships__user=user,
                family__memberships__is_active=True,
            )
            .filter(Q(owner=user) | Q(owner__isnull=True))
            .distinct()
        )


class FamilyScopedManager(models.Manager.from_queryset(FamilyScopedQuerySet)):
    pass


class FamilyScopedNamedModel(models.Model):
    family = models.ForeignKey(
        "families.Family", on_delete=models.CASCADE, related_name="%(class)ss"
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="%(class)s_records",
    )
    name = models.CharField(max_length=120)
    normalized_name = models.CharField(max_length=120, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)

    objects = FamilyScopedManager()

    class Meta:
        abstract = True
        ordering = ("normalized_name", "pk")

    def clean(self):
        super().clean()
        self.normalized_name = normalize_name(self.name)
        if not self.normalized_name:
            raise ValidationError({"name": "Name cannot be blank."})
        if self.owner_id and not self.family.memberships.filter(
            user_id=self.owner_id, is_active=True
        ).exists():
            raise ValidationError({"owner": "Owner must be an active family member."})
    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)


class LogicalAccount(FamilyScopedNamedModel):
    class Meta(FamilyScopedNamedModel.Meta):
        constraints = [
            models.UniqueConstraint(
                fields=("family", "owner", "normalized_name"),
                condition=Q(owner__isnull=False),
                name="unique_private_logical_account_name",
            ),
            models.UniqueConstraint(
                fields=("family", "normalized_name"),
                condition=Q(owner__isnull=True),
                name="unique_shared_logical_account_name",
            ),
        ]


class Category(FamilyScopedNamedModel):
    class Kind(models.TextChoices):
        INCOME = "INCOME", "Income"
        EXPENSE = "EXPENSE", "Expense"

    kind = models.CharField(max_length=7, choices=Kind.choices)

    class Meta(FamilyScopedNamedModel.Meta):
        constraints = [
            models.UniqueConstraint(
                fields=("family", "owner", "kind", "normalized_name"),
                condition=Q(owner__isnull=False),
                name="unique_private_category_name_kind",
            ),
            models.UniqueConstraint(
                fields=("family", "kind", "normalized_name"),
                condition=Q(owner__isnull=True),
                name="unique_shared_category_name_kind",
            ),
        ]
