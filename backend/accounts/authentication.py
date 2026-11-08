from django.contrib.auth.backends import ModelBackend
from rest_framework.authentication import SessionAuthentication

from .models import User


class CaseInsensitiveAccountBackend(ModelBackend):
    """Customers use email; the username login is reserved for staff."""

    def authenticate(self, request, username=None, password=None, email=None, **kwargs):
        if password is None or not (email or username):
            return None
        lookup = {"email__iexact": email} if email else {"username__iexact": username, "is_staff": True}
        try:
            user = User.objects.get(**lookup)
        except User.DoesNotExist:
            # Match the password-hashing cost of an existing account.
            User().set_password(password)
            return None
        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None


class CsrfSessionAuthentication(SessionAuthentication):
    """DRF normally skips CSRF for guests; login and registration need it too."""

    def authenticate(self, request):
        self.enforce_csrf(request)
        return super().authenticate(request)
