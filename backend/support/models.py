from django.conf import settings
from django.core.validators import RegexValidator
from django.db import models


class ContactMessage(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True, related_name="contact_messages")
    name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=10, validators=[RegexValidator(r"^\d{10}$", "Enter a 10-digit phone number.")])
    country_code = models.CharField(max_length=5, default="+977")
    message = models.CharField(max_length=500)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]
