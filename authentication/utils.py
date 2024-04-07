# python 
import hashlib
import random
import json
import time
import re

# django
from django.core.cache import cache

# restframework
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken
from rest_framework_simplejwt.exceptions import TokenError


# account id generator
def generate_account_id():
    # Generate a timestamp
    timestamp = int(time.time())

    # Generate a random number of length 5
    random_part = random.randint(10000, 99999)

    # Concatenate timestamp and random number and convert to string
    account_id = str(timestamp) + str(random_part)

    # Ensure it's exactly 13 digits long
    account_id = account_id[:13].ljust(13, '0')

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

# refresh token
def refresh_access_token(refresh_token):
    try:
        refresh = RefreshToken(refresh_token)
        new_access_token = str(refresh.access_token)
        return new_access_token
    except TokenError:
        # Refresh token is invalid or expired
        return None

# functions
# otp generation function
def generate_otp():
    otp = str(random.randint(100000, 999999))
    hashed_otp = hashlib.sha256(otp.encode()).hexdigest()
    # Generate timestamp for 5 minutes from now
    return otp, hashed_otp

# otp verification function
def verify_user_otp(user_otp, stored_hashed_otp):
    hashed_user_otp = hashlib.sha256(user_otp.encode()).hexdigest()
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
    return  RefreshToken.for_user(user)

    
