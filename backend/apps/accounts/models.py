from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """Project user model, configured before the initial migration."""

    email = models.EmailField(unique=True)


# Create your models here.
