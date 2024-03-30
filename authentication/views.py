from rest_framework.decorators import api_view
from rest_framework.response import Response
from .serializers import CustomTokenObtainPairSerializer
from rest_framework import status
from django.contrib.auth.hashers import check_password
from .models import CustomUser
from django.utils import timezone
import hashlib
import random
from django.core.mail import send_mail, BadHeaderError
from django.template.loader import render_to_string


# Login view
@api_view(['POST'])
def custom_token_obtain_pair(request):
    serializer = CustomTokenObtainPairSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    token = serializer.validated_data

    # Set access token cookie with custom expiration (30 days)
    response = Response({"message": "Login successful", "role": token["role"]})
    response.set_cookie('access_token', token['access'], httponly=True, max_age=30 * 24 * 60 * 60)

    if 'refresh' in token:
        # Set refresh token cookie with the same expiration
        response.set_cookie('refresh_token', token['refresh'], httponly=True, max_age=30 * 24 * 60 * 60)

        # Set the tokens to the user object (if available)
        user = getattr(request, 'user', None)
        if user:
            user.access_token = token['access']
            user.refresh_token = token['refresh']

    return response

# functions
def invalidate_tokens(user):
    try:
        # Clear the user's access & refresh token
        user.refresh_token = None
        user.access_token = None
        user.save()
    except Exception:
        # Handle any errors appropriately
        pass    


# User logout view
@api_view(['POST'])
def user_logout(request):
    # Assuming the user is authenticated
    invalidate_tokens(request.user)

    # Remove access and refresh token cookies from the response
    response = Response({"message": "Logout successful"}, status=status.HTTP_200_OK)
    try:
        response.delete_cookie("access_token")
        print(request.COOKIES.get('access_token'))
        response.delete_cookie("refresh_token")
    except:
        pass
    return response


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
        return Response({"error": "Previous password is incorrect"}, status=status.HTTP_400_BAD_REQUEST)

    # Validate that the new password and confirm password match
    if new_password != confirm_password:
        return Response({"error": "New password and confirm password do not match"}, status=status.HTTP_400_BAD_REQUEST)

    # Update the user's password
    user.set_password(new_password)
    user.save()

    # Invalidate tokens (both access and refresh tokens)
    try:
        # Invalidate the user's refresh token
        refresh_token = user.refresh_token
        if refresh_token:
            # Blacklist the refresh token
            refresh_token.blacklist()
            # Clear the user's refresh token (optional, depending on your use case)
            user.refresh_token = None
            user.save()
    except Exception:
        # Handle any errors appropriately
        pass

    # Return an appropriate response (e.g., success message)
    # Remove access and refresh token cookies from the response
    response = Response({"message": "Password changed successfully"}, status=status.HTTP_200_OK)
    try:
        response.delete_cookie("access_token")
        response.delete_cookie("refresh_token")
    except:
        pass
    return response

# otp generation function
def generate_otp():
    otp = str(random.randint(100000, 999999))
    hashed_otp = hashlib.sha256(otp.encode()).hexdigest()
    return otp, hashed_otp

# otp verification function
def verify_otp(user_otp, stored_hashed_otp):
    hashed_user_otp = hashlib.sha256(user_otp.encode()).hexdigest()
    return hashed_user_otp == stored_hashed_otp


# Request otp view
@api_view(['POST'])
def send_otp(request):
    email = request.data.get('email')
    # try to get the user
    try:
        user = CustomUser.objects.get(email=email)
    except CustomUser.DoesNotExist:
        return Response({"error": "User with this email does not exist."}, status=400)
    otp, hashed_otp = generate_otp()
    user.hashed_otp = hashed_otp
    user.save()

    # Render the email template with the OTP
    html_message = render_to_string('email_template.html', {'otp': otp})

    try:
        # Send the email
        send_mail(
            'Your OTP',
            '',  # We're sending HTML email, so the plain text message is empty
            'from@example.com',  # Replace with your email
            [email],
            html_message=html_message,
            fail_silently=False,
        )
        return Response({"message": "OTP sent."})
    except BadHeaderError:
        return Response({"error": "Invalid header found."}, status=400)
    except Exception as e:
        return Response({"error": str(e)}, status=400)


# Verify otp view
@api_view(['POST'])
def verify_otp_view(request):
    email = request.user.email
    otp = request.data.get('otp')
    user = CustomUser.objects.get(email=email)
    if verify_otp(otp, user.hashed_otp):
        user.hashed_otp = None  # Clear the OTP
        user.save()
        return Response({"message": "OTP verified successfully."})
    else:
        return Response({"error": "Incorrect OTP. Please try again."}, status=400)
