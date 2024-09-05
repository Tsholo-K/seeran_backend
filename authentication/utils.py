# python 
from datetime import timedelta
import hashlib
import re
import secrets
import base64
import requests
from decouple import config

# restframework
from rest_framework_simplejwt.tokens import AccessToken as validate, RefreshToken
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework.response import Response
from rest_framework import status

# django
from django.utils import timezone
from django.db import transaction

# models
from access_tokens.models import AccessToken


def manage_user_sessions(user, token, max_sessions=3):
    """
    Manages user sessions by expiring old tokens and limiting the number of active sessions.
    
    Args:
        user: The user for whom the session is being managed.
        token: The new access token generated for the user.
        max_sessions (int): The maximum number of active sessions allowed. Defaults to 3.
        
    Returns:
        response (Response): A DRF Response object indicating the outcome.
        status_code (int): HTTP status code indicating success or error.
    """
    try:
        cutoff_time = timezone.now() - timedelta(hours=24)
        
        # Expire old access tokens (older than 24 hours)
        with transaction.atomic():
            expired_access_tokens = user.access_tokens.filter(created_at__lt=cutoff_time)
            if expired_access_tokens.exists():
                expired_access_tokens.delete()

        # Check the number of active sessions
        access_tokens_count = user.access_tokens.count()

        if access_tokens_count >= max_sessions:
            return Response({"error": "You have reached the maximum number of connected devices. Please disconnect another device to proceed"}, status=status.HTTP_403_FORBIDDEN)
        
        # Create a new access token record
        with transaction.atomic():
            AccessToken.objects.create(user=user, token=token['access'])

        return None  # No error, so return None

    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def send_otp_email(user, otp, reason):
    """
    Sends an OTP email to the specified user.

    Args:
        user (BaseUser): The user object to whom the OTP is to be sent.
        otp (str): The one-time passcode to be included in the email.

    Returns:
        dict: A dictionary containing the response status and any relevant message.
    """
    mailgun_api_url = f"https://api.eu.mailgun.net/v3/{config('MAILGUN_DOMAIN')}/messages"
    email_data = {
        "from": f"seeran grades <authorization@{config('MAILGUN_DOMAIN')}>",
        "to": f"{user.surname.title()} {user.name.title()}<{user.email}>",
        "subject": "One Time Passcode",
        "template": "one-time passcode",
        "v:onetimecode": otp,
        "v:otpcodereason": reason
    }
    headers = {
        "Authorization": "Basic " + base64.b64encode(f"api:{config('MAILGUN_API_KEY')}".encode()).decode(),
        "Content-Type": "application/x-www-form-urlencoded"
    }

    response = requests.post(mailgun_api_url, headers=headers, data=email_data)

    if response.status_code == 200:
        return {"status": "success"}
    elif response.status_code in [400, 401, 402, 403, 404]:
        return {"status": "error", "message": f"There was an error sending the OTP to your email address. Please open a new bug ticket with the issue, error code {response.status_code}"}
    elif response.status_code == 429:
        return {"status": "error", "message": "There was an error sending the OTP to your email address. Please try again in a few moments"}
    else:
        return {"status": "error", "message": "There was an error sending the OTP to your email address."}


# validate token
def validate_access_token(access_token):
    try:
        validate(access_token).verify()
        # Access token is valid
        return access_token
    except TokenError:
        # Access token is invalid, try refreshing
        return None


# otp generation function
def generate_otp():
    otp = str(secrets.randbelow(900000) + 100000)
    # Generate a random salt
    salt = secrets.token_bytes(16)
    # Convert the salt to hexadecimal
    salt_hex = salt.hex()
    
    # Combine the OTP and the salt, then hash them
    hashed_otp = hashlib.sha256((otp + salt_hex).encode()).hexdigest()
    
    # Return the OTP, hashed OTP, and salt
    return otp, hashed_otp, salt_hex


# otp verification function
def verify_user_otp(user_otp, stored_hashed_otp_and_salt):
    stored_hashed_otp, salt_hex = stored_hashed_otp_and_salt
    hashed_user_otp = hashlib.sha256((user_otp + salt_hex).encode()).hexdigest()

    return hashed_user_otp == stored_hashed_otp


def generate_token(user):
    # Create a refresh token
    refresh = RefreshToken.for_user(user)
    # Optionally, access the access token and its payload
    access_token = refresh.access_token

    # Create a refresh token
    return  {"access" : access_token }


def get_upload_path(instance, filename):
    if instance.role == "PARENT":
        return 'parents_profile_pictures/{}'.format(filename)
    elif instance.role == "TEACHER":
        return 'teachers_profile_pictures/{}'.format(filename)
    elif instance.role == "ADMIN":
        return 'admins_profile_pictures/{}'.format(filename)
    elif instance.role == "FOUNDER":
        return 'founders_profile_pictures/{}'.format(filename)
    else:
        return 'students_profile_pictures/{}'.format(filename)
    
    
def validate_names(names):
    parts = names.split(' ')
    if len(parts) == 2:
        return True
 
    else:
        return False


def is_valid_human_name(name):
    # Valid characters typically found in human names
    valid_characters = re.compile(r'^[a-zA-Z\-\'\s]+$')
    
    # Check if the string contains more than one part when split by a space
    parts = name.strip().split(' ')
    if len(parts) > 1:
        return "name should not be splittable. please provide a single full name/surname without spaces"
    
    # Check if the name contains only valid characters
    if not valid_characters.match(name):
        return "name/surname contains invalid characters"
    
    return True