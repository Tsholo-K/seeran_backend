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
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth.hashers import make_password

# models
from .models import CustomUser

# amazon email sending service
import boto3
from botocore.exceptions import BotoCoreError, ClientError

# utility functions 
from .utils import validate_and_refresh_tokens, generate_otp, verify_otp


# views
# login view
@api_view(['POST'])
def login_view(request):
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
        if user.is_principal or user.is_admin:
            role = 'admin'
        elif user.is_parent:
            role = 'parent'
        else:
            role = 'student'
        response_data = {"message": "login successful", "role": role}
        response = Response(response_data, status=status.HTTP_200_OK)
        # Set access token cookie with custom expiration (30 days)
        response.set_cookie('access_token', token['access'], domain='.seeran-grades.com', samesite='None', secure=True, httponly=True, max_age=300)
        if 'refresh' in token:
            # Set refresh token cookie with the same expiration
            response.set_cookie('refresh_token', token['refresh'], domain='.seeran-grades.com', samesite='None', secure=True, httponly=True, max_age=86400)
        return response
    except CustomUser.DoesNotExist:
        return Response({"error": "user does not exist."}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({"error": f"error logging you in: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# sign in view
@api_view(['POST'])
def signin_view(request):
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
    if user.has_usable_password():
        return Response({"error": "account already activated"})
    # Create an OTP for the user
    otp, hashed_otp = generate_otp()
    cache.set(email, hashed_otp, timeout=300)  # 300 seconds = 5 mins
    # Send the OTP via email
    try:
        client = boto3.client('ses', region_name='af-south-1')  # AWS region
        response = client.send_email(
            Destination={
                'ToAddresses': [email],
            },
            Message={
                'Body': {
                    'Text': {
                        'Data': f'Your OTP is {otp}',
                    },
                },
                'Subject': {
                    'Data': 'Your OTP',
                },
            },
            Source='authorization@seeran-grades.com',  # SES verified email address
        )
        # Check the response to ensure the email was successfully sent
        if response['ResponseMetadata']['HTTPStatusCode'] == 200:
            return Response({"message": "OTP created for user and sent via email", "email" : user.email}, status=status.HTTP_200_OK)
        else:
            return Response({"error": "failed to send OTP via email"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    except (BotoCoreError, ClientError) as error:
        # Handle specific errors and return appropriate responses
        return Response({"error": f"email not sent: {error}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    except BadHeaderError:
        return Response({"error": "invalid header found"}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
  
# set password view
@api_view(['POST'])
def set_password_view(request):
    otp = request.COOKIES.get('setpasswordotp')
    email = request.data.get('email')
    new_password = request.data.get('password')
    confirm_password = request.data.get('confirmpassword')
    if not email or not new_password or not confirm_password or not otp:
        return Response({"error": "email, new password and confrim password are required."}, status=status.HTTP_400_BAD_REQUEST)
    if new_password != confirm_password:
        return Response({"error": "passwords do not match"}, status=status.HTTP_400_BAD_REQUEST)
    try:
        stored_hashed_otp = cache.get(email + 'setpasswordotp')
        if not stored_hashed_otp:
            return Response({"error": "OTP expired, please reload the page to request a new OTP"}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response({"error": f"error retrieving OTP from cache: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    if not verify_otp(otp, stored_hashed_otp):
        return Response({"error": "incorrect OTP. Please try again."}, status=status.HTTP_400_BAD_REQUEST)
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
def resend_otp_view(request):
    email = request.data.get('email')
    # try to get the user
    try:
        user = CustomUser.objects.get(email=email)
    except CustomUser.DoesNotExist:
        return Response({"error": "user with this email does not exist."}, status=status.HTTP_400_BAD_REQUEST)
    otp, hashed_otp = generate_otp()
    cache.set(email, hashed_otp, timeout=300)  # 300 seconds = 5 mins
    # Send the OTP via email
    try:
        client = boto3.client('ses', region_name='af-south-1')  # Replace 'us-west-2' with your AWS region
        response = client.send_email(
            Destination={
                'ToAddresses': [email],
            },
            Message={
                'Body': {
                    'Text': {
                        'Data': f'Your OTP is {otp}',
                    },
                },
                'Subject': {
                    'Data': 'Your OTP',
                },
            },
            Source='authorization@seeran-grades.com',  # Replace with your SES verified email address
        )
        # Check the response to ensure the email was successfully sent
        if response['ResponseMetadata']['HTTPStatusCode'] == 200:
            return Response({"message": "a new OTP has been sent to your email address"}, status=status.HTTP_200_OK)
        else:
            return Response({"error": "failed to send OTP via email"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    except (BotoCoreError, ClientError) as error:
        # Handle specific errors and return appropriate responses
        return Response({"error": f"email not sent: {error}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    except BadHeaderError:
        return Response({"error": "invalid header found."}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

# Verify otp view
@api_view(['POST'])
def verify_otp_view(request):
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
    if verify_otp(otp, stored_hashed_otp):
        # OTP is verified, prompt the user to set their password
        cache.delete(email)
        setpasswordotp, hashed_setpasswordotp = generate_otp()
        cache.set(email+'setpasswordotp', hashed_setpasswordotp, timeout=300)  # 300 seconds = 5 mins
        response = Response({"message": "OTP verified successfully"}, status=status.HTTP_200_OK)
        response.set_cookie('setpasswordotp', setpasswordotp, domain='.seeran-grades.com', samesite='None', secure=True, httponly=True, max_age=300)  # 300 seconds = 5 mins
        return response
    else:
        return Response({"error": "incorrect OTP. Please try again."}, status=status.HTTP_400_BAD_REQUEST)

# get credentials view
@api_view(["GET"])
def get_credentials_view(request):
    access_token = request.COOKIES.get('access_token')
    refresh_token = request.COOKIES.get('refresh_token')

    if not access_token or not refresh_token:
        return Response({'Error': 'Access or refresh tokens are missing'}, status=400)

    new_access_token, error_response = validate_and_refresh_tokens(access_token, refresh_token)
    if new_access_token:
        # Either access token is valid or it has been successfully refreshed
        # Set the new access token in the response cookie
        try:
            # Get the value of a specific cookie
            decoded_token = AccessToken(new_access_token)
            user = CustomUser.objects.get(pk=decoded_token['user_id'])
            response = Response({'name': user.name, 'surname' : user.surname}, status=200)
            response.set_cookie('access_token', new_access_token, domain='.seeran-grades.com', samesite='None', secure=True, httponly=True, max_age=300)
            return response
        except ObjectDoesNotExist:
            return Response({'Error': 'User not found'}, status=404)
        except:
            return Response({'Error': 'Invalid access token'}, status=406)
    else:
        # Error occurred during validation/refresh, return the error response
        return error_response

# account activation check
# checks if the account is activated by checking the password attr
@api_view(["POST"]) 
def account_status_view(request):
    email = request.data.get("email")
    # try to get the user
    try:
        user = CustomUser.objects.get(email=email)
    except CustomUser.DoesNotExist:
        return Response({"error": "user with the provided email does not exist."}, status=400)
    if user.has_usable_password():
        return Response({"error": "account already activated"}, status=status.HTTP_403_FORBIDDEN)
    return Response({"message":"account not activated"}, status=status.HTTP_200_OK)

# User logout view
@api_view(['POST'])
def user_logout_view(request):
    refresh_token = request.COOKIES.get('refresh_token')
    if refresh_token:
        try:
            # Add the refresh token to the blacklist
            cache.set(refresh_token, 'blacklisted',timeout=86400)
            response = Response({"message": "logout successful"})
            # Clear the refresh token cookie
            response.delete_cookie('refresh_token')
            return response
        except Exception as e:
            return Response({"error": "Failed to logout"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    else:
        return Response({"error": "No refresh token provided"}, status=status.HTTP_400_BAD_REQUEST)

# Password change view
@api_view(['POST'])
def user_change_password(request):
    # Assuming the user is authenticated and has changed their password
    user = request.user
    # Get the new password and confirm password from the request data
    new_password = request.data.get('new_password')
    confirm_password = request.data.get('confirm_password')
    # Check if the provided previous password matches the current password
    if not check_password(request.data.get('previous_password'), user.password):
        return Response({"error": "previous password is incorrect"}, status=status.HTTP_400_BAD_REQUEST)
    # Validate that the new password and confirm password match
    if new_password != confirm_password:
        return Response({"error": "new password and confirm password do not match"}, status=status.HTTP_400_BAD_REQUEST)
    # Update the user's password
    user.set_password(new_password)
    user.save()
    # Invalidate tokens (both access and refresh tokens)
    try:
        # Invalidate the user's refresh token
        refresh_token = user.refresh_token
        if refresh_token:
            # Clear the user's refresh token
            user.refresh_token = None
            user.save()
    except Exception:
        # Handle any errors appropriately
        pass
    # Return an appropriate response (e.g., success message)
    # Remove access and refresh token cookies from the response
    response = Response({"message": "password changed successfully"}, status=status.HTTP_200_OK)
    try:
        response.delete_cookie("access_token")
        response.delete_cookie("refresh_token")
    except:
        pass
    return response
