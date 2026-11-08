from django.contrib.auth.validators import UnicodeUsernameValidator
from rest_framework import serializers
from common.serializers import StrictSerializer

from .models import User


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "name", "email", "phone", "country_code", "is_staff"]
        read_only_fields = fields


class IdentitySerializer(StrictSerializer):
    name = serializers.CharField(max_length=100)
    email = serializers.EmailField(max_length=254)
    phone = serializers.RegexField(r"\A[0-9]{10}\Z", max_length=10, error_messages={"invalid": "Enter a 10-digit phone number."})
    country_code = serializers.ChoiceField(choices=["+977", "+91"])

    def validate_email(self, value):
        value = User.objects.normalize_email(value)
        matches = User.objects.filter(email__iexact=value)
        if self.instance:
            matches = matches.exclude(pk=self.instance.pk)
        if matches.exists():
            raise serializers.ValidationError("An account already uses this email.")
        return value


class RegistrationSerializer(IdentitySerializer):
    password = serializers.CharField(write_only=True, trim_whitespace=False, max_length=128)
    password_confirm = serializers.CharField(write_only=True, trim_whitespace=False, max_length=128)


class LoginSerializer(StrictSerializer):
    email = serializers.EmailField(required=False, max_length=254)
    username = serializers.CharField(required=False, max_length=150)
    password = serializers.CharField(write_only=True, trim_whitespace=False, max_length=128)

    def validate(self, attrs):
        if bool(attrs.get("email")) == bool(attrs.get("username")):
            raise serializers.ValidationError("Provide either email or staff username.")
        return attrs


class ProfileSerializer(IdentitySerializer):
    username = serializers.CharField(max_length=150, validators=[UnicodeUsernameValidator()], required=False)

    def validate_username(self, value):
        if not self.instance.is_staff:
            raise serializers.ValidationError("Only staff can change their username.")
        if User.objects.filter(username__iexact=value).exclude(pk=self.instance.pk).exists():
            raise serializers.ValidationError("An account already uses this username.")
        return value


class PasswordSerializer(StrictSerializer):
    old_password = serializers.CharField(write_only=True, trim_whitespace=False, max_length=128)
    new_password = serializers.CharField(write_only=True, trim_whitespace=False, max_length=128)
    password_confirm = serializers.CharField(write_only=True, trim_whitespace=False, max_length=128)
