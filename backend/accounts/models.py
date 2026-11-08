from django.contrib.auth.models import AbstractUser, UserManager
from django.core.validators import RegexValidator
from django.db import models
from django.db.models.functions import Lower


class AccountManager(UserManager):
    @classmethod
    def normalize_email(cls, email):
        return (email or "").strip().lower()


class User(AbstractUser):
    email = models.EmailField(unique=True)
    name = models.CharField(max_length=100)
    phone = models.CharField(max_length=10, blank=True, validators=[RegexValidator(r"^\d{10}$", "Enter a 10-digit phone number.")])
    country_code = models.CharField(max_length=5, default="+977", validators=[RegexValidator(r"^\+\d{1,4}$", "Enter a valid country code.")])
    objects = AccountManager()
    REQUIRED_FIELDS = ["email", "name"]

    class Meta:
        constraints = [
            models.UniqueConstraint(Lower("email"), name="user_email_case_insensitive_unique"),
            models.UniqueConstraint(Lower("username"), name="user_username_case_insensitive_unique"),
        ]

    def save(self, *args, **kwargs):
        self.email = self.email.strip().lower()
        self.username = self.username.strip()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name or self.username
