# python
import json
import random

# rest framework
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.exceptions import AuthenticationFailed
from rest_framework import status
from rest_framework_simplejwt.tokens import AccessToken
from .serializers import CustomTokenObtainPairSerializer

# django
from django.contrib.auth.hashers import check_password
from django.core.mail import BadHeaderError
from django.core.exceptions import ObjectDoesNotExist
from django.core.cache import cache
from django.views.decorators.csrf import csrf_exempt

# models
from email_bans.models import EmailBan
from users.models import CustomUser

# amazon email sending service
import boto3
from botocore.exceptions import BotoCoreError, ClientError

# utility functions 
from .utils import validate_access_token, generate_access_token, generate_token, generate_otp, verify_user_otp, validate_user_email, validate_names

# custom decorators
from .decorators import token_required



### login and authentication views ###


# user login
@api_view(['POST'])
def login(request):
    
    # try to authenticate the incoming credentials
    try:
        serializer = CustomTokenObtainPairSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        token = serializer.validated_data
        
    except AuthenticationFailed:
        # if authentication fails respond accordingly
        return Response({"error": "invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)
    
    except Exception as e:
        # else if some other exception occurs, return it as a response
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    # after successful authentication try to get the user object from the database
    try:
        user = CustomUser.objects.get(email=request.data.get('email'))
        if not user.role == "FOUNDER":
            if user.school.none_compliant:
                return Response({"denied": "access denied"})
            
    except ObjectDoesNotExist:
        # if the user doesnt exist return an error
        # this far through the view this should be impossible but to stay on the safe side we'll handle the error 
        return Response({"error": "invalid credentials/tokens"})   
     
    # if users multi-factor authentication is enabled do this..
    if user.multifactor_authentication:
        # if the users email has recently been banned, disable multi-factor authentication 
        # because mfa requires we send an otp to the users email
        # then log them in without multi-factor authentication 
        if user.email_banned:
            # disable mfa
            user.multifactor_authentication = False
            user.save()
            try:    
                # generate a random 6-digit number that will act as an invalidtor fro cached data on the frontend
                random_number = random.randint(100000, 999999)
                # the alert key is used on the frontend to alert the user of their email being banned and what they can do to appeal(if they can)
                response = Response({"message": "login successful", "role": user.role, "alert" : "your email address has been blacklisted", "invalidator" : random_number}, status=status.HTTP_200_OK)
                # set access token cookie with custom expiration (5 mins)
                response.set_cookie('access_token', token['access'], domain='.seeran-grades.com', samesite='None', secure=True, httponly=True, max_age=300)
                if 'refresh' in token:
                    # set refresh token cookie with custom expiration (86400 seconds = 24 hours)
                    response.set_cookie('refresh_token', token['refresh'], domain='.seeran-grades.com', samesite='None', secure=True, httponly=True, max_age=86400)
                return response
            except Exception as e:
                # if an exception occurs during the entire proccess return an error
                return Response({"error": f"there was an error logging you in"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        # else if their email address is not banned generate an otp for the user
        otp, hashed_otp, salt = generate_otp()
        # then try to send the OTP to their email address 
        try:
            client = boto3.client('ses', region_name='af-south-1')  # AWS region
            # Read the email template from a file
            with open('authentication/templates/authentication/emailotptemplate.html', 'r') as file:
                email_body = file.read()
            # Replace the {{otp}} placeholder with the actual OTP
            email_body = email_body.replace('{{otp}}', otp)
            response = client.send_email(
                Destination={
                    'ToAddresses': [user.email], # send to users email address
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
                # if the email was successfully delivered cache the hashed otp against the users 'email' address for 5 mins( 300 seconds)
                # this is cached to our redis database for faster retrieval when we verify the otp
                cache.set(user.email, (hashed_otp, salt), timeout=300)  # 300 seconds = 5 mins
                
                # then generate another authorization otp for the request
                # this is saved in the cookies of the the request( it will be needed when the user verifyies the otp )
                authorization_otp, hashed_authorization_otp, authorization_otp_salt = generate_otp()
                
                # cache the authorization otp under the users 'email+"authorization_otp"'
                cache.set(user.email+'authorization_otp', (hashed_authorization_otp, authorization_otp_salt), timeout=300)  # 300 seconds = 5 mins
                
                response = Response({"message": "a new OTP has been sent to your email address"}, status=status.HTTP_200_OK)
                # set the authorization cookie then return the response
                response.set_cookie('authorization_otp', authorization_otp, domain='.seeran-grades.com', samesite='None', secure=True, httponly=True, max_age=300)  # 300 seconds = 5 mins
                
                return response
            
            else:
                # if there was an error sending the email respond accordingly
                # this will kick off our sns service and their email will get banned 
                # regardless of wether it was a soft of hard bounce
                return Response({"error": "failed to send OTP to your  email address"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        # Handle any other specific errors and return appropriate responses
        except (BotoCoreError, ClientError) as error:
            return Response({"error": f"email not sent: {error}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        except BadHeaderError:
            return Response({"error": "invalid header found."}, status=status.HTTP_400_BAD_REQUEST)
        
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        
    # if users multi-factor authentication is disabled do this..
    try:
        
        # generate a section random numbers 
        # this will be the cache invalidators on the frontend
        if user.role == "FOUNDER":
            profile_section = random.randint(100000, 999999)
            schools_section = random.randint(100000, 999999)
            bug_reports_section = random.randint(100000, 999999)
            email_ban_appeal_section = random.randint(100000, 999999)
            response = Response({"message": "login successful", "role": user.role, "profile_section" : profile_section, "schools_section" : schools_section, "bug_reports_section" : bug_reports_section, "email_ban_appeal_section" : email_ban_appeal_section}, status=status.HTTP_200_OK)
        else: # user.role == "PRINCIPAL" or  user.role == "ADMIN"
            profile_section = random.randint(100000, 999999)
            response = Response({"message": "login successful", "role": user.role, "profile_section" : profile_section}, status=status.HTTP_200_OK)

        # set access token cookie with custom expiration (5 mins)
        response.set_cookie('access_token', token['access'], domain='.seeran-grades.com', samesite='None', secure=True, httponly=True, max_age=300)
        if 'refresh' in token:
            # set refresh token cookie with custom expiration (86400 seconds = 24 hours)
            response.set_cookie('refresh_token', token['refresh'], domain='.seeran-grades.com', samesite='None', secure=True, httponly=True, max_age=86400)

        return response
    
    # if any exception occurs during the proccess return an error
    except Exception as e:
        return Response({"error": f"there was an error logging you in"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# user multi-factor login
# when a user has mfa enabled this view verifies their otp
@api_view(['POST'])
def multi_factor_authentication(request):
    
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
        
    except ObjectDoesNotExist:
        # if no user exists return an error 
        return Response({"error": "invalid credentials"})
    
    # after getting the user object retrieve the stored otp from cache 
    try:
        stored_hashed_otp = cache.get(user.email)
        if not stored_hashed_otp:
            # if there's no otp in cache( wasn't provided in the first place, or expired since it has a 5 minute lifespan )
            # return an error 
            return Response({"error": "OTP expired. Please generate a new one"}, status=status.HTTP_400_BAD_REQUEST)
    
    # if any other exception rises while retirieving the otp from cache return an error 
    except Exception as e:
        return Response({"error": {str(e)}}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    # if everything above checks out verify the provided otp against the stored otp
    if verify_user_otp(user_otp=otp, stored_hashed_otp=stored_hashed_otp):
        # provided otp is verified successfully 
        # next we verify the authorization otp in the requests cookies
        # try to get the the suthorization otp from cache
        try:
            hashed_authorization_otp = cache.get(user.email + 'authorization_otp')
            if not hashed_authorization_otp:
                # if there's no authorization otp in cache( wasn't provided in the first place, or expired since it also has a 5 minute lifespan )
                # return an error 
                return Response({"error": "OTP expired, please reload the page to request a new OTP"}, status=status.HTTP_400_BAD_REQUEST)
        
        except Exception as e:
            # handle any other error that might occur during the retrieval of the otp
            return Response({"error": {str(e)}}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        if not verify_user_otp(authorization_cookie_otp, hashed_authorization_otp):
            # if the authorization otp does'nt match the one stored for the user return an error 
            return Response({"error": "incorrect authorization OTP, action forrbiden"}, status=status.HTTP_400_BAD_REQUEST)
        
        # if there's no error till here verification is successful
        # delete all cached otps
        cache.delete(user.email)
        cache.delete(user.email + 'authorization_otp')
        
        # then generate an access and refresh token for the user 
        token = generate_token(user)
        
        try:    
            # Generate a random 6-digit number
            # this will be the cache invalidator on the frontend
            random_number = random.randint(100000, 999999)
            
            response = Response({"message": "login successful, welcome back.", "role": user.role, "invalidator" : random_number}, status=status.HTTP_200_OK)
            # set access/refresh token cookies
            response.set_cookie('access_token', token['access_token'], domain='.seeran-grades.com', samesite='None', secure=True, httponly=True, max_age=300)
            response.set_cookie('refresh_token', token['refresh_token'], domain='.seeran-grades.com', samesite='None', secure=True, httponly=True, max_age=86400)

            return response
        
        except Exception as e:
            # if any exceptions rise during return the response return it as the response
            return Response({"error": f"error logging you in: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    else:
        # if the provided otp is invalid return an appropriate response 
        return Response({"error": "incorrect OTP. Please try again."}, status=status.HTTP_400_BAD_REQUEST)


# account search
# this is used for first time account activation
# the first api the user comes in contact with
@api_view(['POST'])
def signin(request):
    
    # retrieve provided infomation
    full_names = request.data.get('fullname')
    email = request.data.get('email')

    # if there's a missing credential return an error
    if not full_names or not email:
        return Response({"error": "missing credentials"})
    
    if not validate_names(full_names):
        return Response({"error": "only provide your first name and surname"})

    # try to validate the credentials by getting a user with the provided credentials 
    try:
        user = CustomUser.objects.get(email=email)
        if not user.role == "FOUNDER":
            if user.school.none_compliant:
                return Response({"denied": "access denied"})
                
    except ObjectDoesNotExist:
        # if there's no user with the provided credentials return an error 
        return Response({"error": "invalid credentials"})
    
    # check if the provided name and surname can be split into exactly two parts
    name, surname = full_names.split(' ')

    # check if the provided name and surname are correct
    if not user.name == name and user.surname == surname or not user.name == surname and user.surname == name:
        return Response({"error": "invalid credentials"})

    # if there is a user with the provided credentials check if their account has already been activated 
    # if it has been indeed activated return an error 
    if user.activated == True:
        return Response({"error": "account already activated"}, status=403)
    
    # if the users account has'nt been activated yet check if their email address is banned
    if user.email_banned:
        # if their email address is banned return an error and let the user know and how they can appeal( if they even can )
        return Response({ "error" : "your email has been banned", "alert" : "your email address has been blacklisted" })
   
    # if everything checks out without an error 
    # create an otp for the user
    otp, hashed_otp, salt = generate_otp()
    
    # try to send the otp to thier email address
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
            
            # if the email was successfully sent cache the otp then return the response
            cache.set(user.email, (hashed_otp, salt), timeout=300)  # 300 seconds = 5 mins
            return Response({"message": "OTP created and sent to your email", "email" : user.email}, status=status.HTTP_200_OK)
        
        else:

            # if there was an error sending the email respond accordingly
            # this will kick off our sns service and their email will get banned 
            # regardless of wether it was a soft of hard bounce
            return Response({"error": "failed to send OTP to your email address"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    # Handle any other specific errors and return appropriate responses
    except (BotoCoreError, ClientError) as error:
        return Response({"error": f"email not sent: {error}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    except BadHeaderError:
        return Response({"error": "invalid header found."}, status=status.HTTP_400_BAD_REQUEST)
    
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


# account activation
# sets user password
@api_view(['POST'])
def set_password(request):

    # get authorization otp 
    otp = request.COOKIES.get('authorization_otp')

    if not otp:
        return Response({"error": "permission denied"}, status=status.HTTP_401_UNAUTHORIZED)
    
    email = request.data.get('email')
    new_password = request.data.get('password')
    confirm_password = request.data.get('confirmpassword')

    if not email or not new_password or not confirm_password:
        return Response({"error": "missing credentials"}, status=status.HTTP_400_BAD_REQUEST)
    
    if new_password != confirm_password:
        return Response({"error": "passwords do not match"}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        hashed_authorization_otp_and_salt = cache.get(email + 'authorization_otp')
        if not hashed_authorization_otp_and_salt:
            return Response({"error": "OTP expired, please reload the page to request a new OTP"}, status=status.HTTP_400_BAD_REQUEST)
    
    except Exception as e:
        return Response({"error": f"error retrieving OTP from cache: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    if not verify_user_otp(otp, hashed_authorization_otp_and_salt):
        return Response({"error": "incorrect OTP, action forbiden"}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        # activate users account
        user = CustomUser.objects.activate_user(email=email, password=new_password)

        response = Response({"message": "login successful", "role": user.role,}, status=status.HTTP_200_OK)
                
        # generate an access and refresh token for the user 
        token = generate_token(user)

        # set access token cookie with custom expiration (5 mins)
        response.set_cookie('access_token', token['access_token'], domain='.seeran-grades.com', samesite='None', secure=True, httponly=True, max_age=300)
        # set refresh token cookie with custom expiration (86400 seconds = 24 hours)
        response.set_cookie('refresh_token', token['refresh_token'], domain='.seeran-grades.com', samesite='None', secure=True, httponly=True, max_age=86400)
        
        # return response
        return response
    
    except ObjectDoesNotExist:
        # if theres no user with the provided email return an error
        return Response({"error": "user does not exist."}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        # if any exceptions rise during return the response return it as the response
        return Response({"error": f"{str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# authenticates incoming tokens
@api_view(["GET"])
@token_required
def authenticate(request):
    if request.user:
        return Response({"message" : "authenticated", "role" : request.user.role}, status=status.HTTP_200_OK)
    else:
        return Response({"error" : "unauthenticated",}, status=status.HTTP_200_OK)



### logout view ###


# user logout view
@api_view(['POST'])
def logout(request):
    refresh_token = request.COOKIES.get('refresh_token')
    if refresh_token:
        try:
            # Add the refresh token to the blacklist
            response = Response({"message": "logged you out successful"})
            # Clear the refresh token cookie
            response.delete_cookie('access_token', domain='.seeran-grades.com')
            response.delete_cookie('refresh_token', domain='.seeran-grades.com')
            cache.set(refresh_token, 'blacklisted', timeout=86400)
            return response
        except Exception as e:
            return Response({"error": e})
    else:
        return Response({"error": "No refresh token provided"})



### toggle features views ###


# activate multi-factor authentication
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


# subscribe to activity emails 
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



### validation and verification views ###


# Verify otp
@api_view(['POST'])
def verify_otp(request):
    
    email = request.data.get('email')
    otp = request.data.get('otp')

    if not email or not otp:
        return Response({"error": "email and OTP are required."}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        stored_hashed_otp_and_salt = cache.get(email)
        if not stored_hashed_otp_and_salt:
            return Response({"error": "OTP expired. Please generate a new one"}, status=status.HTTP_400_BAD_REQUEST)
    
    except Exception as e:
        return Response({"error": f"error retrieving OTP from cache: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    if verify_user_otp(user_otp=otp, stored_hashed_otp_and_salt=stored_hashed_otp_and_salt):
        
        # OTP is verified, prompt the user to set their password
        cache.delete(email)
        authorization_otp, hashed_authorization_otp, salt = generate_otp()
        cache.set(email+'authorization_otp', (hashed_authorization_otp, salt), timeout=300)  # 300 seconds = 5 mins
        
        response = Response({"message": "OTP verified successfully"}, status=status.HTTP_200_OK)
        response.set_cookie('authorization_otp', authorization_otp, domain='.seeran-grades.com', samesite='None', secure=True, httponly=True, max_age=300)  # 300 seconds = 5 mins
        return response
    
    else:
        return Response({"error": "incorrect OTP. Please try again."}, status=status.HTTP_400_BAD_REQUEST)


# verify otp 
# verifies otp before password reset
# sets needed authorization cookie and limited access token so user can reset their password
@api_view(['POST'])
def otp_verification(request):
    
    email = request.data.get('email')
    otp = request.data.get('otp')
    if not email or not otp:
        return Response({"error": "email and OTP are required."}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        hashed_otp = cache.get(email)
        if not hashed_otp:
            return Response({"error": "OTP expired"}, status=status.HTTP_400_BAD_REQUEST)
    
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    if verify_user_otp(user_otp=otp, stored_hashed_otp_and_salt=hashed_otp):
        
        # OTP is verified, prompt the user to set their password
        try:
            user = CustomUser.objects.get(email=email)
        
        except ObjectDoesNotExist:
            return Response({"error": "invalid credentials/tokens"})
        
        cache.delete(user.email)

        authorization_otp, hashed_authorization_otp = generate_otp()
        cache.set(user.email+'authorization_otp', hashed_authorization_otp, timeout=300)  # 300 seconds = 5 mins
                
        access_token = generate_access_token(user)

        response = Response({"message": "OTP verified successfully"}, status=status.HTTP_200_OK)
        response.set_cookie('access_token', access_token, domain='.seeran-grades.com', samesite='None', secure=True, httponly=True, max_age=300)
        response.set_cookie('authorization_otp', authorization_otp, domain='.seeran-grades.com', samesite='None', secure=True, httponly=True, max_age=300)  # 300 seconds = 5 mins
        
        return response
    
    else:
        return Response({"error": "incorrect OTP. Please try again."}, status=status.HTTP_400_BAD_REQUEST)


# validate password before password change
@api_view(['POST'])
@token_required
def validate_password(request):
    
    # make sure an password was sent
    sent_password = request.data.get('password')
    if not sent_password:
        return Response({"error": "password is required"})
    
    # Validate the password
    if not check_password(sent_password, request.user.password):
        return Response({"error": "invalid password, please try again"}, status=status.HTTP_400_BAD_REQUEST)
    
    # check if the users email is banned
    if request.user.email_banned:
        return Response({ "error" : "your email address has been banned"})
    
    # Create an OTP for the user
    otp, hashed_otp, salt = generate_otp()
    
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
            
            cache.set(request.user.email, (hashed_otp, salt), timeout=300)  # 300 seconds = 5 mins
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


# validate email before email change
@api_view(['POST'])
@token_required
def validate_email_change(request):
    
    # check for sent email
    sent_email = request.data.get('email')   
    if not sent_email:
        return Response({"error": "email address is required"})
    
    # validate the email to make sure it is in the correct format
    if not validate_user_email(sent_email):
        return Response({"error": " invalid email address"})
    
    # Validate the email
    if sent_email != request.user.email:
        return Response({"error" : "invalid email address for account"})
    
    # check if users email is banned
    if request.user.email_banned:
        return Response({ "error" : "your email address has been banned"})
    
    # Create an OTP for the user
    otp, hashed_otp, salt = generate_otp()
    
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
            cache.set(sent_email, (hashed_otp, salt), timeout=300)  # 300 seconds = 5 mins
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


# validate email before password reset
@api_view(['POST'])
def validate_password_reset(request):
    
    # check for sent email
    sent_email = request.data.get('email')
    if not sent_email:
        return Response({"error": "email address is required"})
    
    # try to get the user with the provided email
    try:
        user = CustomUser.objects.get(email=sent_email)
        if not user.role == "FOUNDER":
            if user.school.none_compliant:
                return Response({"denied": "access denied"})
            
    except ObjectDoesNotExist:
        return Response({"error": "invalid email address"})
    
    # check if the account is activated 
    if user.activated == False:
        return Response({"error": "action forbiden for provided account"})
    
    # check if the email is banned 
    if user.email_banned:
        return Response({ "error" : "your email address has been banned, failed to send OTP"})
    
    # Validate the email
    if not validate_user_email(sent_email):
        return Response({"error": " invalid email address"})
    
    # Create an OTP for the user
    otp, hashed_otp, salt = generate_otp()
    
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
                'ToAddresses': [sent_email],
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
            cache.set(sent_email, (hashed_otp, salt), timeout=300)  # 300 seconds = 5 mins
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


### email/password change views ###


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
 

# reset password  used when user has forgotten their password
@api_view(['POST'])
def reset_password(request):
       
    # check if request contains required tokens
    access_token = request.COOKIES.get('access_token')
    if not access_token:
        return Response({"error" : "access token required"})
        
    new_access_token = validate_access_token(access_token)
    
    if new_access_token == None: 
        # Error occurred during validation/refresh, return the error response
        return Response({'error': 'invalid token'}, status=406)
    
    # Get the new password and confirm password from the request data, and authorization otp from the cookies
    otp = request.COOKIES.get('authorization_otp')
    new_password = request.data.get('new_password')
    confirm_password = request.data.get('confirm_password')
    
    if not new_password or not confirm_password or not otp:
        return Response({"error": "missing credentials"}, status=status.HTTP_400_BAD_REQUEST)
        
    # Validate that the new password and confirm password match
    if new_password != confirm_password:
        return Response({"error": "new password and confirm password do not match"}, status=status.HTTP_400_BAD_REQUEST)

    # Assuming the user is authenticated and has changed their password
    decoded_token = AccessToken(new_access_token)
    
    try:
        user = CustomUser.objects.get(pk=decoded_token['user_id'])
        
    except ObjectDoesNotExist:
        return Response({"error": "invalid credentials/tokens"})
    
    # get authorization otp from cache and verify provided otp
    try:
        hashed_authorization_otp = cache.get(user.email + 'authorization_otp')
        if not hashed_authorization_otp:
            return Response({"error": "OTP expired"}, status=status.HTTP_400_BAD_REQUEST)
    
    except Exception as e:
        return Response({"error": f"error retrieving OTP from cache: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    if not verify_user_otp(otp, hashed_authorization_otp):
        return Response({"error": "incorrect OTP, action forrbiden"}, status=status.HTTP_400_BAD_REQUEST)
    
    # update the user's password
    user.set_password(new_password)
    user.save()
    
    try:
        
        response = Response({"message": "password changed successfully"}, status=200)
        # Remove access token cookie from the response
        response.delete_cookie('access_token', domain='.seeran-grades.com')
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
        return Response({ "error" : "your email address has been banned, failed to send OTP"})
    
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
            return Response({"message": "OTP created and sent to your email"}, status=status.HTTP_200_OK)
        else:
            return Response({"error": "failed to send OTP via email"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    except (BotoCoreError, ClientError) as error:
        # Handle specific errors and return appropriate responses
        return Response({"error": f"couldn't send email to the specified email"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    except BadHeaderError:
        return Response({"error": "invalid header found"}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)



### account status check views ###


# checks the accounts multi-factor authentication status
@api_view(["GET"])
@token_required
def mfa_status(request):
    return Response({"mfa_status" : request.user.multifactor_authentication},status=200)


# account activation check
# checks if the account is activated by checking if the account has the password attr
@api_view(["POST"]) 
def account_status(request):

    email = request.data.get("email")

    # try to get the user
    try:
        user = CustomUser.objects.get(email=email)
    except CustomUser.DoesNotExist:
        return Response({"error": "user with the provided email does not exist."})
    if user.password != '' and user.has_usable_password() and user.activated == True:
        return Response({"error": "account already activated"})
    return Response({"message":"account not activated"})



### aws endpoints views ###


# sns topic notification endpoint
# recieve post request when emails bounce/report
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
                        EmailBan.objects.create(email=email_address, reason="email bounced permanently", can_appeal=False)
                        
                        # Look up the user and tag them
                        try:
                            user = CustomUser.objects.get(email=email_address)
                            user.email_banned = True
                            user.email_ban_amount = 3
                            user.save()
                        except CustomUser.DoesNotExist:
                            pass
                    else:
                        try:
                            user = CustomUser.objects.get(email=email_address)
                            if user.email_ban_amount > 2:
                                EmailBan.objects.create(email=email_address, reason="more than 3 emails sent to your email address soft bounced", can_appeal=False)
                            else:
                                # Add the email to bounce table
                                EmailBan.objects.create(email=email_address, reason="an email sent to your email address soft bounced") # the user can appeal to get thier email unbanned 
                                user.email_banned = True
                                user.email_ban_amount = user.email_ban_amount + 1
                                user.save()
                        except CustomUser.DoesNotExist:
                            pass
            elif notification['notificationType'] == 'Complaint':
                complaint = notification['complaint']
                for recipient in complaint['complainedRecipients']:
                    email_address = recipient['emailAddress']
                    try:
                        user = CustomUser.objects.get(email=email_address)
                        if user.email_ban_amount > 2:
                            EmailBan.objects.create(email=email_address, reason="marked three of our emails as spam, this badly harms our companys email sender reputation.", can_appeal=False)
                        else:
                            # Handle complaints here
                            EmailBan.objects.create(email=email_address, reason='marked one of our emails as spam this badly harms our companys email sender reputation.') # the user can appeal to get thier email unbanned 
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


