# python
import json
from decouple import config
import datetime
import os

# rest framework
from rest_framework.decorators import api_view, parser_classes
from rest_framework.response import Response
from rest_framework.exceptions import AuthenticationFailed
from rest_framework import status
from rest_framework_simplejwt.tokens import AccessToken
from .serializers import CustomTokenObtainPairSerializer
from rest_framework.parsers import MultiPartParser, FormParser


# django
from django.contrib.auth.hashers import check_password
from django.core.mail import BadHeaderError
from django.core.exceptions import ObjectDoesNotExist
from django.core.cache import cache
from django.contrib.auth.hashers import make_password
from django.views.decorators.cache import cache_control
from django.views.decorators.csrf import csrf_exempt

# boto
import boto3
from botocore.exceptions import BotoCoreError
from botocore.signers import CloudFrontSigner

# cryptography
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import padding

# models
from .models import CustomUser, BouncedComplaintEmail

# serializers

# amazon email sending service
import boto3
from botocore.exceptions import BotoCoreError, ClientError

# utility functions 
from .utils import validate_access_token, generate_access_token, generate_token, generate_otp, verify_user_otp, validate_user_email

# custom decorators
from .decorators import token_required

# root url 
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# cloudfront url signer 
def rsa_signer(message):
    with open(os.path.join(BASE_DIR, 'private_key.pem'), 'rb') as key_file:
        private_key = serialization.load_pem_private_key(
            key_file.read(),
            password=None,
            backend=default_backend()
        )
    return private_key.sign(message, padding.PKCS1v15(), hashes.SHA1())
key_id = 'K1E45RUK43W3WT'
cloudfront_signer = CloudFrontSigner(key_id, rsa_signer)

