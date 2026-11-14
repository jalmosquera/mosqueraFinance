from django.conf import settings
from django.db import models


class FamilyQuerySet(models.QuerySet):
    def visible_to(self, user):
        """Families where ``user`` has an active membership."""
        return self.filter(
            memberships__user=user, memberships__is_active=True
        ).distinct()


class FamilyManager(models.Manager.from_queryset(FamilyQuerySet)):
    pass


class Family(models.Model):
    name = models.CharField(max_length=120)
    created_at = models.DateTimeField(auto_now_add=True)

    objects = FamilyManager()

    class Meta:
        ordering = ("name", "pk")

    def __str__(self):
        return self.name


class FamilyMembershipQuerySet(models.QuerySet):
    def active(self):
        return self.filter(is_active=True)

    def visible_to(self, user):
        """Only the caller's active memberships."""
        return self.active().filter(user=user)

    def in_families_visible_to(self, user):
        """Memberships in a family where the caller is currently active."""
        return self.filter(
            family__memberships__user=user,
            family__memberships__is_active=True,
        ).distinct()

    def active_admin_for(self, user, family):
        return self.active().filter(
            user=user, family=family, role=FamilyMembership.Role.ADMIN
        )


class FamilyMembershipManager(models.Manager.from_queryset(FamilyMembershipQuerySet)):
    pass


class FamilyMembership(models.Model):
    class Role(models.TextChoices):
        ADMIN = "ADMIN", "Admin"
        MEMBER = "MEMBER", "Member"

    family = models.ForeignKey(
        Family, on_delete=models.CASCADE, related_name="memberships"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="family_memberships",
    )
    role = models.CharField(max_length=10, choices=Role.choices, default=Role.MEMBER)
    # Memberships are active when created unless an administrator explicitly deactivates them.
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = FamilyMembershipManager()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("family", "user"), name="unique_family_user_membership"
            ),
        ]
        indexes = [
            models.Index(
                fields=("user", "is_active"), name="membership_user_active_idx"
            ),
            models.Index(
                fields=("family", "is_active"), name="membership_family_active_idx"
            ),
        ]
        ordering = ("family_id", "pk")

    def __str__(self):
        return f"{self.user} in {self.family}"


class UserNotificationPreference(models.Model):
    class Permission(models.TextChoices):
        DEFAULT = "DEFAULT", "Default"
        GRANTED = "GRANTED", "Granted"
        DENIED = "DENIED", "Denied"

    family = models.ForeignKey(
        Family, on_delete=models.CASCADE, related_name="notification_preferences"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notification_preferences",
    )
    is_enabled = models.BooleanField(default=False)
    reminder_time = models.TimeField(null=True, blank=True)
    permission = models.CharField(
        max_length=10, choices=Permission.choices, default=Permission.DEFAULT
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("family", "user"), name="unique_family_user_notification_preference"
            ),
        ]
