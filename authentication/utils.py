# python 
import hashlib
import random

# django
from django.core.exceptions import SuspiciousOperation

# restframework
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken
from rest_framework import status
from rest_framework_simplejwt.exceptions import TokenError


def validate_and_refresh_tokens(access_token, refresh_token):
    try:
        AccessToken(access_token).verify()
        # Access token is valid
        return access_token, None
    except TokenError:
        # Access token is invalid, try refreshing
        if refresh_token:
            try:
                refresh = RefreshToken(refresh_token)
                new_access_token = str(refresh.access_token)
                return new_access_token, None
            except TokenError:
                # Refresh token is invalid or expired
                return None, Response({"error": "Invalid or expired refresh token"}, status=401)
        else:
            # No refresh token provided
            return None, Response({"error": "Access token is invalid and no refresh token provided"}, status=401)

# functions
# otp generation function
def generate_otp():
    otp = str(random.randint(100000, 999999))
    hashed_otp = hashlib.sha256(otp.encode()).hexdigest()
    # Generate timestamp for 5 minutes from now
    return otp, hashed_otp

# otp verification function
def verify_otp(user_otp, stored_hashed_otp):
    hashed_user_otp = hashlib.sha256(user_otp.encode()).hexdigest()
    return hashed_user_otp == stored_hashed_otp
