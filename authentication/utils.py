# python 
import hashlib
import re
import regex
import secrets
import base64
import requests
from decouple import config

# settings
from django.conf import settings

# restframework
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken
from rest_framework_simplejwt.exceptions import TokenError

# django
from django.core.cache import cache

# utility functions 
from accounts import utils as accounts_utilities


def send_otp_email(account, otp, reason, email_address=None):
    """
    Sends an OTP email to the specified account.

    Args:
        account (BaseUser): The user object to whom the OTP is to be sent.
        otp (str): The one-time passcode to be included in the email.

    Returns:
        dict: A dictionary containing the response status and any relevant message.
    """
    mailgun_api_url = f"https://api.eu.mailgun.net/v3/{config('MAILGUN_DOMAIN')}/messages"

    recipient_email = email_address or account.email_address
    email_data = {
        "from": f"seeran grades <authorization@{config('MAILGUN_DOMAIN')}>",
        "to": f"{account.surname.title()} {account.name.title()}<{recipient_email}>",
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
        AccessToken(access_token).verify()
        return access_token
    except TokenError:
        return None


# remove access credentials from a request
def remove_authorization_cookies(response):
    response.delete_cookie('access_token', domain=settings.SESSION_COOKIE_DOMAIN)
    response.delete_cookie('session_authenticated', domain=settings.SESSION_COOKIE_DOMAIN)
    return response


# verifies wether an account can access the system, by checking the compliance status of the linked school account
def accounts_access_control(account):
    if account.role in ['PRINCIPAL', 'ADMIN', 'TEACHER', 'STUDENT']:
        # Fetch the corresponding child model based on the user's role
        requesting_account = accounts_utilities.get_account_and_linked_school(account.account_id, account.role)

        if requesting_account.school.none_compliant:
            return Response({"denied": "Could not process your request, access denied. Your school no longer has an active account on our system."}, status=status.HTTP_403_FORBIDDEN)
    return None


def set_cookie(response, key, value, httponly=True, max_age=300):
    response.set_cookie(
        key,
        value,
        domain=settings.SESSION_COOKIE_DOMAIN,
        samesite=settings.SESSION_COOKIE_SAMESITE,
        secure=True,
        httponly=httponly,
        max_age=max_age,
    )


def generate_and_cache_otp(otp_key, timeout=300):
    otp, hashed_otp, salt = generate_otp()
    cache.set(otp_key, (hashed_otp, salt), timeout=timeout)
    return otp


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
def verify_user_otp(account_otp, stored_hashed_otp_and_salt):
    stored_hashed_otp, salt_hex = stored_hashed_otp_and_salt
    hashed_user_otp = hashlib.sha256((account_otp + salt_hex).encode()).hexdigest()
    return hashed_user_otp == stored_hashed_otp


def generate_token(account):
    # Create a refresh token
    refresh = RefreshToken.for_user(account)
    # Optionally, access the access token and its payload
    access_token = refresh.access_token
    # Create a refresh token
    return  {"access" : access_token }
    

def validate_names(full_name):
    # Ensure the input is a non-empty string
    if not full_name or not isinstance(full_name, str):
        return Response(
            {"error": "Could not process your request, full name is required and must be a valid string of text containing your name and surname in any order."}, 
            status=status.HTTP_400_BAD_REQUEST
        )

    # Strip leading and trailing spaces, and split the name into parts
    parts = full_name.strip().split(' ')

    # Check that there are exactly two parts (name and surname)
    if len(parts) < 2:
        return Response(
            {"error": "Could not process your request, full name must contain at least a first name and a last name (surname)."}, 
            status=status.HTTP_400_BAD_REQUEST
        )

    if len(parts) > 2:
        return Response(
            {"error": "Could not process your request, full name must only contain a first name and a last name (surname) separated by whitespace (space)."}, 
            status=status.HTTP_400_BAD_REQUEST
        )

    # Define a regex pattern for broad human naming conventions
    # - Allows letters (including accented letters)
    # - Permits hyphens and apostrophes as internal characters
    # - Handles names from various languages and scripts
    name_pattern = regex.compile(r"^[\p{L}][\p{L}'\-]*$", regex.UNICODE)

    # Validate each part of the name
    for part in parts:
        if not name_pattern.match(part):
            return Response(
                {"error": f"Could not process your request, Invalid name part: '{part}'. Names can only contain letters, hyphens, or apostrophes."}, 
                status=status.HTTP_403_FORBIDDEN
            )

    return None


def is_valid_human_name(name):
    # Valid characters typically found in human names
    valid_characters = regex.compile(r'^[a-zA-Z\-\'\s]+$')
    # Check if the string contains more than one part when split by a space
    parts = name.strip().split(' ')
    if len(parts) > 1:
        return "name should not be splittable. please provide a single full name/surname without spaces"
    # Check if the name contains only valid characters
    if not valid_characters.match(name):
        return "name/surname contains invalid characters"
    return True