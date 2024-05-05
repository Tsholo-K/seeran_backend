# python 
import hashlib
import json
import re
import uuid
import secrets

# django
from django.core.cache import cache

# restframework
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken
from rest_framework_simplejwt.exceptions import TokenError

# models 


# account id generator
def generate_account_id(prefix=''):
    while True:
        # Generate a UUID
        unique_part = uuid.uuid4().hex

        # Concatenate prefix and UUID and convert to string
        account_id = prefix + unique_part

        # Ensure it's exactly 15 digits long (2 for prefix and 13 for the rest)
        account_id = account_id[:15].ljust(15, '0')
        return account_id


# validate token
def validate_access_token(access_token):
    try:
        AccessToken(access_token).verify()
        # Access token is valid
        return access_token
    except TokenError:
        # Access token is invalid, try refreshing
        return None


# validate refresh token
def validate_refresh_token(refresh_token):
    try:
        RefreshToken(refresh_token).verify()
        # Refresh token is valid
        return refresh_token
    except TokenError:
        # Refresh token is invalid
        return None


# refresh access token
def refresh_access_token(refresh_token):
    try:
        refresh = RefreshToken(refresh_token)
        new_access_token = str(refresh.access_token)
        return new_access_token
    except TokenError:
        # Refresh token is invalid or expired
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


# rate limit function 
def rate_limit(request):
    # You can adjust the rate limit and key as needed
    rate_limit = 5  # Requests per hour
    body_unicode = request.body.decode('utf-8')

    try:
        body_data = json.loads(body_unicode)
    except json.JSONDecodeError:
        return Response({'error': 'Invalid JSON'})

    email = body_data.get('email')

    if email is None:
        return Response({'error': 'Email is required'})

    cache_key = f'rate_limit:{email}'

    request_count = cache.get(cache_key, 0)
    if request_count >= rate_limit:
        return Response({'error': 'Rate limit exceeded. Please try again in 1 hour.'})

    # Increment the request count and set expiry
    cache.set(cache_key, request_count + 1, timeout=3600)  # 3600 seconds = 1 hour


def validate_user_email(email):
    # Regular expression pattern for basic email format validation
    pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'
    return re.match(pattern, email)


def generate_access_token(user):
    # Create a refresh token
    refresh = RefreshToken.for_user(user)
    # Optionally, access the access token and its payload
    access_token = refresh.access_token
    return access_token


def generate_token(user):
    # Create a refresh token
    refresh = RefreshToken.for_user(user)
    # Optionally, access the access token and its payload
    access_token = refresh.access_token
    refresh_token = str(refresh)  # Get the string representation of the refresh token
    # Create a refresh token
    return  {"access_token" : access_token , "refresh_token" : refresh_token }


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