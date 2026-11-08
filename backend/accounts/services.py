from uuid import uuid4

from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError, transaction
from rest_framework.exceptions import ValidationError

from .models import User


class AccountService:
    """Own account mutations and session lifecycle; HTTP views only coordinate."""

    backend = "accounts.authentication.CaseInsensitiveAccountBackend"
    identity_constraints = {
        "user_email_case_insensitive_unique": "email",
        "accounts_user_email_key": "email",
        "user_username_case_insensitive_unique": "username",
        "accounts_user_username_key": "username",
    }

    def __init__(self, request):
        self.request = request

    def _validate_password(self, user, password, confirmation, field):
        if password != confirmation:
            raise ValidationError({"password_confirm": ["Passwords do not match."]})
        try:
            validate_password(password, user=user)
        except DjangoValidationError as exc:
            raise ValidationError({field: exc.messages}) from exc

    def _identity_conflict(self, exc):
        diagnostic = getattr(exc.__cause__, "diag", None)
        field = self.identity_constraints.get(getattr(diagnostic, "constraint_name", None))
        if field:
            raise ValidationError({field: [f"An account already uses this {field}."]}) from exc
        raise exc

    def register(self, data):
        user = User(
            username=f"customer_{uuid4().hex}",
            **{field: data[field] for field in ("name", "email", "phone", "country_code")},
        )
        self._validate_password(user, data["password"], data["password_confirm"], "password")
        user.set_password(data["password"])
        try:
            with transaction.atomic():
                user.save()
        except IntegrityError as exc:
            self._identity_conflict(exc)
        login(self.request, user, backend=self.backend)
        return user

    def sign_in(self, data):
        user = authenticate(self.request, **data)
        if user is None:
            raise ValidationError({"detail": "The sign-in details are incorrect."})
        login(self.request, user)
        return user

    def sign_out(self):
        logout(self.request)

    def update_profile(self, data):
        try:
            with transaction.atomic():
                user = User.objects.select_for_update().get(pk=self.request.user.pk)
                # Keep ownership and role rules inside the service as well as the serializer.
                allowed = {"name", "email", "phone", "country_code"}
                if user.is_staff:
                    allowed.add("username")
                if set(data) - allowed:
                    raise ValidationError({"detail": "This profile field cannot be changed."})
                for field, value in data.items():
                    setattr(user, field, value)
                user.save()
        except IntegrityError as exc:
            self._identity_conflict(exc)
        return user

    def change_password(self, data):
        with transaction.atomic():
            user = User.objects.select_for_update().get(pk=self.request.user.pk)
            if not user.check_password(data["old_password"]):
                raise ValidationError({"old_password": ["Your current password is incorrect."]})
            self._validate_password(user, data["new_password"], data["password_confirm"], "new_password")
            user.set_password(data["new_password"])
            user.save(update_fields=["password"])
        update_session_auth_hash(self.request, user)
