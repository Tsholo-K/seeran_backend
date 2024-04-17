from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model

User = get_user_model()

class EmailOrIdNumberModelBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        # Try to find the user by email
        user = User.objects.filter(email=username).first()

        # If no user is found, return None
        if not user:
            return None

        # Check the password for the found user
        if user.check_password(password):
            return user