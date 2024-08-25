# python
from datetime import timedelta, timezone

# rest framework
from rest_framework import status
from rest_framework.response import Response
from rest_framework.decorators import api_view, throttle_classes
from rest_framework.throttling import UserRateThrottle

# django
from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.contrib.auth.password_validation import validate_password
from django.core.cache import cache
from django.core.validators import validate_email

# models
from users.models import BaseUser, Founder,Principal, Admin, Teacher, Student, Parent
from auth_tokens.models import AccessToken

# serializers
from .serializers import CustomTokenObtainPairSerializer

# utility functions 
from .utils import generate_token, generate_otp, verify_user_otp, validate_names, send_otp_email

# custom decorators
from .decorators import token_required


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
        serializer = CustomTokenObtainPairSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        token = serializer.validated_data
        
        # Retrieve user and related school
        user = BaseUser.objects.prefetch_related('access_tokens').get(email=request.data.get('email'))
        
        # Access control based on user role and school compliance
        role_check_mapping = {
            'PRINCIPAL': user.principal.school.none_compliant if hasattr(user, 'principal') else False,
            'ADMIN': user.admin.school.none_compliant if hasattr(user, 'admin') else False,
            'TEACHER': user.teacher.school.none_compliant if hasattr(user, 'teacher') else False,
            'STUDENT': user.student.school.none_compliant if hasattr(user, 'student') else False
        }

        if user.role in role_check_mapping and role_check_mapping[user.role]:
            return Response({"denied": "access denied"}, status=status.HTTP_403_FORBIDDEN)
     
        # Handle multi-factor authentication (MFA) if enabled for the user
        if user.multifactor_authentication:
            # Disable MFA if email is banned (for security reasons)
            if user.email_banned:
                user.multifactor_authentication = False
                user.save()
                
                # Clear old access tokens if any, to limit active sessions
                if 'access' in token:
                    cutoff_time = timezone.now() - timedelta(hours=24)

                    with transaction.atomic():
                        expired_access_tokens = user.access_tokens.filter(created_at__lt=cutoff_time)
                        if expired_access_tokens.exists():
                            expired_access_tokens.delete()

                    access_tokens_count = user.access_tokens.count()
                    
                    if access_tokens_count >= 3:
                        return Response({"error": "You have reached the maximum number of connected devices. Please disconnect another device to proceed"}, status=status.HTTP_403_FORBIDDEN)
                    
                    with transaction.atomic():
                        AccessToken.objects.create(user=user, token=token['access'])

                    # Set access token cookie with custom expiration (24 hours)
                    response = Response({"message": "You will have access to your dashboard for the next 24 hours, until your session ends", "alert" : "Your email address has been blacklisted", "role" : user.role.title()}, status=status.HTTP_200_OK)
                    response.set_cookie('access_token', token['access'], domain='.seeran-grades.cloud', samesite='None', secure=True, httponly=True, max_age=86400)

                    return response
                
                return Response({"error": "Server error.. Could not generate access token for your account"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
            # Generate OTP and send to user's email for MFA
            otp, hashed_otp, salt = generate_otp()
            email_response = send_otp_email(user, otp, reason="Your account has multi-factor authentication toggled on, this OTP was generated in response to your login request.")
            
            if email_response['status'] == 'success':
                cache.set(user.email+'login_otp', (hashed_otp, salt), timeout=300)  # Cache OTP for 5 mins
                login_authorization_otp, hashed_login_authorization_otp, salt = generate_otp()
                cache.set(user.email+'login_authorization_otp', (hashed_login_authorization_otp, salt), timeout=300)  # Cache auth OTP for 5 mins

                response = Response({"multifactor_authentication": "A new OTP has been sent to your email address. Please check your inbox"}, status=status.HTTP_200_OK)
                response.set_cookie('login_authorization_otp', login_authorization_otp, domain='.seeran-grades.cloud', samesite='None', secure=True, httponly=True, max_age=300)  # Set auth OTP cookie (5 mins)
                
                return response
            else:
                return Response({"error": email_response['message']}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Handle login without MFA
        if 'access' in token:
            cutoff_time = timezone.now() - timedelta(hours=24)

            with transaction.atomic():
                expired_access_tokens = user.access_tokens.filter(created_at__lt=cutoff_time)
                if expired_access_tokens.exists():
                    expired_access_tokens.delete()
                    
            access_tokens_count = user.access_tokens.count()
            
            if access_tokens_count >= 3:
                return Response({"error": "You have reached the maximum number of connected devices. Please disconnect another device to proceed"}, status=status.HTTP_403_FORBIDDEN)
            
            response = Response({"message": "You will have access to your dashboard for the next 24 hours, until your session ends", "role" : user.role.title()}, status=status.HTTP_200_OK)
                    
            with transaction.atomic():
                AccessToken.objects.create(user=user, token=token['access'])
        
            # Set access token cookie with custom expiration (24 hours)
            response.set_cookie('access_token', token['access'], domain='.seeran-grades.cloud', samesite='None', secure=True, httponly=True, max_age=86400)
        
        else:
            response = Response({"error": "Server error.. Could not generate access token for your account"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return response
    
    except BaseUser.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return Response({"error": "The credentials you entered are invalid. Please check your email and password and try again"}, status=status.HTTP_404_NOT_FOUND)
    
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



@api_view(['POST'])
@throttle_classes([CustomRateThrottle])
def multi_factor_authentication_login(request):
    # retrieve the provided email, otp and the authorization otp in the cookie
    email = request.data.get('email')
    otp = request.data.get('otp')
    authorization_cookie_otp = request.COOKIES.get('login_authorization_otp')
    
    # if anyone of these is missing return a 400 error
    if not email or not otp or not authorization_cookie_otp:
        return Response({"error": "missing credentials"}, status=status.HTTP_400_BAD_REQUEST)
    
    # try to get the user object using the provided email address
    try:
        
        user = BaseUser.objects.get(email=email)
            # Access control based on user role and school compliance
        role_check_mapping = {
            'PRINCIPAL': user.principal.school.none_compliant,
            'ADMIN': user.admin.school.none_compliant,
            'TEACHER': user.teacher.school.none_compliant,
            'STUDENT': user.student.school.none_compliant
        }

        if user.role in role_check_mapping and role_check_mapping[user.role]:
            return Response({"denied": "access denied"}, status=status.HTTP_403_FORBIDDEN)

        # after getting the user object retrieve the stored otp from cache 
        stored_hashed_otp_and_salt = cache.get(user.email+'login_otp')
        
        # try to get the the authorization otp from cache
        hashed_authorization_otp_and_salt = cache.get(user.email + 'login_authorization_otp')
        
        if not ( hashed_authorization_otp_and_salt and stored_hashed_otp_and_salt ):
            # if there's no authorization otp in cache( wasn't provided in the first place, or expired since it also has a 5 minute lifespan )
            return Response({"denied": "OTP expired"}, status=status.HTTP_400_BAD_REQUEST)
    
        # if everything above checks out verify the provided otp against the stored otp
        if verify_user_otp(user_otp=otp, stored_hashed_otp_and_salt=stored_hashed_otp_and_salt):
            # provided otp is verified successfully
                        
            if not verify_user_otp(user_otp=authorization_cookie_otp, stored_hashed_otp_and_salt=hashed_authorization_otp_and_salt):
                # if the authorization otp does'nt match the one stored for the user return an error 
                response = Response({"denied": "incorrect authorization OTP, action forrbiden"}, status=status.HTTP_400_BAD_REQUEST)
                            
                # if there's no error till here verification is successful, delete all cached otps
                cache.delete(user.email+'login_otp')
                cache.delete(user.email + 'login_authorization_otp')

                response.delete_cookie('login_authorization_otp', domain='.seeran-grades.cloud')
                return response
            
            # if there's no error till here verification is successful, delete all cached otps
            cache.delete(user.email+'login_otp')
            cache.delete(user.email + 'login_authorization_otp_attempts')
            
            # then generate an access and refresh token for the user 
            token = generate_token(user)
            
            if 'access' in token:
                # Calculate cutoff time for expired tokens
                cutoff_time = timezone.now() - timedelta(hours=24)
            
                with transaction.atomic():
                    # Delete all RefreshToken objects for the user that were created before the cutoff_time
                    expired_access_tokens = user.access_tokens.filter(created_at__lt=cutoff_time)
                    if expired_access_tokens.exists():
                        expired_access_tokens.delete()

                # Count the remaining RefreshToken objects for the user
                access_tokens_count = user.access_tokens.count()
                
                if access_tokens_count >= 3:
                    return Response({"error": "maximum number of connected devices reached"}, status=status.HTTP_403_FORBIDDEN)
                
                with transaction.atomic():
                    AccessToken.objects.create(user=user, token=token['access'])
                
                # set access token cookie with custom expiration (5 mins)
                response = Response({"message": "you will have access to your dashboard for the next 24 hours, until your session ends", "role" : user.role.title()}, status=status.HTTP_200_OK)
                response.set_cookie('access_token', token['access'], domain='.seeran-grades.cloud', samesite='None', secure=True, httponly=True, max_age=86400)

                return response
            
            return Response({"error": "the server could not generate an access token for your account, please try again in a moment"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        attempts = cache.get(email + 'login_authorization_otp_attempts', 3)
        
        if attempts <= 0:
            cache.delete(email+'login_otp')
            cache.delete(email + 'login_authorization_otp_attempts')
            return Response({"denied": "maximum OTP verification attempts exceeded.."}, status=status.HTTP_400_BAD_REQUEST)
        
        # Incorrect OTP, decrement attempts and handle expiration
        attempts -= 1
        cache.set(email + 'login_authorization_otp_attempts', attempts, timeout=300)  # Update attempts with expiration

        return Response({"error": f"incorrect OTP.. {attempts} remaining"}, status=status.HTTP_400_BAD_REQUEST)
    
    except BaseUser.DoesNotExist:
        # Handle the case where the provided email does not exist
        return {'error': 'an account with the provided credentials does not exist, please check the account details and try again'}

    except Exception as e:
        # if any exceptions rise during return the response return it as the response
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@throttle_classes([CustomRateThrottle])
def signin(request):

    """
        This view handles the first-time sign-in process. It expects a POST request with the user's full name and email.

        Steps:
        1. It retrieves the provided full name and email.
        2. If any of these are missing, it returns a 400 Bad Request error.
        3. It validates the email format and the full name format.
        4. It tries to get the user object using the provided email address.
        5. If no user exists or if the user is not a "FOUNDER" and their school is non-compliant, it returns an error.
        6. It checks if the provided name and surname are correct.
        7. If the user's account has already been activated, it returns a 403 Forbidden error.
        8. If the user's email is banned, it returns an alert.
        9. If everything checks out, it creates an OTP for the user and tries to send it to their email address.
        10. If the OTP email is successfully sent, it caches the OTP and returns a successful response.
        11. If there was an error sending the OTP email, it returns a 500 Internal Server Error.

        Note: All exceptions are handled and appropriate HTTP status codes are returned.
    """
    
    # retrieve provided infomation
    try:
        full_names = request.data.get('fullname')
        email = request.data.get('email')

        # if there's a missing credential return an error
        if not full_names or not email:
            return Response({"error": "sign-in credentials are incomplete. please provide all required information"}, status=status.HTTP_400_BAD_REQUEST)
    
        # validate email format
        validate_email(email)

        # validate provided names
        if not validate_names(full_names):
            return Response({"error": "please enter only your first name and surname"}, status=status.HTTP_400_BAD_REQUEST)

        # try to validate the credentials by getting a user with the provided credentials 
        user = BaseUser.objects.get(email=email)

        # Access control based on user role and school compliance
        role_check_mapping = {
            'PRINCIPAL': user.principal.school.none_compliant,
            'ADMIN': user.admin.school.none_compliant,
            'TEACHER': user.teacher.school.none_compliant,
            'STUDENT': user.student.school.none_compliant
        }

        if user.role in role_check_mapping and role_check_mapping[user.role]:
            return Response({"denied": "access denied"}, status=status.HTTP_403_FORBIDDEN)
            
        # check if the provided name and surname are correct
        name, surname = full_names.split(' ', 1)

        if not ((user.name.casefold() == name.casefold() and user.surname.casefold() == surname.casefold()) or (user.name.casefold() == surname.casefold() and user.surname.casefold() == name.casefold())):
            return Response({"error": "the credentials you entered are invalid. please check your full name and email and try again"}, status=status.HTTP_400_BAD_REQUEST)
        
        # if there is a user with the provided credentials check if their account has already been activated 
        if user.activated == True:
            return Response({"error": "your request could not be processed. access has been denied due to invalid or incomplete information"}, status=status.HTTP_403_FORBIDDEN)
        
        # if the users account has'nt been activated yet check if their email address is banned
        if user.email_banned:
            # if their email address is banned return an error and let the user know and how they can appeal( if they even can )
            return Response({"alert" : "your email address has been blacklisted" })
    
        # if everything checks out without an error 
        # create an otp for the user
        otp, hashed_otp, salt = generate_otp()
        email_response = send_otp_email(user, otp, reason="We are pleased to have you trying out our service, this OTP was generated in response to your account activation request..")
        
        if email_response['status'] == 'success':
            cache.set(user.email + 'signin_otp', (hashed_otp, salt), timeout=300)  # 300 seconds = 5 mins
            return Response({"message": "a sign-in OTP has been generated and sent to your email address.. it will be valid for the next 5 minutes",}, status=status.HTTP_200_OK)
        
        else:
            return Response({"error": email_response['message']}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    except BaseUser.DoesNotExist:
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
        email = request.data.get('email')
        new_password = request.data.get('password')

        if not (email or new_password):
            return Response({"error": "missing credentials, all fields are required"}, status=status.HTTP_400_BAD_REQUEST)

        # get authorization otp 
        otp = request.COOKIES.get('signin_authorization_otp')
        hashed_authorization_otp_and_salt = cache.get(email + 'signin_authorization_otp')

        if not (hashed_authorization_otp_and_salt or otp or verify_user_otp(otp, hashed_authorization_otp_and_salt)):
            # if the authorization otp does'nt match the one stored for the user return an error 
            response = Response({"denied": "requests provided authorization OTP is invalid.. process forrbiden"}, status=status.HTTP_400_BAD_REQUEST)
                        
            cache.delete(user.email + 'signin_authorization_otp')
            if otp:
                response.delete_cookie('signin_authorization_otp', domain='.seeran-grades.cloud')
                
            return response
        
        # activate users account
        with transaction.atomic():
            user = BaseUser.objects.activate(email=email, password=new_password)

        response = Response({"message": "account activation successful", "role": user.role.title()}, status=status.HTTP_200_OK)
                
        # generate an access and refresh token for the user 
        token = generate_token(user)
        
        AccessToken.objects.create(user=user, token=token['access'])

        # set access/refresh token cookies
        response.set_cookie('access_token', token['access'], domain='.seeran-grades.cloud', samesite='None', secure=True, httponly=True, max_age=86400)
        
        return response
    
    except BaseUser.DoesNotExist:
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

        child_model_mapping = {
            'FOUNDER' : Founder.objects.get(baseuser_ptr_id=request.user.id),
            'PRINCIPAL': Principal.objects.get(baseuser_ptr_id=request.user.id),
            'ADMIN': Admin.objects.get(baseuser_ptr_id=request.user.id),
            'TEACHER': Teacher.objects.get(baseuser_ptr_id=request.user.id),
            'STUDENT': Student.objects.get(baseuser_ptr_id=request.user.id),
            'PARENT': Parent.objects.get(baseuser_ptr_id=request.user.id),  
        }

        user = child_model_mapping[role]

        if role in ['PRINCIPAL', 'ADMIN', 'TEACHER', 'STUDENT']:
            if user.school.none_compliant:
                return Response({"denied": "access denied"}, status=status.HTTP_403_FORBIDDEN)

        return Response({"role" : request.user.role.title()}, status=status.HTTP_200_OK)

    else:
        return Response({"error" : "request not authenticated.. access denied",}, status=status.HTTP_403_FORBIDDEN)


@api_view(['POST'])
def verify_otp(request):

    try:
        email = request.data.get('email')
        otp = request.data.get('otp')
    
        if not email or not otp:
            return Response({"error": "invalid request.. email and OTP are required."}, status=status.HTTP_400_BAD_REQUEST)
        
        stored_hashed_otp_and_salt = cache.get(email + 'signin_otp')

        if not stored_hashed_otp_and_salt:
            cache.delete(email + 'signin_otp_attempts')
            return Response({"denied": "no sign-in OTP for account on record.. please generate a new one "}, status=status.HTTP_403_FORBIDDEN)

        if verify_user_otp(user_otp=otp, stored_hashed_otp_and_salt=stored_hashed_otp_and_salt):
            
            # OTP is verified, prompt the user to set their password
            cache.delete(email + 'signin_otp')
            
            authorization_otp, hashed_authorization_otp, salt = generate_otp()
            
            response = Response({"message": "OTP verified successfully"}, status=status.HTTP_200_OK)

            cache.set(email + 'signin_authorization_otp', (hashed_authorization_otp, salt), timeout=300)  # 300 seconds = 5 mins
            response.set_cookie('signin_authorization_otp', authorization_otp, domain='.seeran-grades.cloud', samesite='None', secure=True, httponly=True, max_age=300)  # 300 seconds = 5 mins
        
            return response
        
        else:

            attempts = cache.get(email + 'signin_otp_attempts', 3)
            
            # Incorrect OTP, decrement attempts and handle expiration
            attempts -= 1
            
            if attempts <= 0:
                cache.delete(email + 'signin_otp')
                cache.delete(email + 'signin_otp_attempts')
                
                return Response({"denied": "maximum OTP verification attempts exceeded.. generated sign-in OTP for account discarded"}, status=status.HTTP_403_FORBIDDEN)
            
            cache.set(email + 'signin_otp_attempts', attempts, timeout=300)  # Update attempts with expiration

            return Response({"error": f"provided OTP incorrect.. you have {attempts} verification attempts remaining"}, status=status.HTTP_400_BAD_REQUEST)
 
    except Exception as e:
        return {"error": str(e)}


# validate email before password reset
@api_view(['POST'])
@throttle_classes([CustomRateThrottle])
def validate_password_reset(request):
    
    try:
        # check for sent email
        sent_email = request.data.get('email')
        if not sent_email:
            return Response({"error": "request error, no email address provided.. email address is required"}, status=status.HTTP_400_BAD_REQUEST)
        
        # try to get the user with the provided email
        user = BaseUser.objects.get(email=sent_email)

        # Access control based on user role and school compliance
        role_check_mapping = {
            'PRINCIPAL': user.principal.school.none_compliant,
            'ADMIN': user.admin.school.none_compliant,
            'TEACHER': user.teacher.school.none_compliant,
            'STUDENT': user.student.school.none_compliant
        }

        if user.role in role_check_mapping and role_check_mapping[user.role]:
            return Response({"denied": "access denied"}, status=status.HTTP_403_FORBIDDEN)
            
        # check if the account is activated 
        if user.activated == False:
            return Response({"error": "action forbidden for account with provided credentials"}, status=status.HTTP_403_FORBIDDEN)
        
        # check if the email is banned 
        if user.email_banned:
            return Response({ "error" : "your email address has been banned, failed to send OTP.. you can visit your school to have it changed"}, status=status.HTTP_400_BAD_REQUEST)
        
        # validate email format
        validate_email(sent_email)
        
        # if everything checks out without an error 
        # create an otp for the user
        otp, hashed_otp, salt = generate_otp()
        email_response = send_otp_email(user, otp, reason="We recieved a password reset request for your account, this OTP was generated in response to your password reset request..")
        
        if email_response['status'] == 'success':
            cache.set(user.email + 'password_reset_otp', (hashed_otp, salt), timeout=300)  # 300 seconds = 5 mins
            return Response({"message": "a password reset OTP has been generated and sent to your email address.. it will be valid for the next 5 minutes",}, status=status.HTTP_200_OK)
        
        else:
            return Response({"error": email_response['message']}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    except BaseUser.DoesNotExist:
        # if theres no user with the provided email return an error
        return Response({"error": "an account with the provided credentials does not exist. please check the account details and try again"}, status=status.HTTP_404_NOT_FOUND)
            
    except ValidationError:
        return Response({"error": "the provided email address is not in a valid format. please correct the email address and try again"}, status=status.HTTP_400_BAD_REQUEST)

    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
def password_reset_otp_verification(request):
    
    try:
        email = request.data.get('email')
        otp = request.data.get('otp')
    
        if not email or not otp:
            return Response({"error": "email and OTP are required."}, status=status.HTTP_400_BAD_REQUEST)
    
        stored_hashed_otp_and_salt = cache.get(email + 'password_reset_otp')
        if not stored_hashed_otp_and_salt:
            return Response({"denied": "no password reset OTP for account on record.. please generate a new one"}, status=status.HTTP_400_BAD_REQUEST)
    
        if verify_user_otp(user_otp=otp, stored_hashed_otp_and_salt=stored_hashed_otp_and_salt):
            
            cache.delete(email + 'password_reset_otp')
            authorization_otp, hashed_authorization_otp, salt = generate_otp()

            response = Response({"message": "OTP verified successfully"}, status=status.HTTP_200_OK)

            cache.set(email + 'password_reset_authorization_otp', (hashed_authorization_otp, salt), timeout=300)  # 300 seconds = 5 mins
            response.set_cookie('password_reset_authorization_otp', authorization_otp, domain='.seeran-grades.cloud', samesite='None', secure=True, httponly=True, max_age=300)  # 300 seconds = 5 mins
            response.set_cookie('email', email, domain='.seeran-grades.cloud', samesite='None', secure=True, httponly=True, max_age=300)  # 300 seconds = 5 mins

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
        new_password = request.data.get('new_password')
        email = request.COOKIES.get('email')
        
        if not (new_password or otp or email):
            return Response({"error": "invalid request.. missing credentials"}, status=status.HTTP_400_BAD_REQUEST)    
    
        user = BaseUser.objects.get(email=email)
        
        # get authorization otp from cache and verify provided otp
        hashed_authorization_otp_and_salt = cache.get(user.email + 'password_reset_authorization_otp')
        if not hashed_authorization_otp_and_salt:
            return Response({"denied": "no password reset authorization OTP for account on record.. process forrbiden"}, status=status.HTTP_403_FORBIDDEN)
        
        if verify_user_otp(user_otp=otp, stored_hashed_otp_and_salt=hashed_authorization_otp_and_salt):
            response = Response({"denied": "requests provided authorization OTP is invalid.. process forrbiden"}, status=status.HTTP_403_FORBIDDEN)
        
        validate_password(new_password)

        # update the user's password
        user.set_password(new_password)
        user.save()
    
        response = Response({"message": "your accounts password has been changed successfully.. you can now login with your new credentials"}, status=200)
   
        return response
    
    except BaseUser.DoesNotExist:
        # if theres no user with the provided email return an error
        return Response({"denied": "an account with the provided credentials does not exist. please check the account details and try again"}, status=status.HTTP_404_NOT_FOUND)

    except Exception as e:
        return Response({"error": {str(e)}}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# Request otp view
@api_view(['POST'])
def resend_otp(request):
    
    # try to get the user
    try:
    
        email = request.data.get('email')
    
        if not email:
            return Response({"error" : "an email is required"}, status=status.HTTP_400_BAD_REQUEST)

        user = BaseUser.objects.get(email=email)
     
        if user.email_banned:
            return Response({ "error" : "your email address has been banned, failed to send OTP"})
        
        # otp, hashed_otp = generate_otp()
    
        # Send the OTP via email
        # cache.set(user.email, hashed_otp, timeout=300)  # 300 seconds = 5 mins
        return Response({"message": "OTP created and sent to your email"}, status=status.HTTP_200_OK)
    
        # else:
        #     return Response({"error": "failed to send OTP via email"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
      
    except BaseUser.DoesNotExist:
        # if theres no user with the provided email return an error
        return Response({"denied": "an account with the provided credentials does not exist. please check the account details and try again"}, status=status.HTTP_404_NOT_FOUND)

    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

