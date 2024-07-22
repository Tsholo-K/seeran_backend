# python
from datetime import timedelta
from decouple import config
import requests
import base64

# rest framework
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.exceptions import AuthenticationFailed
from rest_framework import status
from rest_framework_simplejwt.tokens import AccessToken as decode
from .serializers import CustomTokenObtainPairSerializer

# django
from django.core.exceptions import ObjectDoesNotExist
from django.core.cache import cache
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

# models
from users.models import CustomUser
from auth_tokens.models import AccessToken

# utility functions 
from .utils import validate_access_token, generate_access_token, generate_token, generate_otp, verify_user_otp, validate_user_email, validate_names

# custom decorators
from .decorators import token_required


####################################################### login and authentication views #############################################


@api_view(['POST'])
def login(request):

    """
        This view handles the login process. It expects a POST request with user credentials.

        Steps:
        1. It tries to authenticate the incoming credentials using the `CustomTokenObtainPairSerializer`.
        2. If authentication fails, it returns a 401 Unauthorized error.
        3. If some other exception occurs during authentication, it returns a 500 Internal Server Error.
        4. After successful authentication, it tries to get the user object from the database using the provided email.
        5. If the user doesn't exist or if the user is not a "FOUNDER" and their school is non-compliant, it returns an error.
        6. If the user's multi-factor authentication is enabled:
            - If the user's email has recently been banned, it disables multi-factor authentication and logs them in without it.
            - If the user's email is not banned, it generates an OTP and tries to send it to the user's email address.
            - If the OTP email is successfully sent, it caches the hashed OTP against the user's email address for 5 minutes.
            - If there was an error sending the OTP email, it returns a 500 Internal Server Error.
        7. If the user's multi-factor authentication is disabled, it logs the user in and sets the access and refresh token cookies.

        Note: All exceptions are handled and appropriate HTTP status codes are returned.
    """
    
    # try to authenticate the incoming credentials
    try:
        serializer = CustomTokenObtainPairSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        token = serializer.validated_data
        
    
        # after successful authentication try to get the user object from the database
        user = CustomUser.objects.get(email=request.data.get('email'))
        
        if user.role not in  ["FOUNDER", "PARENT"]:
            if user.school.none_compliant:
                return Response({"denied": "access denied"}, status=status.HTTP_403_FORBIDDEN)
     
        # if users multi-factor authentication is enabled do this..
        if user.multifactor_authentication:
        
            # if the users email has recently been banned, disable multi-factor authentication 
            # because mfa requires we send an otp to the users email
            # then log them in without multi-factor authentication 
            if user.email_banned:
            
                # disable mfa
                user.multifactor_authentication = False
                user.save()
            
                if 'refresh' in token:
                    # Calculate cutoff time for expired tokens
                    cutoff_time = timezone.now() - timedelta(hours=24)
                
                    with transaction.atomic():
                        # Delete all RefreshToken objects for the user that were created before the cutoff_time
                        AccessToken.objects.filter(user=user, created_at__lt=cutoff_time).delete()

                        # Count the remaining RefreshToken objects for the user
                        refresh_tokens_count = AccessToken.objects.filter(user=user).count()
                    
                    if refresh_tokens_count >= 3:
                        return Response({"error": "maximum number of connected devices reached"}, status=status.HTTP_403_FORBIDDEN)
                    
                    # the alert key is used on the frontend to alert the user of their email being banned and what they can do to appeal(if they can)
                    # the alert key is used on the frontend to alert the user of their email being banned and what they can do to appeal(if they can)
                    response = Response({"message": "login successful", "alert" : "your email address has been blacklisted", "role" : user.role.title()}, status=status.HTTP_200_OK)
        
                    access_token = token['access']
                    AccessToken.objects.create(user=user, token=access_token)
                
                    # set access token cookie with custom expiration (5 mins)
                    response.set_cookie('access_token', token['access'], domain='.seeran-grades.cloud', samesite='None', secure=True, httponly=True, max_age=86400)
                
                else:
                    response = Response({"error": "couldn't generating authentication token"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                
                return response
        
            # else if their email address is not banned generate an otp for the user
            otp, hashed_otp, salt = generate_otp()
        
            # then try to send the OTP to their email address
            # Define your Mailgun API URL
            mailgun_api_url = "https://api.eu.mailgun.net/v3/" + config('MAILGUN_DOMAIN') + "/messages"

            # Define your email data
            email_data = {
                "from": "seeran grades <authorization@" + config('MAILGUN_DOMAIN') + ">",
                "to": user.surname.title() + " " + user.name.title() + "<" + user.email + ">",
                "subject": "One Time Passcode",
                "template": "one-time passcode",
                "v:onetimecode": otp,
                "v:otpcodereason": "Your account has mutil-factor authentication toggled on, this OTP was generated in response to your login request.."
            }

            # Define your headers
            headers = {
                "Authorization": "Basic " + base64.b64encode(f"api:{config('MAILGUN_API_KEY')}".encode()).decode(),
                "Content-Type": "application/x-www-form-urlencoded"
            }

            # Send the email via Mailgun
            response = requests.post(
                mailgun_api_url,
                headers=headers,
                data=email_data
            )

            if response.status_code == 200:
                    
                # if the email was successfully delivered cache the hashed otp against the users 'email' address for 5 mins( 300 seconds)
                # this is cached to our redis database for faster retrieval when we verify the otp
                cache.set(user.email, (hashed_otp, salt), timeout=300)  # 300 seconds = 5 mins
                
                # then generate another authorization otp for the request
                # this is saved in the cookies of the the request( it will be needed when the user verifyies the otp )
                authorization_otp, hashed_authorization_otp, authorization_otp_salt = generate_otp()
                
                # cache the authorization otp under the users 'email+"authorization_otp"'
                cache.set(user.email+'authorization_otp', (hashed_authorization_otp, authorization_otp_salt), timeout=300)  # 300 seconds = 5 mins
                
                response = Response({"multifactor_authentication": "a new OTP has been sent to your email address"}, status=status.HTTP_200_OK)
            
                # set the authorization cookie then return the response
                response.set_cookie('authorization_otp', authorization_otp, domain='.seeran-grades.cloud', samesite='None', secure=True, httponly=True, max_age=300)  # 300 seconds = 5 mins
                
                return response
                
            else:
                # if there was an error sending the email respond accordingly
                # this will kick off our sns service and their email will get banned 
                # regardless of wether it was a soft of hard bounce
                return Response({"error": "failed to send OTP to your  email address"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        if 'access' in token:
            # Calculate cutoff time for expired tokens
            cutoff_time = timezone.now() - timedelta(hours=24)
            
            with transaction.atomic():
                # Delete all RefreshToken objects for the user that were created before the cutoff_time
                AccessToken.objects.filter(user=user, created_at__lt=cutoff_time).delete()

                # Count the remaining RefreshToken objects for the user
                refresh_tokens_count = AccessToken.objects.filter(user=user).count()
            
            if refresh_tokens_count >= 3:
                return Response({"error": "maximum number of connected devices reached"}, status=status.HTTP_403_FORBIDDEN)
            
            # if users multi-factor authentication is disabled do this..
            response = Response({"message": "login successful", "role" : user.role.title()}, status=status.HTTP_200_OK)
 
            access_token = token['access']
            AccessToken.objects.create(user=user, token=access_token)
        
            # set access token cookie with custom expiration (5 mins)
            response.set_cookie('access_token', token['access'], domain='.seeran-grades.cloud', samesite='None', secure=True, httponly=True, max_age=86400)
        
        else:
            response = Response({"error": "could not generating access token"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return response
    
    except ObjectDoesNotExist:
        # if the user doesnt exist return an error
        # this far through the view this should be impossible but to stay on the safe side we'll handle the error 
        return Response({"error": "invalid credentials"}, status=status.HTTP_404_NOT_FOUND)   
    
    except AuthenticationFailed:
        # if authentication fails respond accordingly
        return Response({"error": "invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)
        
    # if any exception occurs during the proccess return an error
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
def multi_factor_authentication_login(request):

    """
        This view handles the multi-factor authentication (MFA) process. It expects a POST request with the user's email and OTP.

        Steps:
        1. It retrieves the provided email, OTP, and the authorization OTP from the cookie.
        2. If any of these are missing, it returns a 400 Bad Request error.
        3. It tries to get the user object using the provided email address.
        4. If no user exists, it returns an error.
        5. After getting the user object, it retrieves the stored OTP from the cache.
        6. If there's no OTP in the cache, it returns a 400 Bad Request error.
        7. If any other exception occurs while retrieving the OTP from the cache, it returns a 500 Internal Server Error.
        8. If everything checks out, it verifies the provided OTP against the stored OTP.
        9. If the provided OTP is verified successfully, it verifies the authorization OTP in the request's cookies.
        10. If the authorization OTP doesn't match the one stored for the user, it returns a 400 Bad Request error.
        11. If there's no error until here, verification is successful. It deletes all cached OTPs and generates an access and refresh token for the user.
        12. It then sets the access/refresh token cookies and returns a successful response.

        Note: All exceptions are handled and appropriate HTTP status codes are returned.
    """
    
    # retrieve the provided email, otp and the authorization otp in the cookie
    email = request.data.get('email')
    otp = request.data.get('otp')
    authorization_cookie_otp = request.COOKIES.get('authorization_otp')
    
    # if anyone of these is missing return a 400 error
    if not email or not otp or not authorization_cookie_otp:
        return Response({"error": "missing credentials"}, status=status.HTTP_400_BAD_REQUEST)
    
    # try to get the user object using the provided email address
    try:
        
        user = CustomUser.objects.get(email=email)
    
        # after getting the user object retrieve the stored otp from cache 
        stored_hashed_otp_and_salt = cache.get(user.email)
        
        # try to get the the authorization otp from cache
        hashed_authorization_otp_and_salt = cache.get(user.email + 'authorization_otp')
        
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
                cache.delete(user.email)
                cache.delete(user.email + 'authorization_otp')

                response.delete_cookie('authorization_otp', domain='.seeran-grades.cloud')
                return response
            
            # if there's no error till here verification is successful, delete all cached otps
            cache.delete(user.email)
            cache.delete(user.email + 'authorization_otp')
            
            # then generate an access and refresh token for the user 
            token = generate_token(user)
            
            if 'access' in token:
                # Calculate cutoff time for expired tokens
                cutoff_time = timezone.now() - timedelta(hours=24)
            
                with transaction.atomic():
                    # Delete all RefreshToken objects for the user that were created before the cutoff_time
                    AccessToken.objects.filter(user=user, created_at__lt=cutoff_time).delete()

                    # Count the remaining RefreshToken objects for the user
                    refresh_tokens_count = AccessToken.objects.filter(user=user).count()
                
                if refresh_tokens_count >= 3:
                    return Response({"error": "maximum number of connected devices reached"}, status=status.HTTP_403_FORBIDDEN)
                
                # if users multi-factor authentication is disabled do this..
                response = Response({"message": "login successful", "role" : user.role.title()}, status=status.HTTP_200_OK)
    
                AccessToken.objects.create(user=user, token=token['access'])
            
                # set access token cookie with custom expiration (5 mins)
                response.set_cookie('access_token', token['access'], domain='.seeran-grades.cloud', samesite='None', secure=True, httponly=True, max_age=86400)
            
            else:
                response = Response({"error": "couldn't generating authentication tokens"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            return response
        
        attempts = cache.get(email + 'attempts', 3)
        
        if attempts <= 0:
            cache.delete(email)
            cache.delete(email + 'attempts')
            return Response({"denied": "maximum OTP verification attempts exceeded.."}, status=status.HTTP_400_BAD_REQUEST)
        
        # Incorrect OTP, decrement attempts and handle expiration
        attempts -= 1
        cache.set(email + 'attempts', attempts, timeout=300)  # Update attempts with expiration

        return Response({"error": f"incorrect OTP.. {attempts} remaining"}, status=status.HTTP_400_BAD_REQUEST)
    
    except ObjectDoesNotExist:
        # if no user exists return an error 
        return Response({"error": "invalid credentials"}, status=status.HTTP_404_NOT_FOUND)

    except Exception as e:
        # if any exceptions rise during return the response return it as the response
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
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
            return Response({"error": "missing credentials"}, status=status.HTTP_400_BAD_REQUEST)
    
        # validate email format
        validate_email(email)

        # validate provided names
        if not validate_names(full_names):
            return Response({"error": "only provide your first name and surname"}, status=status.HTTP_400_BAD_REQUEST)

        # try to validate the credentials by getting a user with the provided credentials 
        user = CustomUser.objects.get(email=email)

        if user.role not in ["FOUNDER", "PARENT"]:
            if user.school.none_compliant:
                return Response({"denied": "access denied"}, status=status.HTTP_403_FORBIDDEN)
                
        # check if the provided name and surname are correct
        name, surname = full_names.split(' ', 1)

        if not ((user.name.casefold() == name.casefold() and user.surname.casefold() == surname.casefold()) or (user.name.casefold() == surname.casefold() and user.surname.casefold() == name.casefold())):
            return Response({"error": "provided credentials are invalid"}, status=status.HTTP_400_BAD_REQUEST)
        
        # if there is a user with the provided credentials check if their account has already been activated 
        if user.activated == True:
            return Response({"error": "invalid request, access denied"}, status=status.HTTP_403_FORBIDDEN)
        
        # if the users account has'nt been activated yet check if their email address is banned
        if user.email_banned:
            # if their email address is banned return an error and let the user know and how they can appeal( if they even can )
            return Response({"alert" : "your email address has been blacklisted" })
    
        # if everything checks out without an error 
        # create an otp for the user
        otp, hashed_otp, salt = generate_otp()

        # Define your Mailgun API URL
        mailgun_api_url = "https://api.eu.mailgun.net/v3/" + config('MAILGUN_DOMAIN') + "/messages"

        # Define your email data
        email_data = {
            "from": "seeran grades <authorization@" + config('MAILGUN_DOMAIN') + ">",
            "to": user.surname.title() + " " + user.name.title() + "<" + user.email + ">",
            "subject": "One Time Passcode",
            "template": "one-time passcode",
            "v:onetimecode": otp,
            "v:otpcodereason": "We are pleased to have you trying out our service, this OTP was generated in response to your account activation request.."
        }

        # Define your headers
        headers = {
            "Authorization": "Basic " + base64.b64encode(f"api:{config('MAILGUN_API_KEY')}".encode()).decode(),
            "Content-Type": "application/x-www-form-urlencoded"
        }

        # Send the email via Mailgun
        response = requests.post(
            mailgun_api_url,
            headers=headers,
            data=email_data
        )

        if response.status_code == 200:

            # if the email was successfully sent cache the otp then return the response
            cache.set(user.email + 'signin_otp', (hashed_otp, salt), timeout=300)  # 300 seconds = 5 mins
            return Response({"message": "a sign-in OTP has been generated and sent to your email address.. it will be valid for the next 5 minutes",}, status=status.HTTP_200_OK)
        
        # if there was an error sending the email respond accordingly
        if response.status_code in [ 400, 401, 402, 403, 404 ]:
            return {"error": f"there was an error sending sign-in OTP to your email address.. please open a new bug ticket with the issue. error code {response.status_code}"}
        
        if response.status_code == 429:
            return {"error": f"there was an error sending sign-in OTP to your email address.. please try again in a few moments"}

        else:
            return {"error": "there was an error sending sign-in OTP to your email address.."}
    
    except ObjectDoesNotExist:
        # if there's no user with the provided credentials return an error 
        return Response({"error": "account with the provided credentials does not exist"}, status=status.HTTP_404_NOT_FOUND)
    
    except ValidationError:
        return Response({"error": "invalid email format.. request revoked"}, status=status.HTTP_400_BAD_REQUEST)
    
    except ValueError:
        return Response({"error": "please enter your first name followed by your surname or vice verca"}, status=status.HTTP_400_BAD_REQUEST)

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
            user = CustomUser.objects.activate_user(email=email, password=new_password)

        response = Response({"message": "account activation successful", "role": user.role.title()}, status=status.HTTP_200_OK)
                
        # generate an access and refresh token for the user 
        token = generate_token(user)
        
        AccessToken.objects.create(user=user, token=token['access'])

        # set access/refresh token cookies
        response.set_cookie('access_token', token['access'], domain='.seeran-grades.cloud', samesite='None', secure=True, httponly=True, max_age=86400)
        
        return response
    
    except ObjectDoesNotExist:
        # if theres no user with the provided email return an error
        return Response({"denied": "user with the provided credentials does not exist."}, status=status.HTTP_404_NOT_FOUND)
  
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
        return Response({"role" : request.user.role.title()}, status=status.HTTP_200_OK)

    else:
        return Response({"error" : "request not authenticated.. access denied",}, status=status.HTTP_403_FORBIDDEN)


####################################################################################################################################

##################################################### validation and verification views ############################################


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
def validate_password_reset(request):
    
    try:
        # check for sent email
        sent_email = request.data.get('email')
        if not sent_email:
            return Response({"error": "request error, no email address provided.. email address is required"}, status=status.HTTP_400_BAD_REQUEST)
        
        # try to get the user with the provided email
        user = CustomUser.objects.get(email=sent_email)

        if user.role != "FOUNDER":
            if user.school.none_compliant:
                return Response({"denied": "access denied"}, status=status.HTTP_400_BAD_REQUEST)
    
        # check if the account is activated 
        if user.activated == False:
            return Response({"error": "action forbidden for account with provided credentials"}, status=status.HTTP_403_FORBIDDEN)
        
        # check if the email is banned 
        if user.email_banned:
            return Response({ "error" : "your email address has been banned, failed to send OTP.. you can visit your school to have it changed"}, status=status.HTTP_400_BAD_REQUEST)
        
        # Validate the email
        if not validate_user_email(sent_email):
            return Response({"error": "provided email address is invalid"}, status=status.HTTP_400_BAD_REQUEST)
        
        # if everything checks out without an error 
        # create an otp for the user
        otp, hashed_otp, salt = generate_otp()

        # Define your Mailgun API URL
        mailgun_api_url = "https://api.eu.mailgun.net/v3/" + config('MAILGUN_DOMAIN') + "/messages"

        # Define your email data
        email_data = {
            "from": "seeran grades <authorization@" + config('MAILGUN_DOMAIN') + ">",
            "to": user.surname.title() + " " + user.name.title() + "<" + user.email + ">",
            "subject": "One Time Passcode",
            "template": "one-time passcode",
            "v:onetimecode": otp,
            "v:otpcodereason": "we recieved a password reset request for your account, this OTP was generated in response to your password reset request.."
        }

        # Define your headers
        headers = {
            "Authorization": "Basic " + base64.b64encode(f"api:{config('MAILGUN_API_KEY')}".encode()).decode(),
            "Content-Type": "application/x-www-form-urlencoded"
        }

        # Send the email via Mailgun
        response = requests.post(mailgun_api_url, headers=headers, data=email_data)

        if response.status_code == 200:

            # if the email was successfully sent cache the otp then return the response
            cache.set(user.email + 'password_reset_otp', (hashed_otp, salt), timeout=300)  # 300 seconds = 5 mins
            return Response({"message": "a password reset OTP has been generated and sent to your email address.. it will be valid for the next 5 minutes",}, status=status.HTTP_200_OK)
        
        # if there was an error sending the email respond accordingly
        if response.status_code in [ 400, 401, 402, 403, 404 ]:
            return {"error": f"there was an error sending password reset OTP to your email address.. please open a new bug ticket with the issue. error code {response.status_code}"}
        
        if response.status_code == 429:
            return {"error": f"there was an error sending password reset OTP to your email address.. please try again in a few moments"}

        else:
            return {"error": "there was an error sending password reset OTP to your email address.."}
       
    except CustomUser.DoesNotExist:
        return { 'error': 'user with the provided credentials does not exist' }
        
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


####################################################################################################################################


####################################################### password reset views #######################################################
 

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
    
        user = CustomUser.objects.get(email=email)
        
        # get authorization otp from cache and verify provided otp
        hashed_authorization_otp_and_salt = cache.get(user.email + 'password_reset_authorization_otp')
        if not hashed_authorization_otp_and_salt:
            return Response({"denied": "no password reset authorization OTP for account on record.. process forrbiden"}, status=status.HTTP_403_FORBIDDEN)
        
        if verify_user_otp(user_otp=otp, stored_hashed_otp_and_salt=hashed_authorization_otp_and_salt):
            response = Response({"denied": "requests provided authorization OTP is invalid.. process forrbiden"}, status=status.HTTP_403_FORBIDDEN)
        
        # update the user's password
        user.set_password(new_password)
        user.save()
    
        response = Response({"message": "your accounts password has been changed successfully.. you can now login with your new credentials"}, status=200)
   
        return response
    
    except ObjectDoesNotExist:
        return Response({"error": "an account with the provided credentials does not exist"})

    except Exception as e:
        return Response({"error": {str(e)}}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# Request otp view
@api_view(['POST'])
def resend_otp(request):
 
    email = request.data.get('email')
  
    if not email:
        return Response({"error" : "an email is required"}, status=status.HTTP_400_BAD_REQUEST)
    
    # try to get the user
    try:
        user = CustomUser.objects.get(email=email)
 
    except CustomUser.DoesNotExist:
        return Response({"error": "user with this email does not exist."}, status=status.HTTP_400_BAD_REQUEST)
    
    if user.email_banned:
        return Response({ "error" : "your email address has been banned, failed to send OTP"})
    
    # otp, hashed_otp = generate_otp()
  
    # Send the OTP via email
    try:
            # cache.set(user.email, hashed_otp, timeout=300)  # 300 seconds = 5 mins
            return Response({"message": "OTP created and sent to your email"}, status=status.HTTP_200_OK)
    
        # else:
        #     return Response({"error": "failed to send OTP via email"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
  
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


####################################################################################################################################
