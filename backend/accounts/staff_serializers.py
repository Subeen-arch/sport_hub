from django.contrib.auth.validators import UnicodeUsernameValidator
from rest_framework import serializers
from common.serializers import StrictSerializer
from .models import User


class StaffInputSerializer(StrictSerializer):
    username = serializers.CharField(max_length=150, validators=[UnicodeUsernameValidator()])
    name = serializers.CharField(max_length=100)
    email = serializers.EmailField(max_length=254)
    password = serializers.CharField(write_only=True, trim_whitespace=False, max_length=128)
    password_confirm = serializers.CharField(write_only=True, trim_whitespace=False, max_length=128)

    def validate_email(self, value):
        value = User.objects.normalize_email(value)
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError('An account already uses this email.')
        return value

    def validate_username(self, value):
        if User.objects.filter(username__iexact=value).exists():
            raise serializers.ValidationError('An account already uses this username.')
        return value
