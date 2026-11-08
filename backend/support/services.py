import hashlib
import json

from django.db import connection, transaction
from rest_framework.exceptions import ValidationError
from .models import ContactMessage


class ContactService:
    @transaction.atomic
    def submit(self, data, user):
        digest = hashlib.sha256(json.dumps(data, sort_keys=True).encode()).digest()
        lock_id = int.from_bytes(digest[:8], byteorder="big", signed=True)
        with connection.cursor() as cursor:
            cursor.execute("SELECT pg_advisory_xact_lock(%s)", [lock_id])
        if ContactMessage.objects.filter(**data).exists():
            raise ValidationError({"detail": "This message has already been sent."})
        return ContactMessage.objects.create(**data, user=user if user.is_authenticated else None)
