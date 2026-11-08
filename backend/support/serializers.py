from rest_framework import serializers
from common.serializers import StrictSerializer
from .models import ContactMessage


class ContactInputSerializer(StrictSerializer):
    name = serializers.CharField(max_length=100)
    email = serializers.EmailField(max_length=254)
    phone = serializers.RegexField(r"\A[0-9]{10}\Z", max_length=10)
    country_code = serializers.ChoiceField(choices=["+977", "+91"], default="+977")
    message = serializers.CharField(max_length=500)

    def validate_email(self, value):
        return value.lower()


class ContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContactMessage
        fields = ["id", "name", "email", "phone", "country_code", "message", "created_at"]
        read_only_fields = fields
