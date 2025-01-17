# python 
import time

# settings
from django.conf import settings

# simple jwt
from rest_framework_simplejwt.tokens import AccessToken as decode, TokenError
from rest_framework import status
from rest_framework.response import Response
from rest_framework.decorators import api_view

# django
from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.contrib.auth import authenticate as authenticate_user, password_validation
from django.contrib.auth.password_validation import validate_password
from django.core.cache import cache
from django.core.validators import validate_email

# models
from accounts.models import BaseAccount
from account_access_tokens.models import AccountAccessToken
from account_browsers.models import AccountBrowsers

# serializers
from accounts.serializers import general_serializers

# utility functions 
from authentication import utils as authentication_utilities
from account_access_tokens.utils import manage_user_sessions
from account_browsers.utils import generate_device_details

# custom decorators
from .decorators import token_required


# authenticate session

@api_view(["GET"])
@token_required
def authenticate(request):
    try:
        # Access control based on user role and school compliance
        compliant = authentication_utilities.accounts_access_control(request.user)
        if compliant:
            return compliant

        return Response({"role" : request.user.role}, status=status.HTTP_200_OK)
    
    except BaseAccount.DoesNotExist:
        # Handle the case where the provided email does not exist
        return Response(
            {'error': 'Could not process your request, an account with the provided credentials does not exist. Please check the account details and try again.'}, 
            status=status.HTTP_404_NOT_FOUND
        )

    except Exception as e:
        # if any exceptions rise during return the response return it as the response
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# activate account

