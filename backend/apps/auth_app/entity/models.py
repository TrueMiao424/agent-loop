from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    display_name = models.CharField(max_length=64, blank=True, default="")
    role = models.CharField(max_length=32, default="operator")  # admin / pm / dev / operator

    class Meta:
        db_table = "users"
