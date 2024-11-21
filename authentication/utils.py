# python 
import hashlib
import re
import secrets
import base64
import requests
from decouple import config

# settings
from django.conf import settings

# djnago
from django.apps import apps

# restframework
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken
from rest_framework_simplejwt.exceptions import TokenError


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
        "to": f"{user.surname.title()} {user.name.title()}<{user.email_address}>",
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
        # Get the Transcript model dynamically
        BaseAccount = apps.get_model('accounts', 'BaseAccount')

        AccessToken(access_token).verify()

        decoded_token = AccessToken(access_token)
        # BaseAccount.objects.get(id=decoded_token['user_id'])

        return access_token

    except (TokenError, BaseAccount.DoesNotExist):
        return None


def remove_authorization_cookies(response):
    response.delete_cookie('access_token', domain=settings.SESSION_COOKIE_DOMAIN)
    response.delete_cookie('session_authenticated', domain=settings.SESSION_COOKIE_DOMAIN)

    return response


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