@api_view(['POST'])
def account_activation_credentials_verification(request):
    try:
        first_name = request.data.get('first_name')
        last_name = request.data.get('last_name')
        email_address = request.data.get('email_address')

        # if there's a missing credential return an error
        if not first_name:
            return Response(
                {"error": "Could not process your request, the provided account activation credentials are incomplete. Please provide your first name and try again."}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        # if there's a missing credential return an error
        if not last_name:
            return Response(
                {"error": "Could not process your request, the provided account activation credentials are incomplete. Please provide your last name and try again."}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        # if there's a missing credential return an error
        if not email_address:
            return Response(
                {"error": "Could not process your request, the provided account activation credentials are incomplete. Please provide your email address and try again."}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        # print('validating email address')
        # validate email format
        validate_email(email_address)
        # print('email address validated')


        # print('requesting user')
        # try to validate the credentials by getting a user with the provided credentials 
        requesting_user = BaseAccount.objects.get(email_address=email_address)
        # print('user requested')

        if not (requesting_user.name.casefold() == first_name.casefold() and requesting_user.surname.casefold() == last_name.casefold()):
            return Response(
                {"error": "Could not process your request, the account activation credentials you provided are invalid. Please check your first name, last name and email address and try again."}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # print('checking user compliant')
        # Access control based on user role and school compliance
        compliant = authentication_utilities.accounts_access_control(requesting_user)
        if compliant:
            return compliant
        # print('check complete')

        # if there is a user with the provided credentials check if their account has already been activated 
        if requesting_user.activated:
            return Response(
                {"error": "Could not process your request, access has been denied due to invalid or incomplete information."}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        # if the users account has'nt been activated yet check if their email address is banned
        if requesting_user.email_banned:
            # if their email address is banned return an error and let the user know and how they can appeal( if they even can )
            response = Response(
                {"alert" : "Could not fully process your login request, your email address has been blacklisted. Our system has flagged your email address and banned it from recieving emails from us."}, 
                status=status.HTTP_403_FORBIDDEN
            )

            authentication_utilities.set_cookie(
                response, 
                'banned_email_address_role', 
                requesting_user.role, 
                httponly=False, 
            )

            return response
    
        # print('genrating otp')
        # create an otp for the user
        account_activation_otp, hashed_account_activation_otp, account_activation_salt = authentication_utilities.generate_otp()
        # print('otp genrated')

        # print('sending otp email')
        email_response = authentication_utilities.send_otp_email(
            requesting_user, 
            account_activation_otp, 
            reason="We're thrilled to have you on board and excited for you to explore all we have to offer. Here's your one-time passcode (OTP), freshly baked just for your account activation request. Use it to unlock the door to your new adventure with us—let's get started!"
        )

        if email_response['status'] == 'success':
            # print('email sent')
            cache.set( # Cache OTP for 5 mins
                email_address + 'multi_factor_authentication_account_activation_otp_hash_and_salt', 
                (hashed_account_activation_otp, account_activation_salt), 
                timeout=300
            ) 

            response = Response(
                {"message": "A account activation OTP has been generated for your account and sent to your email address. It will be valid for the next 5 minutes.",}, 
                status=status.HTTP_200_OK
            )

            account_activation_authorization_otp = authentication_utilities.generate_and_cache_otp(
                email_address + 'multi_factor_authentication_account_activation_authorization_otp_hash_and_salt'
            )
            authentication_utilities.set_cookie(
                response, 
                'multi_factor_authentication_account_activation_authorization_otp', 
                account_activation_authorization_otp, 
            )
            authentication_utilities.set_cookie(
                response, 
                'multi_factor_authentication_account_activation_email_address', 
                email_address, 
            )
            authentication_utilities.set_cookie(
                response, 
                'request_authorized_for_multi_factor_authentication_account_activation', 
                True, 
                httponly=False, 
            )

            return response

        return Response(
            {"error": email_response['message']}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    
    except BaseAccount.DoesNotExist:
        # if there's no user with the provided credentials return an error 
        return Response(
            {"error": "Could not process your request, the credentials you entered are invalid. Please check your full name and email address and try again"}, 
            status=status.HTTP_404_NOT_FOUND
        )
    
    except ValidationError:
        return Response(
            {"error": "Could not process your request, the provided email address is not in a valid format. Please correct the email address and try again"}, 
            status=status.HTTP_400_BAD_REQUEST
        )

    except Exception as e:
        return Response(
            {"error": str(e)}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['POST'])
def account_activation_otp_verification(request):
    try:
        email_address = request.COOKIES.get('multi_factor_authentication_account_activation_email_address')
        authorization_otp = request.COOKIES.get('multi_factor_authentication_account_activation_authorization_otp')

        if not (email_address or authorization_otp):
            return Response(
                {"denied": "Could not process your request, your request is missing required authentication credentials to process this request."}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        requesting_user = BaseAccount.objects.get(email_address=email_address)
        
        # Access control based on user role and school compliance
        compliant = authentication_utilities.accounts_access_control(requesting_user)
        if compliant:
            return compliant

        stored_hashed_account_activation_otp_and_salt = cache.get(email_address + 'multi_factor_authentication_account_activation_otp_hash_and_salt')
        
        # try to get the the authorization otp from cache
        stored_hashed_account_activation_authorization_otp_and_salt = cache.get(email_address + 'multi_factor_authentication_account_activation_authorization_otp_hash_and_salt')
        
        if not (stored_hashed_account_activation_authorization_otp_and_salt or stored_hashed_account_activation_otp_and_salt):
            # if there's no authorization otp in cache( wasn't provided in the first place, or expired since it also has a 5 minute lifespan )
            return Response(
                {"denied": "Could not process your request, your accounts multi-factor authentication login One Time Passcode has expired. To generate a new one you will have to re-authenticate from the login page."}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        account_activation_otp = request.data.get('account_activation_otp')
        if not account_activation_otp:
            return Response(
                {"error": "Could not process your request, your request is missing important authorization credentials needed to process this request. Please provide your account activation One Time Passcode then try again."}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        # if everything above checks out verify the provided otp against the stored otp
        if authentication_utilities.verify_user_otp(
            account_otp=account_activation_otp, 
            stored_hashed_otp_and_salt=stored_hashed_account_activation_otp_and_salt
        ):
            # provided otp is verified successfully
            if authentication_utilities.verify_user_otp(
                account_otp=authorization_otp, 
                stored_hashed_otp_and_salt=stored_hashed_account_activation_authorization_otp_and_salt
            ):

                activate_account_authorization_otp, hashed_activate_account_authorization_otp, activate_account_salt = authentication_utilities.generate_otp()

                cache.set( # 300 seconds = 5 mins
                    email_address + 'activate_account_authorization_otp_hash_and_salt', 
                    (hashed_activate_account_authorization_otp, activate_account_salt), 
                    timeout= 60 * 60 * 24
                ) 
                
                response = Response(
                    {"message": "Your account activation One Time Passcode has been successfully verified, you can create a new password for your account on the next page to fully activate it."}, 
                    status=status.HTTP_200_OK
                )

                authentication_utilities.set_cookie(
                    response, 
                    'activate_account_authorization_otp', 
                    activate_account_authorization_otp, 
                    max_age= 60 * 60 * 24
                )
                authentication_utilities.set_cookie(
                    response, 
                    'activate_account_email_address', 
                    email_address, 
                    max_age= 60 * 60 * 24
                )
                authentication_utilities.set_cookie(
                    response, 
                    'request_authorized_for_account_activation', 
                    True, 
                    httponly=False, 
                    max_age= 60 * 60 * 24
                )

                response.delete_cookie('multi_factor_authentication_account_activation_email_address', domain=settings.SESSION_COOKIE_DOMAIN)
                response.delete_cookie('multi_factor_authentication_account_activation_authorization_otp', domain=settings.SESSION_COOKIE_DOMAIN)

                # OTP is verified, prompt the user to set their password
                cache.delete(email_address + 'multi_factor_authentication_account_activation_otp_hash_and_salt')
                cache.delete(email_address + 'multi_factor_authentication_account_activation_authorization_otp_hash_and_salt')
                cache.delete(email_address + 'account_activation_otp_failed_attempts')
            
                return response
                        
            # if there's no error till here verification is successful, delete all cached otps
            cache.delete(email_address + 'multi_factor_authentication_account_activation_otp_hash_and_salt')
            cache.delete(email_address + 'multi_factor_authentication_account_activation_authorization_otp_hash_and_salt')
            cache.delete(email_address + 'account_activation_otp_failed_attempts')
            
            # if the authorization otp does'nt match the one stored for the user return an error 
            response = Response({"denied": "Could not process your request, incorrect authorization OTP. Action forrbiden."}, status=status.HTTP_400_BAD_REQUEST)

            response.delete_cookie('multi_factor_authentication_account_activation_email_address', domain=settings.SESSION_COOKIE_DOMAIN)
            response.delete_cookie('multi_factor_authentication_account_activation_authorization_otp', domain=settings.SESSION_COOKIE_DOMAIN)
            return response

        attempts = cache.get(email_address + 'account_activation_otp_failed_attempts', 3)
        
        if attempts > 0:
            # Incorrect OTP, decrement attempts and handle expiration
            attempts -= 1
            cache.set(email_address + 'account_activation_otp_failed_attempts', attempts, timeout=300)  # Update attempts with expiration

            return Response(
                {"error": f"Could not process your request, the provided account activation One Time Passcode is incorrect. You have {attempts} {'attempts' if attempts > 1 else 'attempt'} remaining."}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        cache.delete(email_address + 'multi_factor_authentication_account_activation_otp_hash_and_salt')
        cache.delete(email_address + 'multi_factor_authentication_account_activation_authorization_otp_hash_and_salt')
        cache.delete(email_address + 'account_activation_otp_failed_attempts')

        response = Response(
            {"denied": "Could not process your request, you have exceeded the maximum number of One Time Passcode verification attempts. Generated account activation One Time Passcode for your account has been discarded."}, 
            status=status.HTTP_403_FORBIDDEN
        )
        
        response.delete_cookie('multi_factor_authentication_account_activation_email_address', domain=settings.SESSION_COOKIE_DOMAIN)
        response.delete_cookie('multi_factor_authentication_account_activation_authorization_otp', domain=settings.SESSION_COOKIE_DOMAIN)
        return response

    except BaseAccount.DoesNotExist:
        # if there's no user with the provided credentials return an error 
        return Response(
            {"error": "Could not process your request, the credentials you entered are invalid. Please check your full name and email address and try again"}, 
            status=status.HTTP_404_NOT_FOUND
        )

    except Exception as e:
        return Response(
            {"error": str(e)}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
def activate_account(request):
    try:
        email_address = request.COOKIES.get('activate_account_email_address')
        authorization_otp = request.COOKIES.get('activate_account_authorization_otp')

        if not (email_address or authorization_otp):
            return Response(
                {"denied": "Could not process your request, your request is missing required authentication credentials to process this request."}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        # get authorization otp 
        stored_activate_account_hashed_otp_and_salt = cache.get(email_address + 'activate_account_authorization_otp_hash_and_salt')

        if not stored_activate_account_hashed_otp_and_salt:
            response = Response(
                {"denied": "Could not process your request, there is no account activation authorization One Time Passcode for your account on record. Your request can therefore not be authorized, returning you back to the account activation page shortly."}, 
                status=status.HTTP_400_BAD_REQUEST
            )
            
            response.delete_cookie('activate_account_email_address', domain=settings.SESSION_COOKIE_DOMAIN)
            response.delete_cookie('activate_account_authorization_otp', domain=settings.SESSION_COOKIE_DOMAIN)
            response.delete_cookie('request_authorized_for_account_activation', domain=settings.SESSION_COOKIE_DOMAIN)
            return response

        if authentication_utilities.verify_user_otp(account_otp=authorization_otp, stored_hashed_otp_and_salt=stored_activate_account_hashed_otp_and_salt):
            password = request.data.get('password')
            if not password:
                return Response(
                    {"error": "Could not process your request, your request is missing important credentials. Make sure to privide your password then try again."}, 
                    status=status.HTTP_400_BAD_REQUEST
                ) 

            public_key = request.data.get('publicKey')
            static_key = request.data.get('staticKey')

            password_encrypted_private_key = request.data.get('passwordEncryptedPrivateKey')
            password_encrypted_private_key_salt = request.data.get('passwordEncryptedPrivateKeySalt')
            password_encryption_iv = request.data.get('passwordEncryptioniv')

            recovery_Key_encrypted_private_key = request.data.get('recoveryKeyEncryptedPrivateKey')
            recovery_key_encrypted_private_key_salt = request.data.get('recoveryKeyEncryptedPrivateKeySalt')
            recovery_key_encryption_iv = request.data.get('recoveryKeyEncryptioniv')

            # Validate required fields
            if not all([
                public_key,
                static_key,

                password_encrypted_private_key, 
                password_encrypted_private_key_salt, 
                password_encryption_iv,

                recovery_Key_encrypted_private_key, 
                recovery_key_encrypted_private_key_salt, 
                recovery_key_encryption_iv,
            ]):
                return Response(
                    {"error": "Could not process your request, request is missing required data to process account activation."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # activate users account
            with transaction.atomic():
                account = BaseAccount.objects.get(email_address=email_address)

                # Access control based on user role and school compliance
                compliant = authentication_utilities.accounts_access_control(account)
                if compliant:
                    return compliant
                
                BaseAccount.objects.activate_account(email_address=email_address, password=password)

                # Save the cryptographic fields
                account.public_key = public_key

                account.password_encrypted_private_key = password_encrypted_private_key
                account.password_encrypted_private_key_salt = password_encrypted_private_key_salt
                account.password_encryption_iv = password_encryption_iv

                account.recovery_Key_encrypted_private_key = recovery_Key_encrypted_private_key
                account.recovery_encrypted_private_key_salt = recovery_key_encrypted_private_key_salt
                account.recovery_encryption_iv = recovery_key_encryption_iv

                account.save()

                # generate an access and refresh token for the user 
                token = authentication_utilities.generate_token(account=account)
                access_token = AccountAccessToken.objects.create(account=account, access_token_string=token['access'])

                # Now update the account browsers with the current device info
                browser_info = generate_device_details(request)
                browser = AccountBrowsers.objects.create(
                    account=account,
                    access_token=access_token,
                    static_key=static_key,
                    device_type=browser_info['device_type'],
                    os=browser_info['os'],
                    os_version=browser_info['os_version'],
                    browser=browser_info['browser'],
                    browser_version=browser_info['browser_version'],
                    language=browser_info['language'],
                    time_zone=browser_info['time_zone'],
                    created_at=timezone.now(),
                )

            cache.delete(email_address + 'activate_account_authorization_otp_hash_and_salt')

            account_details = general_serializers.BasicAccountDetailsSerializer(account)

            response = Response(
                {
                    "message": "Congratulations! You have successully activated your account. Welcome to seeran grades.", 
                    "account": account_details
                }, 
                status=status.HTTP_200_OK
            )

            response.delete_cookie('activate_account_email_address', domain=settings.SESSION_COOKIE_DOMAIN)
            response.delete_cookie('activate_account_authorization_otp', domain=settings.SESSION_COOKIE_DOMAIN)
            response.delete_cookie('request_authorized_for_account_activation', domain=settings.SESSION_COOKIE_DOMAIN)

            # Set access token cookie with custom expiration (24 hours)
            authentication_utilities.set_cookie(
                response, 
                'access_token', 
                token['access'], 
                max_age=86400
            )
            authentication_utilities.set_cookie(
                response, 
                'browser_id', 
                browser.browser_id, 
                max_age= 60 * 60 * 24 * 30 # the browser will be identified for 30 days as long as the user keeps using the browser
            )
            authentication_utilities.set_cookie(
                response, 
                'session_authenticated', 
                'This session is valid and active.', 
                httponly=False, 
                max_age=86400
            )

            return response

        response = Response(
            {"denied": "Could not process your request, your requests authorization One Time Passcode is invalid. Request forrbiden."}, 
            status=status.HTTP_403_FORBIDDEN
        )

        cache.delete(email_address + 'activate_account_authorization_otp_hash_and_salt')

        response.delete_cookie('activate_account_email_address', domain=settings.SESSION_COOKIE_DOMAIN)
        response.delete_cookie('activate_account_authorization_otp', domain=settings.SESSION_COOKIE_DOMAIN)
        response.delete_cookie('request_authorized_for_account_activation', domain=settings.SESSION_COOKIE_DOMAIN)
        return response

    except BaseAccount.DoesNotExist:
        # if theres no user with the provided email return an error
        return Response(
            {"denied": "Could not process your request, an account with the provided credentials does not exist. Please check the account details and try again."}, 
            status=status.HTTP_404_NOT_FOUND
        )
  
    except Exception as e:
        # if any exceptions rise during return the response return it as the response
        return Response(
            {"error": str(e)}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

# login

@api_view(['POST'])
def login(request):
    try:
        email_address = request.data.get('email_address')
        password = request.data.get('password')
        
        # Verify user credentials
        requesting_user = authenticate_user(email_address=email_address, password=password)
        if requesting_user is None:
            return Response(
                {"error": "Could not process your request, the provided credentials are invalid. Please check your email address and password and try again."}, 
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        # Access control based on user role and school compliance
        compliant = authentication_utilities.accounts_access_control(requesting_user)
        if compliant:
            return compliant
            
        # generate an access token for the user 
        token = authentication_utilities.generate_token(requesting_user)

        # Handle multi-factor authentication (MFA) if enabled for the user
        if requesting_user.multifactor_authentication:
            # Disable MFA if email is banned (for security reasons)
            if requesting_user.email_banned:
                requesting_user.multifactor_authentication = False
                requesting_user.save()
                
                # Clear old access tokens if any, to limit active sessions
                if 'access' in token:
                    session_response = manage_user_sessions(requesting_user, token)
                    if session_response:  # If the function returns a response, it indicates an error
                        return session_response

                    # Set access token cookie with custom expiration (24 hours)
                    response = Response(
                        {"alert" : "Could not fully process your login request, your email address has been blacklisted. Our system has flagged your email address and banned it from recieving emails from us."}, 
                        status=status.HTTP_403_FORBIDDEN 
                    )

                    authentication_utilities.set_cookie(
                        response, 
                        'access_token', 
                        token['access'], 
                        max_age=86400
                    )
                    authentication_utilities.set_cookie(
                        response, 
                        'session_authenticated', 
                        'This session is valid and active.', 
                        httponly=False, 
                        max_age=86400
                    )
                    authentication_utilities.set_cookie(
                        response, 
                        'banned_email_address_role', 
                        requesting_user.role, 
                        httponly=False, 
                    )

                    return response
                
                return Response(
                    {"error": "Could not process your request, server error. Could not generate access token for your account"}, 
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
            
            # Generate OTP and send to user's email for MFA
            multi_factor_authentication_login_otp, multi_factor_authentication_hashed_otp, multi_factor_authentication_salt = authentication_utilities.generate_otp()
            email_response = authentication_utilities.send_otp_email(
                requesting_user, 
                multi_factor_authentication_login_otp, 
                reason="Your account has multi-factor authentication toggled on, this One Time Passcode was generated in response to your login request."
            )

            if email_response['status'] == 'success':
                cache.set( # Cache OTP for 5 mins
                    email_address + 'multi_factor_authentication_login_otp_hash_and_salt', 
                    (multi_factor_authentication_hashed_otp, multi_factor_authentication_salt), 
                    timeout=300
                ) 

                response = Response(
                    {"multifactor_authentication": "You have successufully authenticated using your email address and password, a new login One Time Passcode has been sent to your email address. Please check your inbox for the email."}, 
                    status=status.HTTP_200_OK
                )
                
                multi_factor_authentication_authorization_otp = authentication_utilities.generate_and_cache_otp(
                    email_address + 'multi_factor_authentication_login_authorization_otp'
                )
                authentication_utilities.set_cookie(
                    response, 
                    'multi_factor_authentication_login_authorization_otp', 
                    multi_factor_authentication_authorization_otp, 
                )
                authentication_utilities.set_cookie(
                    response, 
                    'multi_factor_authentication_login_account_email_address', 
                    email_address, 
                )
                authentication_utilities.set_cookie(
                    response, 
                    'request_authorized_for_multi_factor_authentication_login', 
                    True, 
                    httponly=False
                )

                return response
            
            return Response({"error": email_response['message']}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Handle login without MFA
        if 'access' in token:
            session_response = manage_user_sessions(requesting_user, token)
            if session_response:  # If the function returns a response, it indicates an error
                return session_response
            
            response = Response(
                {"message": "You will have access to your dashboard for the next 24 hours, until your session ends.", "role" : requesting_user.role}, 
                status=status.HTTP_200_OK
            )
        
            # Set access token cookie with custom expiration (24 hours)
            authentication_utilities.set_cookie(
                response, 
                'access_token', 
                token['access'], 
                max_age=86400
            )
            authentication_utilities.set_cookie(
                response, 
                'session_authenticated', 
                'This session is valid and active.', 
                httponly=False, 
                max_age=86400
            )

            return response
       
        return Response(
            {"error": "Could not process your request, server error. Could not generate access token for your account, please try again in a moment."}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    
    except BaseAccount.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return Response(
            {"error": "Could not process your request, the credentials you entered are invalid. Please check your email and password and try again"}, 
            status=status.HTTP_404_NOT_FOUND
        )
    
    except Exception as e:
        return Response(
            {"error": str(e)}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['POST'])
def multi_factor_authentication_login(request):
    try:
        # retrieve the provided email, otp and the authorization otp in the cookie
        multi_factor_authentication_login_otp = request.data.get('multi_factor_authentication_login_otp')
        authorization_otp = request.COOKIES.get('multi_factor_authentication_login_authorization_otp')
        
        # if anyone of these is missing return a 400 error
        if not (email_address or multi_factor_authentication_login_otp or authorization_otp):
            return Response(
                {"denied": "Could not process your request, your request is missing required authentication credentials to process this request."}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        requesting_user = BaseAccount.objects.get(email_address=email_address)
        
        # Access control based on user role and school compliance
        compliant = authentication_utilities.accounts_access_control(requesting_user)
        if compliant:
            return compliant

        # after getting the user object retrieve the stored otp from cache 
        stored_hashed_otp_and_salt = cache.get(email_address + 'multi_factor_authentication_login_otp_hash_and_salt')
        
        # try to get the the authorization otp from cache
        hashed_authorization_otp_and_salt = cache.get(email_address + 'multi_factor_authentication_login_authorization_otp')
        
        if not (hashed_authorization_otp_and_salt or stored_hashed_otp_and_salt):
            # if there's no authorization otp in cache( wasn't provided in the first place, or expired since it also has a 5 minute lifespan )
            return Response(
                {"denied": "Could not process your request, your accounts multi-factor authentication login One Time Passcode has expired. To generate a new one you will have to re-authenticate from the login page."}, 
                status=status.HTTP_400_BAD_REQUEST
            )
    
        # if everything above checks out verify the provided otp against the stored otp
        if authentication_utilities.verify_user_otp(account_otp=multi_factor_authentication_login_otp, stored_hashed_otp_and_salt=stored_hashed_otp_and_salt):
            # provided otp is verified successfully
            if authentication_utilities.verify_user_otp(account_otp=authorization_otp, stored_hashed_otp_and_salt=hashed_authorization_otp_and_salt):
                email_address = request.COOKIES.get('multi_factor_authentication_login_account_email_address') 
                # if anyone of these is missing return a 400 error
                if not (email_address or multi_factor_authentication_login_otp or authorization_otp):
                    return Response(
                        {"denied": "Could not process your request, your request is missing required information. Request does not provide the accounts email address required to generate access credentials for your account."}, 
                        status=status.HTTP_400_BAD_REQUEST
                    )

                # if there's no error till here verification is successful, delete all cached otps
                cache.delete(email_address + 'multi_factor_authentication_login_otp_hash_and_salt')
                cache.delete(email_address + 'multi_factor_authentication_login_failed_otp_attempts')
                
                # then generate an access and refresh token for the user 
                token = authentication_utilities.generate_token(requesting_user)
                
                if 'access' in token:
                    session_response = manage_user_sessions(requesting_user, token)
                    if session_response:  # If the function returns a response, it indicates an error
                        return session_response
                    
                    # set access token cookie with custom expiration (5 mins)
                    response = Response(
                        {"message": "You will have access to your dashboard for the next 24 hours, until your session ends.", "role" : requesting_user.role}, 
                        status=status.HTTP_200_OK
                    )

                    authentication_utilities.set_cookie(
                        response, 
                        'access_token', 
                        token['access'], 
                        max_age=86400
                    )
                    authentication_utilities.set_cookie(
                        response, 
                        'session_authenticated', 
                        'This session is valid and active.', 
                        httponly=False, 
                        max_age=86400
                    )

                    cache.delete(requesting_user.email_address + 'multi_factor_authentication_login_otp_hash_and_salt')
                    cache.delete(requesting_user.email_address + 'multi_factor_authentication_login_authorization_otp')
                    cache.delete(email_address + 'multi_factor_authentication_login_failed_otp_attempts')

                    response.delete_cookie('multi_factor_authentication_login_authorization_otp', domain=settings.SESSION_COOKIE_DOMAIN)
                    response.delete_cookie('multi_factor_authentication_login_account_email_address', domain=settings.SESSION_COOKIE_DOMAIN)
                    response.delete_cookie('request_authorized_for_multi_factor_authentication_login', domain=settings.SESSION_COOKIE_DOMAIN)

                    return response
                
                return Response(
                    {"error": "Could not process your request, the server could not generate an access token for your account. Please try again in a moment"}, 
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
            
            # if the authorization otp does'nt match the one stored for the user return an error 
            response = Response(
                {"denied": "Could not process your request, incorrect authorization OTP. Action forrbiden"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
                        
            # if there's no error till here verification is successful, delete all cached otps
            cache.delete(requesting_user.email_address + 'multi_factor_authentication_login_otp_hash_and_salt')
            cache.delete(requesting_user.email_address + 'multi_factor_authentication_login_authorization_otp')
            cache.delete(email_address + 'multi_factor_authentication_login_failed_otp_attempts')

            response.delete_cookie('multi_factor_authentication_login_authorization_otp', domain=settings.SESSION_COOKIE_DOMAIN)
            response.delete_cookie('multi_factor_authentication_login_account_email_address', domain=settings.SESSION_COOKIE_DOMAIN)
            response.delete_cookie('request_authorized_for_multi_factor_authentication_login', domain=settings.SESSION_COOKIE_DOMAIN)
            return response

        attempts = cache.get(email_address + 'multi_factor_authentication_login_failed_otp_attempts', 3)
        
        if attempts <= 0:
            response = Response(
                {"denied": "Could not process your request, you have exceeded the maximum One Time Passcode verification attempts. Returning you to the login page shortly."}, 
                status=status.HTTP_400_BAD_REQUEST
            )

            cache.delete(requesting_user.email_address + 'multi_factor_authentication_login_otp_hash_and_salt')
            cache.delete(requesting_user.email_address + 'multi_factor_authentication_login_authorization_otp')
            cache.delete(email_address + 'multi_factor_authentication_login_failed_otp_attempts')

            response.delete_cookie('multi_factor_authentication_login_authorization_otp', domain=settings.SESSION_COOKIE_DOMAIN)
            response.delete_cookie('multi_factor_authentication_login_account_email_address', domain=settings.SESSION_COOKIE_DOMAIN)
            response.delete_cookie('request_authorized_for_multi_factor_authentication_login', domain=settings.SESSION_COOKIE_DOMAIN)

            return response
        
        # Incorrect OTP, decrement attempts and handle expiration
        attempts -= 1
        cache.set(email_address + 'multi_factor_authentication_login_failed_otp_attempts', attempts, timeout=300)  # Update attempts with expiration

        return Response(
            {"error": f"Could not process your request, incorrect One Time Passcode.. {attempts} remaining"}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    except BaseAccount.DoesNotExist:
        # Handle the case where the provided email does not exist
        return Response(
            {'error': 'Could not process your request, an account with the provided credentials does not exist. Please check the account details and try again.'}, 
            status=status.HTTP_404_NOT_FOUND
        )

    except Exception as e:
        # if any exceptions rise during return the response return it as the response
        return Response(
            {"error": str(e)}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# reset password

@api_view(['POST'])
def credentials_reset_email_verification(request):
    try:
        # check for sent email
        email_address = request.data.get('email_address')
        if not email_address:
            return Response(
                {"error": "Could not process your request, no email address provided. Email address is required."}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        # validate email format
        validate_email(email_address)

        # try to get the user with the provided email
        requesting_user = BaseAccount.objects.get(email_address=email_address)

        # Access control based on user role and school compliance
        compliant = authentication_utilities.accounts_access_control(requesting_user)
        if compliant:
            return compliant

        # check if the account is activated 
        if requesting_user.activated == False:
            return Response(
                {"error": "Could not process your request, action forbidden for account with the provided credentials."}, 
                status=status.HTTP_403_FORBIDDEN
            )

        # check if the email is banned 
        if requesting_user.email_banned:
            return Response(
                { "error" : "Could not process your request, failed to send One Time Passcode email, your email address has been banned. You can contact your school administrators for assistance or to have it updated."}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        # if everything checks out without an error 
        # create an otp for the user
        password_reset_otp, hashed_password_reset_otp, password_reset_salt = authentication_utilities.generate_otp()
        email_response = authentication_utilities.send_otp_email(
            requesting_user, 
            password_reset_otp, 
            reason="We recieved a password reset request, looks like you're ready for a fresh start, we've got you covered! Use the One Time Passcode below to securely reset your password."
        )

        if email_response['status'] == 'success':
            cache.set(email_address + 'multi_factor_authentication_password_reset_otp_hash_and_salt', (hashed_password_reset_otp, password_reset_salt), timeout=300)  # Cache OTP for 5 mins

            response = Response(
                {"message": "A password reset One Time Password has been generated and sent to your email address. If you do not see the email check your spam/junk folder.",}, 
                status=status.HTTP_200_OK
            )

            password_reset_authorization_otp = authentication_utilities.generate_and_cache_otp(
                email_address + 'multi_factor_authentication_password_reset_authorization_otp_hash_and_salt'
            )
            authentication_utilities.set_cookie(
                response, 
                'multi_factor_authentication_password_reset_authorization_otp', 
                password_reset_authorization_otp, 
            )
            authentication_utilities.set_cookie(
                response, 
                'multi_factor_authentication_password_reset_account_email_address', 
                email_address, 
            )
            authentication_utilities.set_cookie(
                response, 
                'request_authorized_for_multi_factor_authentication_password_reset', 
                True, 
                httponly=False, 
            )

            return response

        return Response(
            {"error": email_response['message']}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    
    except BaseAccount.DoesNotExist:
        # if theres no user with the provided email return an error
        return Response(
            {"error": "Could not process your request, an account with the provided credentials does not exist. Please check the account details and try again"}, 
            status=status.HTTP_404_NOT_FOUND
        )
            
    except ValidationError:
        return Response(
            {"error": "Could not process your request, the provided email address is not in a valid format. Please correct the email address and try again"}, 
            status=status.HTTP_400_BAD_REQUEST
        )

    except Exception as e:
        return Response(
            {"error": str(e)}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['POST'])
def credentials_reset_otp_verification(request):
    try:
        email_address = request.COOKIES.get('multi_factor_authentication_password_reset_account_email_address')
        password_reset_authorization_otp = request.COOKIES.get('multi_factor_authentication_password_reset_authorization_otp')

        if not (email_address or password_reset_authorization_otp):
            return Response(
                {"denied": "Could not process your request, your request is missing required authentication credentials to process this request."}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        requesting_user = BaseAccount.objects.get(email_address=email_address)

        # Access control based on user role and school compliance
        compliant = authentication_utilities.accounts_access_control(requesting_user)
        if compliant:
            return compliant

        # after getting the user object retrieve the stored otp from cache 
        stored_hashed_otp_and_salt = cache.get(email_address + 'multi_factor_authentication_password_reset_otp_hash_and_salt')

        # try to get the the authorization otp from cache
        multi_factor_authentication_password_reset_hashed_authorization_otp_and_salt = cache.get(email_address + 'multi_factor_authentication_password_reset_authorization_otp_hash_and_salt')

        if not (multi_factor_authentication_password_reset_hashed_authorization_otp_and_salt and stored_hashed_otp_and_salt):
            # if there's no authorization otp in cache( wasn't provided in the first place, or expired since it also has a 5 minute lifespan )
            return Response(
                {"denied": "Could not process your request, your accounts multi-factor authentication password reset One Time Password has expired. Returning you to the password reset page shortly."}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        # if everything above checks out verify the provided otp against the stored otp
        if authentication_utilities.verify_user_otp(account_otp=password_reset_otp, stored_hashed_otp_and_salt=stored_hashed_otp_and_salt):
            # provided otp is verified successfully
            if authentication_utilities.verify_user_otp(account_otp=password_reset_authorization_otp, stored_hashed_otp_and_salt=multi_factor_authentication_password_reset_hashed_authorization_otp_and_salt):
                password_reset_otp = request.data.get('password_reset_otp')

                if not password_reset_otp:
                    return Response(
                        {"error": "Could not process your request, the provided information is invalid. Email address and One Time Passcode are required."}, 
                        status=status.HTTP_400_BAD_REQUEST
                    )

                response = Response(
                    {"message": "Password reset one time passcode successfully verified. You will be redirected to the reset password page where you will be able to update your password."}, 
                    status=status.HTTP_200_OK
                )

                password_reset_authorization_otp = authentication_utilities.generate_and_cache_otp(
                    email_address + 'password_reset_hashed_authorization_otp_and_salt'
                )
                authentication_utilities.set_cookie(
                    response, 
                    'password_reset_authorization_otp', 
                    password_reset_authorization_otp, 
                )
                authentication_utilities.set_cookie(
                    response, 
                    'password_reset_email_address', 
                    email_address, 
                )
                authentication_utilities.set_cookie(
                    response, 
                    'request_authorized_to_reset_account_password', 
                    email_address, 
                    httponly=False, 
                )

                cache.delete(email_address + 'multi_factor_authentication_password_reset_otp_hash_and_salt')
                cache.delete(email_address + 'multi_factor_authentication_password_reset_authorization_otp_hash_and_salt')
                cache.delete(email_address + 'multi_factor_authentication_password_reset_failed_otp_attempts')

                response.delete_cookie('multi_factor_authentication_password_reset_authorization_otp', domain=settings.SESSION_COOKIE_DOMAIN)
                response.delete_cookie('multi_factor_authentication_password_reset_account_email_address', domain=settings.SESSION_COOKIE_DOMAIN)
                response.delete_cookie('request_authorized_for_multi_factor_authentication_password_reset', domain=settings.SESSION_COOKIE_DOMAIN)

                return response

            # if the authorization otp does'nt match the one stored for the user return an error 
            response = Response(
                {"denied": "Could not process your request, incorrect authorization One Time Passcode. Action forrbiden."}, 
                status=status.HTTP_400_BAD_REQUEST
            )

            # if there's no error till here verification is successful, delete all cached otps
            cache.delete(email_address + 'multi_factor_authentication_password_reset_otp_hash_and_salt')
            cache.delete(email_address + 'multi_factor_authentication_password_reset_authorization_otp_hash_and_salt')
            cache.delete(email_address + 'multi_factor_authentication_password_reset_failed_otp_attempts')

            response.delete_cookie('multi_factor_authentication_password_reset_authorization_otp', domain=settings.SESSION_COOKIE_DOMAIN)
            response.delete_cookie('multi_factor_authentication_password_reset_account_email_address', domain=settings.SESSION_COOKIE_DOMAIN)
            response.delete_cookie('request_authorized_for_multi_factor_authentication_password_reset', domain=settings.SESSION_COOKIE_DOMAIN)

            return response

        attempts = cache.get(email_address + 'multi_factor_authentication_password_reset_failed_otp_attempts', 3)

        if attempts <= 0:
            cache.delete(email_address + 'multi_factor_authentication_password_reset_otp_hash_and_salt')
            cache.delete(email_address + 'multi_factor_authentication_password_reset_authorization_otp_hash_and_salt')
            cache.delete(email_address + 'multi_factor_authentication_password_reset_failed_otp_attempts')

            response = Response(
                {"denied": "Could not process your request, you have exceeded the maximum number of One Time Passcode verification attempts."}, 
                status=status.HTTP_400_BAD_REQUEST
            )

            response.delete_cookie('multi_factor_authentication_password_reset_authorization_otp', domain=settings.SESSION_COOKIE_DOMAIN)
            response.delete_cookie('multi_factor_authentication_password_reset_account_email_address', domain=settings.SESSION_COOKIE_DOMAIN)
            response.delete_cookie('request_authorized_for_multi_factor_authentication_password_reset', domain=settings.SESSION_COOKIE_DOMAIN)

            return response

        # Incorrect OTP, decrement attempts and handle expiration
        attempts -= 1
        cache.set(email_address + 'multi_factor_authentication_password_reset_failed_otp_attempts', attempts, timeout=300)  # Update attempts with expiration

        return Response(
            {"error": f"Could not process your request, he provided password reset One Time Passcode is incorrect. You have {attempts} {'attempts' if attempts > 1 else 'attempt'} remaining."}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    except BaseAccount.DoesNotExist:
        # if theres no user with the provided email return an error
        return Response(
            {"error": "Could not process your request, an account with the provided credentials does not exist. Please check the account details and try again"}, 
            status=status.HTTP_404_NOT_FOUND
        )

    except Exception as e:
        # if any exceptions rise during return the response return it as the response
        return Response(
            {"error": str(e)}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
 
@api_view(['POST'])
def reset_credentials(request):
    try:
        # Get the new password and confirm password from the request data, and authorization otp from the cookies
        email_address = request.COOKIES.get('password_reset_email_address')
        password_reset_otp = request.COOKIES.get('password_reset_authorization_otp')
        
        if not (email_address or password_reset_otp):
            return Response(
                {"denied": "Could not process your request, your request is missing required authentication credentials to process this request."}, 
                status=status.HTTP_400_BAD_REQUEST
            )    
    
        requesting_user = BaseAccount.objects.get(email_address=email_address)
        
        # Access control based on user role and school compliance
        compliant = authentication_utilities.accounts_access_control(requesting_user)
        if compliant:
            return compliant
        
        # get authorization otp from cache and verify provided otp
        hashed_authorization_otp_and_salt = cache.get(email_address + 'password_reset_hashed_authorization_otp_and_salt')
        if not hashed_authorization_otp_and_salt:
            response = Response(
                {"denied": "Could not process your request, there is no password reset authorization One Time Passcode for your account on record. Process forrbiden."}, 
                status=status.HTTP_403_FORBIDDEN
            )

            response.delete_cookie('password_reset_email_address', domain=settings.SESSION_COOKIE_DOMAIN)
            response.delete_cookie('password_reset_authorization_otp', domain=settings.SESSION_COOKIE_DOMAIN)
            response.delete_cookie('request_authorized_to_reset_account_password', domain=settings.SESSION_COOKIE_DOMAIN)

            return response

        if authentication_utilities.verify_user_otp(account_otp=password_reset_otp, stored_hashed_otp_and_salt=hashed_authorization_otp_and_salt):
            new_password = request.data.get('new_password')
            if not new_password:
                return Response(
                    {"error": "Could not process your request, the provided information is invalid. New account password is required."}, 
                    status=status.HTTP_400_BAD_REQUEST
                )    

            password_validation.validate_password(new_password)

            # update the user's password
            requesting_user.set_password(new_password)
            requesting_user.save()
        
            response = Response(
                {"message": "Your seeran grades account password has been updated successfully, you can now login using your new credentials."}, 
                status=status.HTTP_200_OK
            )
            
            cache.delete(email_address + 'password_reset_hashed_authorization_otp_and_salt')

            response.delete_cookie('password_reset_email_address', domain=settings.SESSION_COOKIE_DOMAIN)
            response.delete_cookie('password_reset_authorization_otp', domain=settings.SESSION_COOKIE_DOMAIN)
            response.delete_cookie('request_authorized_to_reset_account_password', domain=settings.SESSION_COOKIE_DOMAIN)

            return response
        
        response = Response(
            {"denied": "Could not process your request, the provided password reset authorization One Time Passcode is invalid. Process forrbiden."}, 
            status=status.HTTP_403_FORBIDDEN
        )
    
        cache.delete(email_address + 'password_reset_hashed_authorization_otp_and_salt')

        response.delete_cookie('password_reset_email_address', domain=settings.SESSION_COOKIE_DOMAIN)
        response.delete_cookie('password_reset_authorization_otp', domain=settings.SESSION_COOKIE_DOMAIN)
        response.delete_cookie('request_authorized_to_reset_account_password', domain=settings.SESSION_COOKIE_DOMAIN)
        
        return response

    except BaseAccount.DoesNotExist:
        # if theres no user with the provided email return an error
        return Response(
            {"denied": "Could not process your request, an account with the provided credentials does not exist. Please check the account details and try again."}, 
            status=status.HTTP_404_NOT_FOUND
        )

    except Exception as e:
        return Response(
            {"error": {str(e)}}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# update email address

@api_view(["POST"])
@token_required
def email_address_update_account_password_verification(request): # first step
    try:
        password = request.data.get('password')
        if not password:
            return Response(
                {"error": "Could not process your request, no password was provided with the request. The current account password is required."}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        # verify the provided password with the requesting user account..
        requesting_user = authenticate_user(email_address=request.user.email_address, password=password)
        if requesting_user is None:
            return Response(
                {"error": "Could not process your request, the provided current password for the account is invalid. Please check your password and try again."}, 
                status=status.HTTP_401_UNAUTHORIZED
            )

        response = Response(
            {'message': "Your account password has been successfully verified. Provide your new email address on the next step then verify ownership."}, 
            status=status.HTTP_200_OK
        )

        email_address_update_otp = authentication_utilities.generate_and_cache_otp(
            request.user.email_address + 'email_address_update_authorization_otp_hash_and_salt'
        )
        authentication_utilities.set_cookie(
            response, 
            'email_address_update_authorization_otp', 
            email_address_update_otp, 
        )
        authentication_utilities.set_cookie(
            response, 
            'email_address_update_reuqest_authorized', 
            True, 
            httponly=False
        )

        return response

    except TokenError as e:
        return Response(
            {"error": "There was an error decoding your provided access token. If this error persists please open a bug report or email our support line with the following error trail: " + str(e)}, 
            status=status.HTTP_403_FORBIDDEN
        )

    except Exception as e:
        return Response(
            {"error": str(e)}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['POST'])
@token_required
def email_address_update_validate_new_email_address(request):
    try:
        email_address_update_authorization_otp = request.COOKIES.get('email_address_update_authorization_otp')
        if not email_address_update_authorization_otp:
            return Response(
                {"denied": "Could not process your request, the authorization credentials provided are missing. A authorization OTP is required to process this request."}, 
                status=status.HTTP_400_BAD_REQUEST
            )
    
        email_address_update_authorization_otp_hash_and_salt = cache.get(request.user.email_address + 'email_address_update_authorization_otp_hash_and_salt')
        if not email_address_update_authorization_otp_hash_and_salt:
            return Response(
                {"denied": "Could not process your request, your authorization credentials have expired. Returning you to the update email address page shortly."}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        requesting_user = BaseAccount.objects.get(email_address=request.user.email_address)
        
        # Access control based on user role and school compliance
        compliant = authentication_utilities.accounts_access_control(requesting_user)
        if compliant:
            return compliant
    
        # if everything above checks out verify the provided otp against the stored otp
        if authentication_utilities.verify_user_otp(account_otp=email_address_update_authorization_otp, stored_hashed_otp_and_salt=email_address_update_authorization_otp_hash_and_salt):
            new_email_address = request.data.get('new_email_address')
            if not new_email_address:
                return Response(
                    {"error": "Could not process your request, the provided information is invalid. Email address is required, please correct the email address and try again."}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
        
            # validate email format
            validate_email(new_email_address)

            email_address_ownership_otp, hashed_email_address_ownership_otp, email_address_ownership_salt = authentication_utilities.generate_otp()
            email_response = authentication_utilities.send_otp_email(
                requesting_user, 
                email_address_ownership_otp, 
                reason="We recieved a request to update your email address, looks like you're ready for a fresh start, we've got you covered! Use the OTP below to securely authenticate and update your email address.", 
                email_address=new_email_address
            )

            if email_response['status'] == 'success':
                email_address_ownership_authorization_otp, hashed_email_address_ownership_authorization_otp, email_address_ownership_authorization_salt = authentication_utilities.generate_otp()

                cache.set( # Cache OTP for 5 mins
                    new_email_address + 'email_address_update_verify_new_email_address_ownership_otp_hash_and_salt', 
                    (hashed_email_address_ownership_otp, email_address_ownership_salt), 
                    timeout=300
                ) 

                response = Response({"message": "A email address ownership verification OTP has been generated for your account and sent to your email address. It will be valid for the next 5 minutes.",}, status=status.HTTP_200_OK)
            
                email_address_ownership_authorization_otp = authentication_utilities.generate_and_cache_otp(
                    request.user.email_address + 'email_address_update_verify_new_email_address_ownership_authorization_otp_hash_and_salt'
                )

                authentication_utilities.set_cookie(
                    response, 
                    'email_address_update_verify_new_email_address_ownership_authorization_otp', 
                    email_address_ownership_authorization_otp, 
                )
                authentication_utilities.set_cookie(
                    response, 
                    'email_address_update_verify_new_email_address_ownership_email_address', 
                    new_email_address, 
                )
                authentication_utilities.set_cookie(
                    response, 
                    'request_authorized_to_verify_new_email_address_ownership', 
                    email_address_ownership_authorization_otp, 
                    httponly=False
                )

                cache.delete(request.user.email_address + 'email_address_update_authorization_otp_hash_and_salt')

                response.delete_cookie(
                    'email_address_update_authorization_otp', 
                    domain=settings.SESSION_COOKIE_DOMAIN
                )

                response.delete_cookie(
                    'email_address_update_reuqest_authorized', 
                    domain=settings.SESSION_COOKIE_DOMAIN
                )

                return response

            return Response(
                {"error": email_response['message']}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        response = Response(
            {"denied": "Could not process your request, the provided authorization One Time Passcode is incorrect. Action forrbiden."}, 
            status=status.HTTP_400_BAD_REQUEST
        )

        cache.delete(request.user.email_address + 'email_address_update_authorization_otp_hash_and_salt')

        response.delete_cookie(
            'email_address_update_authorization_otp', 
            domain=settings.SESSION_COOKIE_DOMAIN
        )
        response.delete_cookie(
            'email_address_update_reuqest_authorized', 
            domain=settings.SESSION_COOKIE_DOMAIN
        )

        return response
    
    except BaseAccount.DoesNotExist:
        # if theres no user with the provided email return an error
        return Response(
            {"denied": "Could not process your request, an account with the provided credentials does not exist. Please check the account details and try again."}, 
            status=status.HTTP_404_NOT_FOUND
        )
            
    except ValidationError:
        return Response(
            {"error": "Could not process your request, the provided email address is not in a valid format. Please correct the email address and try again"}, 
            status=status.HTTP_400_BAD_REQUEST
        )

    except Exception as e:
        # if any exceptions rise during return the response return it as the response
        return Response(
            {"error": str(e)}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
 
@api_view(['POST'])
def email_address_update_verify_new_email_address_ownership(request):
    try:
        # Get the new password and confirm password from the request data, and authorization otp from the cookies
        email_address_ownership_authorization_otp = request.COOKIES.get('email_address_update_verify_new_email_address_ownership_authorization_otp')
        new_email_address = request.COOKIES.get('email_address_update_verify_new_email_address_ownership_email_address')
        if not (email_address_ownership_authorization_otp or new_email_address):
            return Response(
                {"denied": "Could not process your request, your request is missing important authorization credentials needed to process this request."}, 
                status=status.HTTP_400_BAD_REQUEST
            ) 
    
        requesting_user = BaseAccount.objects.get(email_address=request.user.email_address)
        
        # Access control based on user role and school compliance
        compliant = authentication_utilities.accounts_access_control(requesting_user)
        if compliant:
            return compliant
        
        email_address_ownership_otp = request.data.get('email_address_ownership_otp')
        if not email_address_ownership_otp:
            return Response(
                {"error": "Could not process your request, your request does not include the email address ownership OTP needed to verify that the email address you provided belongs to you. Please try again."}, 
                status=status.HTTP_400_BAD_REQUEST
            ) 

        # get authorization otp from cache and verify provided otp
        email_address_update_verify_new_email_address_ownership_otp_hash_and_salt = cache.get(request.user.email_address + 'email_address_update_verify_new_email_address_ownership_otp_hash_and_salt')
        email_address_update_verify_new_email_address_ownership_authorization_otp_hash_and_salt = cache.get(request.user.email_address + 'email_address_update_verify_new_email_address_ownership_authorization_otp_hash_and_salt')

        if not (email_address_update_verify_new_email_address_ownership_otp_hash_and_salt or email_address_update_verify_new_email_address_ownership_authorization_otp_hash_and_salt):
            return Response({"denied": "Could not process your request, the authorization credentials generated for your account to aid this process have expired. Redirecting you back to the email address update page."}, status=status.HTTP_400_BAD_REQUEST) 

        if authentication_utilities.verify_user_otp(account_otp=email_address_ownership_otp, stored_hashed_otp_and_salt=email_address_update_verify_new_email_address_ownership_otp_hash_and_salt):
            if authentication_utilities.verify_user_otp(account_otp=email_address_ownership_authorization_otp, stored_hashed_otp_and_salt=email_address_update_verify_new_email_address_ownership_authorization_otp_hash_and_salt):
                requesting_user.email_address = new_email_address
                requesting_user.save()

                response = Response({"message": "Your accounts email address has been succesfully updated, use your new credentials on your next authentication into your dashboard."}, status=status.HTTP_200_OK)

                # OTP is verified, prompt the user to set their password
                cache.delete(request.user.email_address + 'email_address_update_verify_new_email_address_ownership_otp_hash_and_salt')
                cache.delete(request.user.email_address + 'email_address_update_verify_new_email_address_ownership_authorization_otp_hash_and_salt')
                cache.delete(request.user.email_address + 'email_address_update_verify_new_email_address_ownership_otp_failed_attempts')

                response.delete_cookie(
                    'email_address_update_verify_new_email_address_ownership_authorization_otp', 
                    domain=settings.SESSION_COOKIE_DOMAIN
                )

                response.delete_cookie(
                    'email_address_update_verify_new_email_address_ownership_email_address', 
                    domain=settings.SESSION_COOKIE_DOMAIN
                )

                response.delete_cookie(
                    'request_authorized_to_verify_new_email_address_ownership', 
                    domain=settings.SESSION_COOKIE_DOMAIN
                )
            
                return response
                        
            # if there's no error till here verification is successful, delete all cached otps
            cache.delete(request.user.email_address + 'email_address_update_verify_new_email_address_ownership_otp_hash_and_salt')
            cache.delete(request.user.email_address + 'email_address_update_verify_new_email_address_ownership_authorization_otp_hash_and_salt')
            cache.delete(request.user.email_address + 'email_address_update_verify_new_email_address_ownership_otp_failed_attempts')
            
            # if the authorization otp does'nt match the one stored for the user return an error 
            response = Response({"denied": "Could not process your request, your authorization OTP needed to process this request is invalid. Action forrbiden."}, status=status.HTTP_400_BAD_REQUEST)

            response.delete_cookie(
                'email_address_update_verify_new_email_address_ownership_authorization_otp', 
                domain=settings.SESSION_COOKIE_DOMAIN
            )

            response.delete_cookie(
                'email_address_update_verify_new_email_address_ownership_email_address', 
                domain=settings.SESSION_COOKIE_DOMAIN
            )

            response.delete_cookie(
                'request_authorized_to_verify_new_email_address_ownership', 
                domain=settings.SESSION_COOKIE_DOMAIN
            )

            return response

        attempts = cache.get(request.user.email_address + 'email_address_update_verify_new_email_address_ownership_otp_failed_attempts', 3)
        
        if attempts > 0:
            # Incorrect OTP, decrement attempts and handle expiration
            attempts -= 1
            cache.set(request.user.email_address + 'email_address_update_verify_new_email_address_ownership_otp_failed_attempts', attempts, timeout=300)  # Update attempts with expiration

            return Response(
                {"error": f"Could not process your request, the provided email ownership OTP is incorrect. You have {attempts} {'attempts' if attempts > 1 else 'attempt'} remaining."}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        cache.delete(request.user.email_address + 'email_address_update_verify_new_email_address_ownership_otp_hash_and_salt')
        cache.delete(request.user.email_address + 'email_address_update_verify_new_email_address_ownership_authorization_otp_hash_and_salt')
        cache.delete(request.user.email_address + 'email_address_update_verify_new_email_address_ownership_otp_failed_attempts')

        response = Response(
            {"denied": "Could not process your request, you have exceeded the maximum number of email ownership OTP verification attempts. Redirecting you to the update email address page shortly."}, 
            status=status.HTTP_403_FORBIDDEN
        )
        
        response.delete_cookie(
            'email_address_update_verify_new_email_address_ownership_authorization_otp', 
            domain=settings.SESSION_COOKIE_DOMAIN
        )

        response.delete_cookie(
            'email_address_update_verify_new_email_address_ownership_email_address', 
            domain=settings.SESSION_COOKIE_DOMAIN
        )

        response.delete_cookie(
            'request_authorized_to_verify_new_email_address_ownership', 
            domain=settings.SESSION_COOKIE_DOMAIN
        )

        return response

    except BaseAccount.DoesNotExist:
        # if theres no user with the provided email return an error
        return Response(
            {"denied": "Could not process your request, an account with the provided credentials does not exist. Please check the account details and try again."}, 
            status=status.HTTP_404_NOT_FOUND
        )

    except Exception as e:
        return Response(
            {"error": {str(e)}}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# update account password

@api_view(["POST"])
@token_required
def password_update_password_verification(request):    
    try:
        current_password = request.data.get('current_password')
        new_password = request.data.get('new_password')

        if not (current_password):
            return Response(
                {"error": "Could not process your request, the accounts current password was not provided. The current password is required to process this request."}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        if not (new_password):
            return Response(
                {"error": "Could not process your request, the new password was not provided. The new password is required to process this request."}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        # verify the provided password with the requesting user account..
        requesting_user = authenticate_user(email_address=request.user.email_address, password=current_password)
        if requesting_user is None:
            return Response(
                {"error": "Could not process your request, the provided current password for the account is invalid. Please check your password and try again."}, 
                status=status.HTTP_403_FORBIDDEN
            )

        validate_password(new_password)  # Ensure the password meets the validation criteria

        with transaction.atomic():
            requesting_user.set_password(new_password)
            requesting_user.save()

            access_tokens = AccountAccessToken.objects.filter(account=requesting_user)

            for access_token in access_tokens:
                # Decode the token
                token = decode(access_token.access_token_string)
                
                # Calculate the remaining time for the token to expire
                expiration_time = token.payload['exp'] - int(time.time())

                if expiration_time > 0:
                    cache.set(access_token.access_token_string, 'blacklisted', timeout=expiration_time)

        return Response(
            {'message': "Your account password has been successfully updated, use your new credentials on your next authentication into your dashboard."}, 
            status=status.HTTP_200_OK
        )

    except TokenError as e:
        return Response(
            {"error": "There was an error decoding your provided access token. If this error persists please open a bug report or email our support line with the following error trail: " + str(e)}, 
            status=status.HTTP_403_FORBIDDEN
        )

    except ValidationError as e:
        return Response(
            {"error": e.messages}, 
            status=status.HTTP_400_BAD_REQUEST
        )

    except Exception as e:
        return Response(
            {"error": str(e)}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# logout

@api_view(["POST"])
@token_required
def log_out(request):    
    try:
        access_token = request.COOKIES.get('access_token')

        # Decode the token
        token = decode(access_token)
        
        # Calculate the remaining time for the token to expire
        expiration_time = token.payload['exp'] - int(time.time())
        
        if expiration_time > 0:
            cache.set(access_token, 'blacklisted', timeout=expiration_time)
    
        # delete token from database
        AccountAccessToken.objects.filter(access_token_string=str(access_token)).delete()

        return authentication_utilities.remove_authorization_cookies(
            Response(
                {'message': "Your current session has been logged out successfully and access token has been blacklisted for the remainder of it's lifespan."}, 
                status=status.HTTP_200_OK
            )
        )
    
    except TokenError as e:
        return Response(
            {"error": "Could not process your request, there was an error decoding your provided access token. If this error persists please open a bug report or email our support line and provide the following error trail: " + str(e)}, 
            status=status.HTTP_200_OK
        )

    except Exception as e:
        return Response(
            {"error": str(e)}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )