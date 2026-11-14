from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """Project user model, configured before the initial migration."""

    email = models.EmailField(unique=True)


class LoginThrottle(models.Model):
    """Shared rolling login-attempt window keyed by an anonymized fingerprint."""

    fingerprint = models.CharField(max_length=64, unique=True)
    attempts = models.PositiveIntegerField(default=0)
    window_started_at = models.DateTimeField()

    class Meta:
        indexes = [models.Index(fields=["window_started_at"])]
