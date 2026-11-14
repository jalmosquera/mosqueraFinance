from django.conf import settings
from django.db import models

from .exceptions import ImmutableAuditLogError


class AuditLogQuerySet(models.QuerySet):
    def update(self, **kwargs):
        raise ImmutableAuditLogError("Audit logs cannot be updated.")

    def delete(self):
        raise ImmutableAuditLogError("Audit logs cannot be deleted.")


class AuditLogManager(models.Manager.from_queryset(AuditLogQuerySet)):
    def create(self, **kwargs):
        raise ImmutableAuditLogError("Use audit.services.record_membership_mutation().")

    def bulk_create(self, objs, **kwargs):
        raise ImmutableAuditLogError("Audit logs cannot be bulk created.")

    def _create_for_service(self, **kwargs):
        audit_log = self.model(**kwargs)
        audit_log.save(force_insert=True, _from_audit_service=True)
        return audit_log


class AuditLog(models.Model):
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    action = models.CharField(max_length=64)
    family = models.ForeignKey("families.Family", on_delete=models.PROTECT)
    membership_target_id = models.BigIntegerField()
    metadata = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    objects = AuditLogManager()

    class Meta:
        ordering = ("-created_at", "-pk")

    def clean(self):
        super().clean()
        if not isinstance(self.metadata, dict):
            raise ImmutableAuditLogError("Audit metadata must be a JSON object.")

    def save(self, *args, _from_audit_service=False, **kwargs):
        if self._state.adding and not _from_audit_service:
            raise ImmutableAuditLogError(
                "Use audit.services.record_membership_mutation()."
            )
        if not self._state.adding:
            raise ImmutableAuditLogError("Audit logs cannot be updated.")
        self.full_clean()
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ImmutableAuditLogError("Audit logs cannot be deleted.")
