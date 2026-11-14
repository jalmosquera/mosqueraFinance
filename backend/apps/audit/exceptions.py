from django.core.exceptions import ValidationError


class ImmutableAuditLogError(ValidationError):
    pass