# views
# login view
@api_view(['POST'])
def login(request):
    try:
        serializer = CustomTokenObtainPairSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        token = serializer.validated_data
    except AuthenticationFailed:
        return Response({"error": "invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    try:
        user = CustomUser.objects.get(email=request.data.get('email'))
    except ObjectDoesNotExist:
        return Response({"error": "invalid credentials/tokens"})
    #  mfa enabled
    if user.multifactor_authentication:
        # if the users email has recently been banned, disable multi-factor authentication because it requires we send an otp to them via email
        # then log them in without multi-factor authentication 
        if user.email_banned:
            user.multifactor_authentication = False
            user.save()
            try:    
                if user.is_principal or user.is_admin:
                    role = 'admin'
                elif user.is_parent:
                    role = 'parent'
                else:
                    role = 'student'
                # Getting the current date and time
                dt = datetime.now()
                # Getting the timestamp
                ts = round(datetime.timestamp(dt))
                # the alert key is used on the frontend to alert the user of their email being banned and what they can do to appeal(if they can)
                response = Response({"message": "login successful", "role": role, "alert" : "email in blacklist", "invalidator" : ts}, status=status.HTTP_200_OK)
                # Set access token cookie with custom expiration (5 mins)
                response.set_cookie('access_token', token['access'], domain='.seeran-grades.com', samesite='None', secure=True, httponly=True, max_age=300)
                if 'refresh' in token:
                    # Set refresh token cookie
                    response.set_cookie('refresh_token', token['refresh'], domain='.seeran-grades.com', samesite='None', secure=True, httponly=True, max_age=86400)
                return response
            except Exception as e:
                return Response({"error": f"there was an error logging you in"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        otp, hashed_otp = generate_otp()
        # Send the OTP via email
        try:
            client = boto3.client('ses', region_name='af-south-1')  # AWS region
            # Read the email template from a file
            with open('authentication/templates/authentication/emailotptemplate.html', 'r') as file:
                email_body = file.read()
            # Replace the {{otp}} placeholder with the actual OTP
            email_body = email_body.replace('{{otp}}', otp)
            response = client.send_email(
                Destination={
                    'ToAddresses': [user.email],
                },
                Message={
                    'Body': {
                        'Html': {
                            'Data': email_body,
                        },
                    },
                    'Subject': {
                        'Data': 'One Time Passcode',
                    },
                },
                Source='seeran grades <authorization@seeran-grades.com>',  # SES verified email address
            )
            # Check the response to ensure the email was successfully sent
            if response['ResponseMetadata']['HTTPStatusCode'] == 200:
                cache.set(user.email, hashed_otp, timeout=300)  # 300 seconds = 5 mins
                authorization_otp, hashed_authorization_otp = generate_otp()
                cache.set(user.email+'authorization_otp', hashed_authorization_otp, timeout=300)  # 300 seconds = 5 mins
                response = Response({"message": "a new OTP has been sent to your email address"}, status=status.HTTP_200_OK)
                response.set_cookie('authorization_otp', authorization_otp, domain='.seeran-grades.com', samesite='None', secure=True, httponly=True, max_age=300)  # 300 seconds = 5 mins
                return response
            else:
                return Response({"error": "failed to send OTP to your specified email"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except (BotoCoreError, ClientError) as error:
            # Handle specific errors and return appropriate responses
            return Response({"error": f"email not sent: {error}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except BadHeaderError:
            return Response({"error": "invalid header found."}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
    # mfa disabled
    try: 
        if user.is_principal or user.is_admin:
            role = 'admin'
        elif user.is_parent:
            role = 'parent'
        else:
            role = 'student'
        # Getting the current date and time
        dt = datetime.now()
        # Getting the timestamp
        ts = round(datetime.timestamp(dt))
        response = Response({"message": "login successful", "role": role, "invalidator" : ts}, status=status.HTTP_200_OK)
        # Set access token cookie with custom expiration (5 mins)
        response.set_cookie('access_token', token['access'], domain='.seeran-grades.com', samesite='None', secure=True, httponly=True, max_age=300)
        if 'refresh' in token:
            # Set refresh token cookie
            response.set_cookie('refresh_token', token['refresh'], domain='.seeran-grades.com', samesite='None', secure=True, httponly=True, max_age=86400)
        return response
    except Exception as e:
        return Response({"error": f"there was an error logging you in"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# multi-factor login view
@api_view(['POST'])
def multi_factor_authentication(request):
    email = request.data.get('email')
    otp = request.data.get('otp')
    authorization_cookie_otp = request.COOKIES.get('authorization_otp')
    if not email or not otp or not authorization_cookie_otp:
        return Response({"error": "missing credentials"}, status=status.HTTP_400_BAD_REQUEST)
    try:
        user = CustomUser.objects.get(email=email)
    except ObjectDoesNotExist:
        return Response({"error": "invalid credentials"})
    try:
        stored_hashed_otp = cache.get(user.email)
        if not stored_hashed_otp:
            return Response({"error": "OTP expired. Please generate a new one"}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response({"error": f"error retrieving OTP from cache: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    if verify_user_otp(user_otp=otp, stored_hashed_otp=stored_hashed_otp):
        # OTP is verified, prompt the user to set their password
        try:
            hashed_authorization_otp = cache.get(user.email + 'authorization_otp')
            if not hashed_authorization_otp:
                return Response({"error": "OTP expired, please reload the page to request a new OTP"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": f"error retrieving OTP from cache: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        if not verify_user_otp(authorization_cookie_otp, hashed_authorization_otp):
            return Response({"error": "incorrect authorization OTP, action forrbiden"}, status=status.HTTP_400_BAD_REQUEST)
        cache.delete(user.email)
        cache.delete(user.email + 'authorization_otp')
        token = generate_token(user)
        try:    
            if user.is_principal or user.is_admin:
                role = 'admin'
            elif user.is_parent:
                role = 'parent'
            else:
                role = 'student'
            # Getting the current date and time
            dt = datetime.now()
            # Getting the timestamp
            ts = round(datetime.timestamp(dt))
            response = Response({"message": "login successful, welcome back.", "role": role, "invalidator" : ts}, status=status.HTTP_200_OK)
            # Set access token cookie with custom expiration (5 mins)
            response.set_cookie('access_token', token['access_token'], domain='.seeran-grades.com', samesite='None', secure=True, httponly=True, max_age=300)
            # Set refresh token cookie
            response.set_cookie('refresh_token', token['refresh_token'], domain='.seeran-grades.com', samesite='None', secure=True, httponly=True, max_age=86400)
            return response
        except Exception as e:
            return Response({"error": f"error logging you in: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    else:
        return Response({"error": "incorrect OTP. Please try again."}, status=status.HTTP_400_BAD_REQUEST)
    
# sign in view
@api_view(['POST'])
def signin(request):
    name = request.data.get('name')
    surname = request.data.get('surname')
    email = request.data.get('email')
    if not name or not surname or not email:
        return Response({"error": "all feilds are required"})
    # Validate the user
    try:
        user = CustomUser.objects.get(name=name, surname=surname, email=email)
    except ObjectDoesNotExist:
        return Response({"error": "invalid credentials"})
    if user.email_banned:
        return Response({ "error" : "your email has been banned"})
    if user.password != '' and user.has_usable_password():
        return Response({"error": "account already activated"}, status=403)
    # Create an OTP for the user
    otp, hashed_otp = generate_otp()
    # Send the OTP via email
    try:
        client = boto3.client('ses', region_name='af-south-1')  # AWS region
        # Read the email template from a file
        with open('authentication/templates/authentication/emailotptemplate.html', 'r') as file:
            email_body = file.read()
        # Replace the {{otp}} placeholder with the actual OTP
        email_body = email_body.replace('{{otp}}', otp)
        response = client.send_email(
            Destination={
                'ToAddresses': [email],
            },
            Message={
                'Body': {
                    'Html': {
                        'Data': email_body,
                    },
                },
                'Subject': {
                    'Data': 'One Time Passcode',
                },
            },
            Source='authorization@seeran-grades.com',  # SES verified email address
        )
        # Check the response to ensure the email was successfully sent
        if response['ResponseMetadata']['HTTPStatusCode'] == 200:
            cache.set(user.email, hashed_otp, timeout=300)  # 300 seconds = 5 mins
            return Response({"message": "OTP created and sent to your email", "email" : user.email}, status=status.HTTP_200_OK)
        else:
            return Response({"error": "failed to send OTP via email"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    except (BotoCoreError, ClientError) as error:
        # Handle specific errors and return appropriate responses
        return Response({"error": f"couldn't send email to the specified email"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    except BadHeaderError:
        return Response({"error": "invalid header found"}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

# activate multifactor authentication
@api_view(['POST'])
@token_required
def mfa_change(request):
    if request.user.email_banned:
        return Response({ "error" : "your email has been banned"})
    sent_email = request.data.get('email')
    toggle = request.data.get('toggle')
    if not sent_email or toggle == None:
        return Response({"error": "supplied credentials are invalid"})
    if not validate_user_email(sent_email):
        return Response({"error": " invalid email address"})
    # Validate the email
    if sent_email != request.user.email:
        return Response({"error" : "invalid email address for account"})
    # Validate toggle value
    request.user.multifactor_authentication = toggle
    request.user.save()
    return Response({'message': 'Multifactor authentication {} successfully'.format('enabled' if toggle else 'disabled')}, status=status.HTTP_200_OK)

# activate multifactor authentication
@api_view(['POST'])
@token_required
def event_emails_subscription(request):
    if request.user.email_banned:
        return Response({ "error" : "your email has been banned"})
    sent_email = request.data.get('email')
    toggle = request.data.get('toggle')
    if not sent_email or toggle == None:
        return Response({"error": "supplied credentials are invalid"})
    if not validate_user_email(sent_email):
        return Response({"error": " invalid email address"})
    # Validate the email
    if sent_email != request.user.email:
        return Response({"error" : "invalid email address for account"})
    # Validate toggle value
    request.user.event_emails = toggle
    request.user.save()
    return Response({'message': '{}'.format('subscribed to event emails' if toggle else 'unsubscribed from event emails')}, status=status.HTTP_200_OK)

# validate password before password change view
@api_view(['POST'])
@token_required
def validate_password(request):
    if request.user.email_banned:
        return Response({ "error" : "your email address has been banned"})
    sent_password = request.data.get('password')
    # make sure an password was sent
    if not sent_password:
        return Response({"error": "password is required"})
    # Validate the password
    if not check_password(sent_password, request.user.password):
        return Response({"error": "invalid password, please try again"}, status=status.HTTP_400_BAD_REQUEST)
    # Create an OTP for the user
    otp, hashed_otp = generate_otp()
    # Send the OTP via email
    try:
        client = boto3.client('ses', region_name='af-south-1')  # AWS region
        # Read the email template from a file
        with open('authentication/templates/authentication/emailotptemplate.html', 'r') as file:
            email_body = file.read()
        # Replace the {{otp}} placeholder with the actual OTP
        email_body = email_body.replace('{{otp}}', otp)
        response = client.send_email(
            Destination={
                'ToAddresses': [request.user.email],
            },
            Message={
                'Body': {
                    'Html': {
                        'Data': email_body,
                    },
                },
                'Subject': {
                    'Data': 'One Time Passcode',
                },
            },
            Source='seeran grades <authorization@seeran-grades.com>',  # SES verified email address
        )
        # Check the response to ensure the email was successfully sent
        if response['ResponseMetadata']['HTTPStatusCode'] == 200:
            cache.set(request.user.email, hashed_otp, timeout=300)  # 300 seconds = 5 mins
            return Response({"message": "password verified, OTP created and sent to your email", "users_email" : request.user.email}, status=status.HTTP_200_OK)
        else:
            return Response({"error": "failed to send OTP via email"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    except (BotoCoreError, ClientError) as error:
        # Handle specific errors and return appropriate responses
        return Response({"error": f"email not sent: {error}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    except BadHeaderError:
        return Response({"error": "invalid header found"}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

# validate email before email change view
@api_view(['POST'])
@token_required
def validate_email(request):
    if request.user.email_banned:
        return Response({ "error" : "your email address has been banned"})
    sent_email = request.data.get('email')   
    if not sent_email:
        return Response({"error": "email address is required"})
    if not validate_user_email(sent_email):
        return Response({"error": " invalid email address"})
    # Validate the email
    if sent_email != request.user.email:
        return Response({"error" : "invalid email address for account"})
    # Create an OTP for the user
    otp, hashed_otp = generate_otp()
    # Send the OTP via email
    try:
        client = boto3.client('ses', region_name='af-south-1')  # AWS region
        # Read the email template from a file
        with open('authentication/templates/authentication/emailotptemplate.html', 'r') as file:
            email_body = file.read()
        # Replace the {{otp}} placeholder with the actual OTP
        email_body = email_body.replace('{{otp}}', otp)
        response = client.send_email(
            Destination={
                'ToAddresses': [request.user.email],
            },
            Message={
                'Body': {
                    'Html': {
                        'Data': email_body,
                    },
                },
                'Subject': {
                    'Data': 'One Time Passcode',
                },
            },
            Source='seeran grades <authorization@seeran-grades.com>',  # SES verified email address
        )
        # Check the response to ensure the email was successfully sent
        if response['ResponseMetadata']['HTTPStatusCode'] == 200:
            # cache hashed otp and return reponse
            cache.set(sent_email, hashed_otp, timeout=300)  # 300 seconds = 5 mins
            return Response({"message": "email verified, OTP created and sent to your email"}, status=status.HTTP_200_OK)
        else:
            return Response({"error": "failed to send OTP via email"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    except (BotoCoreError, ClientError) as error:
        # Handle specific errors and return appropriate responses
        return Response({"error": f"email not sent: {error}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    except BadHeaderError:
        return Response({"error": "invalid header found"}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

# validate email before password change view
@api_view(['POST'])
def otp_verification(request):
    email = request.data.get('email')
    otp = request.data.get('otp')
    if not email or not otp:
        return Response({"error": "email and OTP are required."}, status=status.HTTP_400_BAD_REQUEST)
    try:
        stored_hashed_otp = cache.get(email)
        if not stored_hashed_otp:
            return Response({"error": "OTP expired. Please generate a new one"}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response({"error": f"error retrieving OTP from cache: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    if verify_user_otp(user_otp=otp, stored_hashed_otp=stored_hashed_otp):
        # OTP is verified, prompt the user to set their password
        try:
            user = CustomUser.objects.get(email=email)
        except ObjectDoesNotExist:
            return Response({"error": "invalid credentials/tokens"})
        access_token = generate_access_token(user)
        authorization_otp, hashed_authorization_otp = generate_otp()
        cache.set(user.email+'authorization_otp', hashed_authorization_otp, timeout=300)  # 300 seconds = 5 mins
        response = Response({"message": "OTP verified successfully"}, status=status.HTTP_200_OK)
        response.set_cookie('access_token', access_token, domain='.seeran-grades.com', samesite='None', secure=True, httponly=True, max_age=300)
        response.set_cookie('authorization_otp', authorization_otp, domain='.seeran-grades.com', samesite='None', secure=True, httponly=True, max_age=300)  # 300 seconds = 5 mins
        cache.delete(email)
        return response
    else:
        return Response({"error": "incorrect OTP. Please try again."}, status=status.HTTP_400_BAD_REQUEST)

# Password reset view
@api_view(['POST'])
def reset_password(request):
    access_token = request.COOKIES.get('access_token')
    # check if request contains required tokens
    if not access_token:
        return Response({"error" : "access token required"})
    new_access_token = validate_access_token(access_token)
    if new_access_token == None: 
        # Error occurred during validation/refresh, return the error response
        return Response({'error': 'invalid token'}, status=406)
    # Assuming the user is authenticated and has changed their password
    decoded_token = AccessToken(new_access_token)
    try:
        user = CustomUser.objects.get(pk=decoded_token['user_id'])
    except ObjectDoesNotExist:
        return Response({"error": "invalid credentials/tokens"})
    otp = request.COOKIES.get('authorization_otp')
    # Get the new password and confirm password from the request data
    new_password = request.data.get('new_password')
    confirm_password = request.data.get('confirm_password')
    if not new_password or not confirm_password or not otp:
        return Response({"error": "missing credentials"}, status=status.HTTP_400_BAD_REQUEST)
    try:
        hashed_authorization_otp = cache.get(user.email + 'authorization_otp')
        if not hashed_authorization_otp:
            return Response({"error": "OTP expired, please reload the page to request a new OTP"}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response({"error": f"error retrieving OTP from cache: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    if not verify_user_otp(otp, hashed_authorization_otp):
        return Response({"error": "incorrect OTP, action forrbiden"}, status=status.HTTP_400_BAD_REQUEST)
    # Validate that the new password and confirm password match
    if new_password != confirm_password:
        return Response({"error": "new password and confirm password do not match"}, status=status.HTTP_400_BAD_REQUEST)
    # Update the user's password
    user.set_password(new_password)
    user.save()
    try:
        # Return an appropriate response (e.g., success message)
        response = Response({"message": "password changed successfully"}, status=200)
        # Remove access token cookie from the response
        response.delete_cookie('access_token', domain='.seeran-grades.com')
        return response
    except:
        pass

# Password change view
@api_view(['POST'])
@token_required
def change_password(request):
    otp = request.COOKIES.get('authorization_otp')
    # Get the new password and confirm password from the request data
    new_password = request.data.get('new_password')
    confirm_password = request.data.get('confirm_password')
    if not new_password or not confirm_password or not otp:
        return Response({"error": "missing credentials"}, status=status.HTTP_400_BAD_REQUEST)
    try:
        hashed_authorization_otp = cache.get(request.user.email + 'authorization_otp')
        if not hashed_authorization_otp:
            return Response({"error": "OTP expired, please reload the page to request a new OTP"}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response({"error": f"error retrieving OTP from cache: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    if not verify_user_otp(otp, hashed_authorization_otp):
        return Response({"error": "incorrect OTP, action forrbiden"}, status=status.HTTP_400_BAD_REQUEST)
    # Validate that the new password and confirm password match
    if new_password != confirm_password:
        return Response({"error": "new password and confirm password do not match"}, status=status.HTTP_400_BAD_REQUEST)
    # Update the user's password
    request.user.set_password(new_password)
    request.user.save()
    try:
        # Return an appropriate response (e.g., success message)
        response = Response({"message": "password changed successfully"}, status=200)
        # Remove access and refresh token cookies from the response
        response.delete_cookie('access_token', domain='.seeran-grades.com')
        response.delete_cookie('refresh_token', domain='.seeran-grades.com')
        # blacklist refresh token
        refresh_token = request.COOKIES.get('refresh_token')
        cache.set(refresh_token, 'blacklisted', timeout=86400)
        return response
    except:
        pass
 
# change email view
@api_view(['POST'])
@token_required
def change_email(request):
    otp = request.COOKIES.get('authorization_otp')
    new_email = request.data.get('new_email')
    confirm_email = request.data.get('confirm_email')
    # make sure all required fields are provided
    if not new_email or not confirm_email or not otp:
        return Response({"error": "missing credentials"}, status=status.HTTP_400_BAD_REQUEST)
    # check if emails match 
    if new_email != confirm_email:
        return Response({"error": "emails do not match"}, status=status.HTTP_400_BAD_REQUEST)
    if new_email == request.user.email:
        return Response({"error": "cannot set current email as new email"}, status=status.HTTP_400_BAD_REQUEST)
    try:
        hashed_authorization_otp = cache.get(request.user.email + 'authorization_otp')
        if not hashed_authorization_otp:
            return Response({"error": "OTP expired, please reload the page to request a new OTP"}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response({"error": f"error retrieving OTP from cache: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    if not verify_user_otp(otp, hashed_authorization_otp):
        return Response({"error": "incorrect OTP, action forrbiden"}, status=status.HTTP_400_BAD_REQUEST)
    try:
        if not validate_user_email(new_email):
            return Response({'error': 'Invalid email format'}, status=400)
        request.user.email = new_email
        request.user.save()
        try:
            # Add the refresh token to the blacklist
            refresh_token = request.COOKIES.get('refresh_token')
            cache.set(refresh_token, 'blacklisted', timeout=86400)
            response = Response({"message": "email changed successfully"})
            # Clear the refresh token cookie
            response.delete_cookie('access_token', domain='.seeran-grades.com')
            response.delete_cookie('refresh_token', domain='.seeran-grades.com')
            return response
        except Exception as e:
            return Response({"error": e})
    except Exception as e:
        return Response({"error": f"error setting email: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(["GET"])
@token_required
def authenticate(request):
    if request.user.is_principal or request.user.is_admin:
        role = 'admin'
    elif request.user.is_parent:
        role = 'parent'
    else:
        role = 'student'
    return Response({"message" : "authenticated", "role" : role}, status=status.HTTP_200_OK)

# set password view
@api_view(['POST'])
def set_password(request):
    otp = request.COOKIES.get('authorization_otp')
    email = request.data.get('email')
    new_password = request.data.get('password')
    confirm_password = request.data.get('confirmpassword')
    if not email or not new_password or not confirm_password or not otp:
        return Response({"error": "email, new password and confrim password are required."}, status=status.HTTP_400_BAD_REQUEST)
    if new_password != confirm_password:
        return Response({"error": "passwords do not match"}, status=status.HTTP_400_BAD_REQUEST)
    try:
        hashed_authorization_otp = cache.get(email + 'authorization_otp')
        if not hashed_authorization_otp:
            return Response({"error": "OTP expired, please reload the page to request a new OTP"}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response({"error": f"error retrieving OTP from cache: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    if not verify_user_otp(otp, hashed_authorization_otp):
        return Response({"error": "incorrect OTP, action forbiden"}, status=status.HTTP_400_BAD_REQUEST)
    try:
        user = CustomUser.objects.get(email=email)
        user.password = make_password(new_password)
        user.save()
        return Response({"message": "password set successfully"}, status=status.HTTP_200_OK)
    except ObjectDoesNotExist:
        return Response({"error": "user does not exist."}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({"error": f"error setting password: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# Request otp view
@api_view(['POST'])
def resend_otp(request):
    email = request.data.get('email')
    if not email:
        return Response({"message" : "an email is required"}, status=status.HTTP_400_BAD_REQUEST)
    # try to get the user
    try:
        user = CustomUser.objects.get(email=email)
    except CustomUser.DoesNotExist:
        return Response({"error": "user with this email does not exist."}, status=status.HTTP_400_BAD_REQUEST)
    if user.email_banned:
        return Response({ "error" : "your email address has been banned"})
    otp, hashed_otp = generate_otp()
    # Send the OTP via email
    try:
        client = boto3.client('ses', region_name='af-south-1')  # AWS region
        # Read the email template from a file
        with open('authentication/templates/authentication/emailotptemplate.html', 'r') as file:
            email_body = file.read()
        # Replace the {{otp}} placeholder with the actual OTP
        email_body = email_body.replace('{{otp}}', otp)
        response = client.send_email(
            Destination={
                'ToAddresses': [email],
            },
            Message={
                'Body': {
                    'Html': {
                        'Data': email_body,
                    },
                },
                'Subject': {
                    'Data': 'One Time Passcode',
                },
            },
            Source='seeran grades <authorization@seeran-grades.com>',  # SES verified email address
        )
        # Check the response to ensure the email was successfully sent
        if response['ResponseMetadata']['HTTPStatusCode'] == 200:
            cache.set(user.email, hashed_otp, timeout=300)  # 300 seconds = 5 mins
            return Response({"message": "OTP created and sent to your email", "email" : user.email}, status=status.HTTP_200_OK)
        else:
            return Response({"error": "failed to send OTP via email"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    except (BotoCoreError, ClientError) as error:
        # Handle specific errors and return appropriate responses
        return Response({"error": f"couldn't send email to the specified email"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    except BadHeaderError:
        return Response({"error": "invalid header found"}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

# Verify otp view
@api_view(['POST'])
def verify_otp(request):
    email = request.data.get('email')
    otp = request.data.get('otp')
    if not email or not otp:
        return Response({"error": "email and OTP are required."}, status=status.HTTP_400_BAD_REQUEST)
    try:
        stored_hashed_otp = cache.get(email)
        if not stored_hashed_otp:
            return Response({"error": "OTP expired. Please generate a new one"}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response({"error": f"error retrieving OTP from cache: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    if verify_user_otp(user_otp=otp, stored_hashed_otp=stored_hashed_otp):
        # OTP is verified, prompt the user to set their password
        cache.delete(email)
        authorization_otp, hashed_authorization_otp = generate_otp()
        cache.set(email+'authorization_otp', hashed_authorization_otp, timeout=300)  # 300 seconds = 5 mins
        response = Response({"message": "OTP verified successfully"}, status=status.HTTP_200_OK)
        response.set_cookie('authorization_otp', authorization_otp, domain='.seeran-grades.com', samesite='None', secure=True, httponly=True, max_age=300)  # 300 seconds = 5 mins
        return response
    else:
        return Response({"error": "incorrect OTP. Please try again."}, status=status.HTTP_400_BAD_REQUEST)

# get credentials view
@api_view(["GET"])
@cache_control(max_age=3600, private=True)
@token_required
def user_info(request):
    if request.user.is_principal or request.user.is_admin:
        role = 'admin'
    elif request.user.is_parent:
        role = 'parent'
    else:
        role = 'student'
    return Response({ "email" : request.user.email, 'name': request.user.name, 'surname' : request.user.surname, "role" : role, "account_id" : request.user.account_id},status=200)

# get user image view
@api_view(["GET"])
@cache_control(max_age=3600, private=True)
@token_required
def user_image(request):
    if request.user.profile_picture == "":
        return Response({ "image_url" : None },status=200)
    s3_url = request.user.profile_picture.url
    cloudfront_url = s3_url.replace('https://seeran-storage.s3.amazonaws.com', 'https://d376l49ehaoi1m.cloudfront.net')
    signed_url = cloudfront_signer.generate_presigned_url(
        cloudfront_url, 
        date_less_than=datetime.datetime(2025, 1, 1)
    )
    return Response({ "image_url" : signed_url},status=200)

# get credentials view
@api_view(["GET"])
@cache_control(max_age=3600, private=True)
@token_required
def user_email(request):
    return Response({ "email" : request.user.email},status=200)

# get credentials view
@api_view(["GET"])
@cache_control(max_age=3600, private=True)
@token_required
def user_names(request):
    return Response({ "name" : request.user.name, "surname" : request.user.surname},status=200)

# checks the accounts multi-factor authentication status
@api_view(["GET"])
@token_required
def mfa_status(request):
    return Response({"mfa_status" : request.user.multifactor_authentication},status=200)

# account activation check
# checks if the account is activated by checking the password attr
@api_view(["POST"]) 
def account_status(request):
    email = request.data.get("email")
    # try to get the user
    try:
        user = CustomUser.objects.get(email=email)
    except CustomUser.DoesNotExist:
        return Response({"error": "user with the provided email does not exist."})
    if user.password != '' and user.has_usable_password():
        return Response({"error": "account already activated"})
    return Response({"message":"account not activated"})

# user logout view
@api_view(['POST'])
def logout(request):
    refresh_token = request.COOKIES.get('refresh_token')
    if refresh_token:
        try:
            # Add the refresh token to the blacklist
            response = Response({"message": "logout successful"})
            # Clear the refresh token cookie
            response.delete_cookie('access_token', domain='.seeran-grades.com')
            response.delete_cookie('refresh_token', domain='.seeran-grades.com')
            cache.set(refresh_token, 'blacklisted', timeout=86400)
            return response
        except Exception as e:
            return Response({"error": e})
    else:
        return Response({"error": "No refresh token provided"})

# user email events unsubscribe
@csrf_exempt
@api_view(['POST'])
def unsubscribe(request):
    if request.method == 'POST':
        email_address = request.data.get('email')
        try:
            user = CustomUser.objects.get(email=email_address)
            user.event_emails = False
            user.save()
            return Response({'status': 'Unsubscribed successfully'})
        except CustomUser.DoesNotExist:
            return Response({'error': 'Email address not found'}, status=400)
    else:
        return Response({'error': 'Invalid request'}, status=400)

# aws endpoints
# sns topic notification endpoint 
@csrf_exempt
@api_view(['POST'])
def sns_endpoint(request):
    if request.method == 'POST':
        message = json.loads(request.body)
        if message['Type'] == 'Notification':
            notification = json.loads(message['Message'])
            if notification['notificationType'] == 'Bounce':
                bounce = notification['bounce']
                for recipient in bounce['bouncedRecipients']:
                    email_address = recipient['emailAddress']
                    # Check if the bounce is permanent
                    if bounce['bounceType'] == 'Permanent':
                        # Add the email to your bounce table
                        BouncedComplaintEmail.objects.get_or_create(email=email_address, reason="email bounced permanently")
                        # Look up the user and tag them
                        try:
                            user = CustomUser.objects.get(email=email_address)
                            user.email_banned = True
                            user.email_ban_amount = 3
                            user.save()
                        except CustomUser.DoesNotExist:
                            pass
                    else:
                        # Add the email to your bounce table
                        BouncedComplaintEmail.objects.get_or_create(email=email_address, reason="email soft bounced, there might be an issues with the your email address or mail server. these issues can include a full mailbox or a temporarily unavailable server") # the user can appeal to get thier email unbanned 
                        try:
                            user = CustomUser.objects.get(email=email_address)
                            user.email_banned = True
                            user.email_ban_amount = user.email_ban_amount + 1
                            user.save()
                        except CustomUser.DoesNotExist:
                            pass
            elif notification['notificationType'] == 'Complaint':
                complaint = notification['complaint']
                for recipient in complaint['complainedRecipients']:
                    email_address = recipient['emailAddress']
                    # Handle complaints here
                    BouncedComplaintEmail.objects.get_or_create(email=email_address, reason='you marked one of our emails as spam. we respect our customers, so we will refrain from sending you any emails here on out') # the user can appeal to get thier email unbanned 
                    try:
                        user = CustomUser.objects.get(email=email_address)
                        user.email_banned = True
                        user.email_ban_amount = user.email_ban_amount + 1
                        user.save()
                    except CustomUser.DoesNotExist:
                        pass
            elif notification['notificationType'] == 'Delivery':
                pass
        return Response({'status':'OK'})
    else:
        return Response({'status':'Invalid request'})
    
# user profile pictures upload 
# views.py
@api_view(['PATCH'])
@parser_classes([MultiPartParser, FormParser])
@token_required
def update_profile_picture(request):
    profile_picture = request.FILES.get('profile_picture', None)
    if profile_picture:
        user = CustomUser.objects.get(email=request.user.email)  # get the current user
        user.profile_picture.delete()  # delete the old profile picture if it exists
        user.profile_picture.save(profile_picture.name, profile_picture)  # save the new profile picture
        user.save()
        return Response({"message" : "picture updated successfully.",})
    else:
        return Response({"error" : "No file was uploaded."}, status=400)

