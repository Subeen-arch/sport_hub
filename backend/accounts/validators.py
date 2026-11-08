import re

from django.core.exceptions import ValidationError


class SpecialCharacterPasswordValidator:
    def validate(self, password, user=None):
        if not re.search(r"[^\w\s]|_", password):
            raise ValidationError("Include at least one special character.", code="password_no_special")

    def get_help_text(self):
        return "Your password must contain at least one special character."
