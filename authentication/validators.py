from django.core.exceptions import ValidationError
import re


# dont remove this user variable, it's used to match other django validators as they all take in password and user
# so removing the user variable will raise this error 
# "PasswordValidator.validate() takes 2 positional arguments but 3 were given"
class PasswordValidator:
    def validate(self, password, user=None):
        if len(password) < 8:
            raise ValidationError("Password must be at least 8 characters long")
        if len(password) > 128:
            raise ValidationError("Password cannot exceed 128 characters")
        if not re.search('[a-z]', password):
            raise ValidationError("Password must contain at least one lowercase letter")
        if not re.search('[A-Z]', password):
            raise ValidationError("Password must contain at least one uppercase letter")
        if not re.search('[0-9]', password):
            raise ValidationError("Password must contain at least one digit")
        if not re.search('[!@#$%^&*(),.?":{}|<>]', password):
            raise ValidationError("Password must contain at least one special character")

    def get_help_text(self):
        return "Your password must be at least 8 characters long, contain at least one lowercase letter, one uppercase letter, one digit, and one special character"

