# python 
import random

# django
from django.views.decorators.cache import cache_control
from django.core.exceptions import ObjectDoesNotExist
from django.core.cache import cache
from django.core.mail import BadHeaderError

# rest framework
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

# amazon email sending service
import boto3
from botocore.exceptions import BotoCoreError, ClientError

# models
from .models import EmailBan
from users.models import CustomUser

# custom decorators
from authentication.decorators import token_required

# serializers
from .serializers import EmailBansSerializer, EmailBanSerializer

# utility finctions 
from authentication.utils import generate_otp, verify_user_otp


@api_view(['GET'])
@token_required
def email_bans(request):
    email_bans = EmailBan.objects.filter(email=request.user.email).order_by('-banned_at')
    serializer = EmailBansSerializer(email_bans, many=True)
    
    return Response({ "email_bans" : serializer.data, 'strikes' : request.user.email_ban_amount, 'banned' : request.user.email_banned }, status=status.HTTP_200_OK)


@api_view(['GET'])
@token_required
@cache_control(max_age=3600, private=True)
def email_ban(request, email_ban_id, invalidator):
    try:
        email_ban = EmailBan.objects.get(ban_id=email_ban_id)
        serializer = EmailBanSerializer(email_ban)
        return Response({ "email_ban" : serializer.data }, status=status.HTTP_200_OK)
    except ObjectDoesNotExist:
        return Response({ "error" : "invalid email ban ID" }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@token_required
def send_otp(request, email_ban_id):
    try:
        email_ban = EmailBan.objects.get(ban_id=email_ban_id)
        
        if not email_ban.email == request.user.email:
            return Response({ "error" : "invalid request, banned email different from account email" }, status=status.HTTP_400_BAD_REQUEST)

        if email_ban.status == 'APPEALED':
            return Response({ "error" : "ban already appealed" }, status=status.HTTP_400_BAD_REQUEST)

        if not email_ban.can_appeal:
            return Response({ "error" : "can not appeal email ban" }, status=status.HTTP_400_BAD_REQUEST)
        
        if email_ban.otp_send >= 3 :
            return Response({ "error" : "reached maximum amount of OTP sends" }, status=status.HTTP_400_BAD_REQUEST)
        
        email_ban.otp_send += 1
        email_ban.status = 'PENDING'
        email_ban.save()
            
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
                    'ToAddresses': [email_ban.email],
                },
                Message={
                    'Body': {
                        'Html': {
                            'Data': email_body,
                        },
                    },
                    'Subject': {
                        'Data': 'Email Revalidate Passcode',
                    },
                },
                Source='seeran grades <authorization@seeran-grades.com>',  # SES verified email address
            )
            # Check the response to ensure the email was successfully sent
            if response['ResponseMetadata']['HTTPStatusCode'] == 200:
                
                # generate authorization cookies needed to revalidate email
                authorization_otp, hashed_authorization_otp, authorization_otp_salt = generate_otp()
                
                # save both otps
                cache.set(email_ban.email+'authorization_otp', (hashed_authorization_otp, authorization_otp_salt), timeout=300)  # 300 seconds = 5 mins
                cache.set(email_ban.email + 'email_revalidation_otp', (hashed_otp, salt), timeout=300)  # 300 seconds = 5 mins
                
                # Generate a random 6-digit number
                # this will invalidate the cache on the frontend
                profile_section = random.randint(100000, 999999)
                response = Response({"message": "OTP created and sent to your email", 'profile_section' : profile_section, 'otp_send' : email_ban.otp_send, 'status' : email_ban.status.title()}, status=status.HTTP_200_OK)
                
                # store authorization otp in cookies
                response.set_cookie('authorization_otp', authorization_otp, domain='.seeran-grades.com', samesite='None', secure=True, httponly=True, max_age=300)  # 300 seconds = 5 mins

                return response
            
            else:
                return Response({"error": "failed to send OTP via email"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        except (BotoCoreError, ClientError) as error:
            # Handle specific errors and return appropriate responses
            return Response({"error": str(error)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        except BadHeaderError:
            return Response({"error": "invalid header found"}, status=status.HTTP_400_BAD_REQUEST)
        
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
  
    except ObjectDoesNotExist:
        return Response({ "error" : "invalid email ban id" }, status=status.HTTP_400_BAD_REQUEST)
    

@api_view(['POST'])
@token_required
def revalidate_email(request, email_ban_id):
    
    # check for otp
    otp = request.data.get('otp')
    authorization_otp = request.COOKIES.get('authorization_otp')
    if not otp or not authorization_otp:
        return Response({"error": "OTP missing."}, status=status.HTTP_400_BAD_REQUEST)
    
    # try to get revalidation otp from cache
    try:
        hashed_otp = cache.get(request.user.email + 'email_revalidation_otp')
        if not hashed_otp:
            return Response({"error": "OTP expired"}, status=status.HTTP_400_BAD_REQUEST)
    
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    # try to get authorization otp from cache and verify provided otp
    try:
        hashed_authorization_otp = cache.get(request.user.email + 'authorization_otp')
        if not hashed_authorization_otp:
            return Response({"error": "OTP expired"}, status=status.HTTP_400_BAD_REQUEST)
    
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # check if both otps are valid
    if verify_user_otp(user_otp=otp, stored_hashed_otp_and_salt=hashed_otp) and verify_user_otp(user_otp=authorization_otp, stored_hashed_otp_and_salt=hashed_authorization_otp):
        try:
            user = CustomUser.objects.get(user_id=request.user.user_id)
            ban = EmailBan.objects.get(ban_id=email_ban_id)
        
        except ObjectDoesNotExist:
            return Response({"error": "provided information is invalid"})
        
        ban.status = 'APPEALED'
        user.email_banned = False
        user.save()
        ban.save()
        
        # Generate a random 6-digit number
        # this will invalidate the cache on the frontend
        profile_section = random.randint(100000, 999999)

        return Response({"message": "email successfully revalidated", 'profile_section' : profile_section, 'status' : ban.status.title()}, status=status.HTTP_200_OK)

    else:
        return Response({"error": "incorrect OTP"}, status=status.HTTP_400_BAD_REQUEST)
