# rest framework
from rest_framework import status
from rest_framework.response import Response
from rest_framework.decorators import api_view, throttle_classes
from rest_framework.throttling import UserRateThrottle

# django
from django.db import transaction
from django.core.exceptions import ValidationError
from django.contrib.auth import authenticate as authenticate_user, password_validation
from django.core.cache import cache
from django.core.validators import validate_email

# models
from accounts.models import BaseAccount
from account_access_tokens.models import AccountAccessToken

# utility functions 
from .utils import generate_token, generate_otp, verify_user_otp, validate_names, send_otp_email
from account_access_tokens.utils import manage_user_sessions

# custom decorators
from .decorators import token_required

# utility functions 
from accounts import utils as accounts_utilities


class CustomRateThrottle(UserRateThrottle):
    rate = '5/hour'
    
    def throttle_failure(self):
        """
        Custom response for rate limit exceeded.
        """
        return Response({"error": "too many login attempts. please try again later."}, status=status.HTTP_429_TOO_MANY_REQUESTS)
    

@api_view(['POST'])
@throttle_classes([CustomRateThrottle])
def login(request):
    try:
        email_address = request.data.get('email_address')
        password = request.data.get('password')
        
        # Verify user credentials
        requesting_user = authenticate_user(email_address=email_address, password=password)
        if requesting_user is None:
            return Response({"error": "the provided credentials are invalid, please check your email and password and try again"}, status=status.HTTP_401_UNAUTHORIZED)
        
        # Access control based on user role and school compliance
        if requesting_user.role in ['PRINCIPAL', 'ADMIN', 'TEACHER', 'STUDENT']:
            # Fetch the corresponding child model based on the user's role
            requesting_account = accounts_utilities.get_account_and_linked_school(requesting_user.account_id, requesting_user.role)

            if requesting_account.school.none_compliant:
                return Response({"denied": "access denied"}, status=status.HTTP_403_FORBIDDEN)
            
        # generate an access token for the user 
        token = generate_token(requesting_user)

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
                    response = Response({"message": "You will have access to your dashboard for the next 24 hours, until your session ends", "alert" : "Your email address has been blacklisted", "role" : requesting_user.role.title()}, status=status.HTTP_200_OK)
                    response.set_cookie('access_token', token['access'], domain='.seeran-grades.cloud', samesite='None', secure=True, httponly=True, max_age=86400)

                    return response
                
                return Response({"error": "Server error.. Could not generate access token for your account"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
            # Generate OTP and send to user's email for MFA
            otp, hashed_otp, salt = generate_otp()
            email_response = send_otp_email(requesting_user, otp, reason="Your account has multi-factor authentication toggled on, this OTP was generated in response to your login request.")
            
            if email_response['status'] == 'success':
                login_authorization_otp, hashed_login_authorization_otp, salt = generate_otp()

                cache.set(requesting_user.email+'login_otp', (hashed_otp, salt), timeout=300)  # Cache OTP for 5 mins
                cache.set(requesting_user.email+'login_authorization_otp', (hashed_login_authorization_otp, salt), timeout=300)  # Cache auth OTP for 5 mins

                response = Response({"multifactor_authentication": "A new OTP has been sent to your email address. Please check your inbox"}, status=status.HTTP_200_OK)
                response.set_cookie('login_authorization_otp', login_authorization_otp, domain='.seeran-grades.cloud', samesite='None', secure=True, httponly=True, max_age=300)  # Set auth OTP cookie (5 mins)
                
                return response
            else:
                return Response({"error": email_response['message']}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Handle login without MFA
        if 'access' in token:
            session_response = manage_user_sessions(requesting_user, token)
            if session_response:  # If the function returns a response, it indicates an error
                return session_response
            
            response = Response({"message": "You will have access to your dashboard for the next 24 hours, until your session ends", "role" : requesting_user.role.title()}, status=status.HTTP_200_OK)
        
            # Set access token cookie with custom expiration (24 hours)
            response.set_cookie('access_token', token['access'], domain='.seeran-grades.cloud', samesite='None', secure=True, httponly=True, max_age=86400)
        
        else:
            response = Response({"error": "Server error.. Could not generate access token for your account, please try again in a moment"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return response
    
    except BaseAccount.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return Response({"error": "The credentials you entered are invalid. Please check your email and password and try again"}, status=status.HTTP_404_NOT_FOUND)
    
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@throttle_classes([CustomRateThrottle])
def multi_factor_authentication_login(request):
    # try to get the user object using the provided email address
    try:
        # retrieve the provided email, otp and the authorization otp in the cookie
        email_address = request.data.get('email_address')
        otp = request.data.get('otp')
        authorization_cookie_otp = request.COOKIES.get('login_authorization_otp')
        
        # if anyone of these is missing return a 400 error
        if not email_address or not otp or not authorization_cookie_otp:
            return Response({"error": "missing credentials"}, status=status.HTTP_400_BAD_REQUEST)
        
        requesting_user = BaseAccount.objects.get(email_address=email_address)

        if requesting_user.role in ['PRINCIPAL', 'ADMIN', 'TEACHER', 'STUDENT']:
            # Fetch the corresponding child model based on the user's role
            requesting_account = accounts_utilities.get_account_and_linked_school(requesting_user.account_id, requesting_user.role)

            if requesting_account.school.none_compliant:
                return Response({"denied": "access denied"}, status=status.HTTP_403_FORBIDDEN)

        # after getting the user object retrieve the stored otp from cache 
        stored_hashed_otp_and_salt = cache.get(requesting_user.email_address+'login_otp')
        
        # try to get the the authorization otp from cache
        hashed_authorization_otp_and_salt = cache.get(requesting_user.email_address + 'login_authorization_otp')
        
        if not (hashed_authorization_otp_and_salt and stored_hashed_otp_and_salt):
            # if there's no authorization otp in cache( wasn't provided in the first place, or expired since it also has a 5 minute lifespan )
            return Response({"denied": "OTP expired"}, status=status.HTTP_400_BAD_REQUEST)
    
        # if everything above checks out verify the provided otp against the stored otp
        if verify_user_otp(user_otp=otp, stored_hashed_otp_and_salt=stored_hashed_otp_and_salt):
            # provided otp is verified successfully
                        
            if not verify_user_otp(user_otp=authorization_cookie_otp, stored_hashed_otp_and_salt=hashed_authorization_otp_and_salt):
                # if the authorization otp does'nt match the one stored for the user return an error 
                response = Response({"denied": "incorrect authorization OTP, action forrbiden"}, status=status.HTTP_400_BAD_REQUEST)
                            
                # if there's no error till here verification is successful, delete all cached otps
                cache.delete(requesting_user.email_address+'login_otp')
                cache.delete(requesting_user.email_address+'login_authorization_otp')

                response.delete_cookie('login_authorization_otp', domain='.seeran-grades.cloud')
                return response
            
            # if there's no error till here verification is successful, delete all cached otps
            cache.delete(requesting_user.email_address+'login_otp')
            cache.delete(requesting_user.email_address+'login_authorization_otp_attempts')
            
            # then generate an access and refresh token for the user 
            token = generate_token(requesting_user)
            
            if 'access' in token:
                session_response = manage_user_sessions(requesting_user, token)
                if session_response:  # If the function returns a response, it indicates an error
                    return session_response
                
                # set access token cookie with custom expiration (5 mins)
                response = Response({"message": "you will have access to your dashboard for the next 24 hours, until your session ends", "role" : requesting_user.role.title()}, status=status.HTTP_200_OK)
                response.set_cookie('access_token', token['access'], domain='.seeran-grades.cloud', samesite='None', secure=True, httponly=True, max_age=86400)

                return response
            
            return Response({"error": "the server could not generate an access token for your account, please try again in a moment"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        attempts = cache.get(email_address + 'login_authorization_otp_attempts', 3)
        
        if attempts <= 0:
            cache.delete(email_address+'login_otp')
            cache.delete(email_address+'login_authorization_otp_attempts')
            return Response({"denied": "maximum OTP verification attempts exceeded.."}, status=status.HTTP_400_BAD_REQUEST)
        
        # Incorrect OTP, decrement attempts and handle expiration
        attempts -= 1
        cache.set(email_address+'login_authorization_otp_attempts', attempts, timeout=300)  # Update attempts with expiration

        return Response({"error": f"incorrect OTP.. {attempts} remaining"}, status=status.HTTP_400_BAD_REQUEST)
    
    except BaseAccount.DoesNotExist:
        # Handle the case where the provided email does not exist
        return {'error': 'an account with the provided credentials does not exist, please check the account details and try again'}

    except Exception as e:
        # if any exceptions rise during return the response return it as the response
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@throttle_classes([CustomRateThrottle])
def signin(request):
    try:
        full_names = request.data.get('full_names')
        email_address = request.data.get('email_address')

        # if there's a missing credential return an error
        if not full_names or not email_address:
            return Response({"error": "sign-in credentials are incomplete. please provide all required information"}, status=status.HTTP_400_BAD_REQUEST)
    
        # validate email format
        validate_email(email_address)

        # validate provided names
        if not validate_names(full_names):
            return Response({"error": "please enter only your first name and surname"}, status=status.HTTP_400_BAD_REQUEST)

        # try to validate the credentials by getting a user with the provided credentials 
        requesting_user = BaseAccount.objects.get(email_address=email_address)
            
        # check if the provided name and surname are correct
        name, surname = full_names.split(' ', 1)

        if not ((requesting_user.name.casefold() == name.casefold() and requesting_user.surname.casefold() == surname.casefold()) or (requesting_user.name.casefold() == surname.casefold() and requesting_user.surname.casefold() == name.casefold())):
            return Response({"error": "the credentials you entered are invalid. please check your full name and email and try again"}, status=status.HTTP_400_BAD_REQUEST)

        # Access control based on user role and school compliance
        if requesting_user.role in ['PRINCIPAL', 'ADMIN', 'TEACHER', 'STUDENT']:
            # Fetch the corresponding child model based on the user's role
            requesting_account = accounts_utilities.get_account_and_linked_school(requesting_user.account_id, requesting_user.role)

            if requesting_account.school.none_compliant:
                return Response({"denied": "access denied"}, status=status.HTTP_403_FORBIDDEN)
        
        # if there is a user with the provided credentials check if their account has already been activated 
        if requesting_user.activated:
            return Response({"error": "your request could not be processed. access has been denied due to invalid or incomplete information"}, status=status.HTTP_403_FORBIDDEN)
        
        # if the users account has'nt been activated yet check if their email address is banned
        if requesting_user.email_banned:
            # if their email address is banned return an error and let the user know and how they can appeal( if they even can )
            return Response({"alert" : "your email address has been blacklisted" })
    
        # if everything checks out without an error 
        # create an otp for the user
        otp, hashed_otp, salt = generate_otp()
        email_response = send_otp_email(requesting_user, otp, reason="We are pleased to have you trying out our service, this OTP was generated in response to your account activation request..")
        
        if email_response['status'] == 'success':
            cache.set(requesting_user.email_address+'signin_otp', (hashed_otp, salt), timeout=300)  # 300 seconds = 5 mins
            return Response({"message": "a sign-in OTP has been generated and sent to your email address.. it will be valid for the next 5 minutes",}, status=status.HTTP_200_OK)
        
        else:
            return Response({"error": email_response['message']}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    except BaseAccount.DoesNotExist:
        # if there's no user with the provided credentials return an error 
        return Response({"error": "the credentials you entered are invalid. please check your full name and email and try again"}, status=status.HTTP_404_NOT_FOUND)
    
    except ValidationError:
        return Response({"error": "the provided email address is not in a valid format. please correct the email address and try again"}, status=status.HTTP_400_BAD_REQUEST)

    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
def activate_account(request):

    """
        This view handles the account activation process for first-time sign-in. It expects a POST request with the user's email and new password.

        Steps:
        1. It retrieves the authorization OTP from the cookie, and the provided email and new password.
        2. If any of these are missing or if the new password doesn't match the confirm password, it returns a 400 Bad Request error.
        3. It retrieves the stored authorization OTP from the cache.
        4. If there's no OTP in the cache, it returns a 400 Bad Request error.
        5. If any other exception occurs while retrieving the OTP from the cache, it returns a 500 Internal Server Error.
        6. It verifies the provided OTP against the stored OTP.
        7. If the provided OTP is verified successfully, it activates the user's account and sets the new password.
        8. It then generates an access and refresh token for the user, sets the access/refresh token cookies, and returns a successful response.
        9. If the user with the provided email doesn't exist, it returns a 404 Not Found error.
        10. If any other exception occurs, it returns a 500 Internal Server Error.

        Note: All exceptions are handled and appropriate HTTP status codes are returned.
    """
    
    try:
        email_address = request.data.get('email_address')
        password = request.data.get('password')

        if not email_address or not password:
            return Response({"error": "missing credentials, all fields are required"}, status=status.HTTP_400_BAD_REQUEST)

        # get authorization otp 
        otp = request.COOKIES.get('signin_authorization_otp')
        stored_hashed_otp_and_salt = cache.get(email_address + 'signin_authorization_otp')

        if not stored_hashed_otp_and_salt:
            response = Response({"denied": "there is no authorization OTP for your account on record.. process forrbiden"}, status=status.HTTP_400_BAD_REQUEST)
            if otp:
                response.delete_cookie('signin_authorization_otp', domain='.seeran-grades.cloud')
            return response

        if not otp:
            cache.delete(email_address + 'signin_authorization_otp')
            return Response({"denied": "Your request does not contain an authorization OTP.. request forrbiden"}, status=status.HTTP_400_BAD_REQUEST)

        if not verify_user_otp(account_otp=otp, stored_hashed_otp_and_salt=stored_hashed_otp_and_salt):
            response = Response({"denied": "Your requests authorization OTP is invalid.. request forrbiden"}, status=status.HTTP_400_BAD_REQUEST)

            cache.delete(email_address + 'signin_authorization_otp')
            response.delete_cookie('signin_authorization_otp', domain='.seeran-grades.cloud')
            return response
        
        # activate users account
        with transaction.atomic():
            print('about to activate account')
            account = BaseAccount.objects.activate(email_address=email_address, password=password)

            # generate an access and refresh token for the user 
            account_access_token = generate_token(account=account)
            AccountAccessToken.objects.create(account=account, access_token_string=account_access_token['access'])

        response = Response({"message": "You have successully activated your account. Welcome to seeran grades.", "role": account.role}, status=status.HTTP_200_OK)
        # set access/refresh token cookies
        response.set_cookie('access_token', account_access_token['access'], domain='.seeran-grades.cloud', samesite='None', secure=True, httponly=True, max_age=86400)
        
        return response
    
    except BaseAccount.DoesNotExist:
        # if theres no user with the provided email return an error
        return Response({"denied": "an account with the provided credentials does not exist. please check the account details and try again"}, status=status.HTTP_404_NOT_FOUND)
  
    except Exception as e:
        # if any exceptions rise during return the response return it as the response
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["GET"])
@token_required
def authenticate(request):

    """
        This view handles the authentication of incoming requests. It expects a GET request.

        Steps:
        1. If the user is authenticated, it returns a 200 OK status code along with the user's role.
        2. If the user is not authenticated, it returns a 401 Unauthorized error.

        Note: The `@token_required` decorator is used to check if the incoming request has a valid token.
    """
   
    # if the user is authenticated, return a 200 status code
    if request.user:
        role = request.user.role

        if role not in ['FOUNDER', 'PARENT', 'PRINCIPAL', 'ADMIN', 'TEACHER', 'STUDENT']:
            return Response({"error": "your request could not be processed, your account has an invalid role"}, status=status.HTTP_401_UNAUTHORIZED)

        # Access control based on user role and school compliance
        elif request.user.role in ['PRINCIPAL', 'ADMIN', 'TEACHER', 'STUDENT']:
            # Fetch the corresponding child model based on the user's role
            requesting_account = accounts_utilities.get_account_and_linked_school(request.user.account_id, request.user.role)

            if requesting_account.school.none_compliant:
                return Response({"denied": "access denied"}, status=status.HTTP_403_FORBIDDEN)

        return Response({"role" : request.user.role.title()}, status=status.HTTP_200_OK)

    else:
        return Response({"error" : "request not authenticated.. access denied",}, status=status.HTTP_403_FORBIDDEN)


@api_view(['POST'])
def verify_otp(request):

    try:
        email_address = request.data.get('email_address')
        otp = request.data.get('otp')
    
        if not email_address or not otp:
            return Response({"error": "invalid request.. email and OTP are required."}, status=status.HTTP_400_BAD_REQUEST)
        
        stored_hashed_otp_and_salt = cache.get(email_address+'signin_otp')

        if not stored_hashed_otp_and_salt:
            cache.delete(email_address+'signin_otp_attempts')
            return Response({"denied": "no sign-in OTP for account on record.. please generate a new one "}, status=status.HTTP_403_FORBIDDEN)

        if verify_user_otp(account_otp=otp, stored_hashed_otp_and_salt=stored_hashed_otp_and_salt):
            
            # OTP is verified, prompt the user to set their password
            cache.delete(email_address+'signin_otp')
            
            authorization_otp, hashed_authorization_otp, salt = generate_otp()
            
            response = Response({"message": "OTP verified successfully"}, status=status.HTTP_200_OK)

            cache.set(email_address+'signin_authorization_otp', (hashed_authorization_otp, salt), timeout=300)  # 300 seconds = 5 mins
            response.set_cookie('signin_authorization_otp', authorization_otp, domain='.seeran-grades.cloud', samesite='None', secure=True, httponly=True, max_age=300)  # 300 seconds = 5 mins
        
            return response
        
        else:

            attempts = cache.get(email_address+'signin_otp_attempts', 3)
            
            # Incorrect OTP, decrement attempts and handle expiration
            attempts -= 1
            
            if attempts <= 0:
                cache.delete(email_address+'signin_otp')
                cache.delete(email_address+'signin_otp_attempts')
                
                return Response({"denied": "maximum OTP verification attempts exceeded.. generated sign-in OTP for account discarded"}, status=status.HTTP_403_FORBIDDEN)
            
            cache.set(email_address+'signin_otp_attempts', attempts, timeout=300)  # Update attempts with expiration

            return Response({"error": f"provided OTP incorrect.. you have {attempts} verification attempts remaining"}, status=status.HTTP_400_BAD_REQUEST)
 
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# validate email before password reset
@api_view(['POST'])
@throttle_classes([CustomRateThrottle])
def validate_password_reset(request):
    
    try:
        # check for sent email
        email_address = request.data.get('email_address')
        if not email_address:
            return Response({"error": "request error, no email address provided.. email address is required"}, status=status.HTTP_400_BAD_REQUEST)
        
        # try to get the user with the provided email
        requesting_user = BaseAccount.objects.get(email_address=email_address)

        # Access control based on user role and school compliance
        if requesting_user.role in ['PRINCIPAL', 'ADMIN', 'TEACHER', 'STUDENT']:
            # Fetch the corresponding child model based on the user's role
            requesting_account = accounts_utilities.get_account_and_linked_school(requesting_user.account_id, requesting_user.role)

            if requesting_account.school.none_compliant:
                return Response({"denied": "access denied"}, status=status.HTTP_403_FORBIDDEN)
            
        # check if the account is activated 
        if requesting_user.activated == False:
            return Response({"error": "action forbidden for account with provided credentials"}, status=status.HTTP_403_FORBIDDEN)
        
        # check if the email is banned 
        if requesting_user.email_banned:
            return Response({ "error" : "your email address has been banned, failed to send OTP.. you can visit your school to have it changed"}, status=status.HTTP_400_BAD_REQUEST)
        
        # validate email format
        validate_email(email_address)
        
        # if everything checks out without an error 
        # create an otp for the user
        otp, hashed_otp, salt = generate_otp()
        email_response = send_otp_email(requesting_user, otp, reason="We recieved a password reset request for your account, this OTP was generated in response to your password reset request..")
        
        if email_response['status'] == 'success':
            cache.set(requesting_user.email_address+'password_reset_otp', (hashed_otp, salt), timeout=300)  # 300 seconds = 5 mins
            return Response({"message": "a password reset OTP has been generated and sent to your email address.. it will be valid for the next 5 minutes",}, status=status.HTTP_200_OK)
        
        else:
            return Response({"error": email_response['message']}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    except BaseAccount.DoesNotExist:
        # if theres no user with the provided email return an error
        return Response({"error": "an account with the provided credentials does not exist. please check the account details and try again"}, status=status.HTTP_404_NOT_FOUND)
            
    except ValidationError:
        return Response({"error": "the provided email address is not in a valid format. please correct the email address and try again"}, status=status.HTTP_400_BAD_REQUEST)

    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
def password_reset_otp_verification(request):
    
    try:
        email_address = request.data.get('email_address')
        otp = request.data.get('otp')
    
        if not email_address or not otp:
            return Response({"error": "email and OTP are required."}, status=status.HTTP_400_BAD_REQUEST)
    
        stored_hashed_otp_and_salt = cache.get(email_address+'password_reset_otp')
        if not stored_hashed_otp_and_salt:
            return Response({"denied": "no password reset OTP for account on record.. please generate a new one"}, status=status.HTTP_400_BAD_REQUEST)
    
        if verify_user_otp(user_otp=otp, stored_hashed_otp_and_salt=stored_hashed_otp_and_salt):
            
            cache.delete(email_address+'password_reset_otp')
            authorization_otp, hashed_authorization_otp, salt = generate_otp()

            response = Response({"message": "OTP verified successfully"}, status=status.HTTP_200_OK)

            cache.set(email_address + 'password_reset_authorization_otp', (hashed_authorization_otp, salt), timeout=300)  # 300 seconds = 5 mins
            response.set_cookie('password_reset_authorization_otp', authorization_otp, domain='.seeran-grades.cloud', samesite='None', secure=True, httponly=True, max_age=300)  # 300 seconds = 5 mins
            response.set_cookie('email_address', email_address, domain='.seeran-grades.cloud', samesite='None', secure=True, httponly=True, max_age=300)  # 300 seconds = 5 mins

            return response
        
        else:
            return Response({"error": "incorrect OTP. Please try again."}, status=status.HTTP_400_BAD_REQUEST)
    
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
 

# reset password  used when user has forgotten their password
@api_view(['POST'])
def reset_password(request):
    
    try:
        # Get the new password and confirm password from the request data, and authorization otp from the cookies
        otp = request.COOKIES.get('password_reset_authorization_otp')
        email_address = request.COOKIES.get('email_address')
        new_password = request.data.get('new_password')
        
        if not (new_password or otp or email_address):
            return Response({"error": "invalid request.. missing credentials"}, status=status.HTTP_400_BAD_REQUEST)    
    
        user = BaseAccount.objects.get(email_address=email_address)
        
        # get authorization otp from cache and verify provided otp
        hashed_authorization_otp_and_salt = cache.get(user.email_address+'password_reset_authorization_otp')
        if not hashed_authorization_otp_and_salt:
            return Response({"denied": "no password reset authorization OTP for account on record.. process forrbiden"}, status=status.HTTP_403_FORBIDDEN)
        
        if verify_user_otp(user_otp=otp, stored_hashed_otp_and_salt=hashed_authorization_otp_and_salt):
            response = Response({"denied": "requests provided authorization OTP is invalid.. process forrbiden"}, status=status.HTTP_403_FORBIDDEN)
        
        password_validation.validate_password(new_password)

        # update the user's password
        user.set_password(new_password)
        user.save()
    
        response = Response({"message": "your accounts password has been changed successfully.. you can now login with your new credentials"}, status=200)
   
        return response
    
    except BaseAccount.DoesNotExist:
        # if theres no user with the provided email return an error
        return Response({"denied": "an account with the provided credentials does not exist. please check the account details and try again"}, status=status.HTTP_404_NOT_FOUND)

    except Exception as e:
        return Response({"error": {str(e)}}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

