# python 
import random

# rest framework
from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework import status

# django
from django.views.decorators.cache import cache_control
from django.core.mail import BadHeaderError

# custom decorators
from authentication.decorators import token_required
from users.decorators import founder_only

# models
from users.models import CustomUser
from schools.models import School
from balances.models import Balance

# serilializer
from .serializers import MyProfileSerializer, MySecurityInfoSerializer, MyIDSerializer, MyDetailsSerializer, PrincipalCreationSerializer, PrincipalProfileSerializer

# boto
import boto3
from botocore.exceptions import BotoCoreError

# amazon email sending service
import boto3
from botocore.exceptions import BotoCoreError, ClientError

# custom decorators
from authentication.decorators import token_required
from .decorators import founder_only


### users infomation views ###


# get users id info
@api_view(["GET"])
@cache_control(max_age=3600, private=True)
@token_required
def my_id(request, invalidator):
    serializer = MyIDSerializer(instance=request.user)
    return Response({ "user" : serializer.data },status=200)

# get users profile info
@api_view(["GET"])
@cache_control(max_age=3600, private=True)
@token_required
def my_profile(request, invalidator):
    serializer = MyProfileSerializer(instance=request.user)
    return Response({ "user" : serializer.data },status=200)

# get users profile info
@api_view(["GET"])
@cache_control(max_age=3600, private=True)
@token_required
def my_details(request, invalidator):
    serializer = MyDetailsSerializer(instance=request.user)
    return Response({ "user" : serializer.data },status=200)

# get users profile info
@api_view(["GET"])
@cache_control(max_age=0, private=True)
@token_required
def my_security_info(request, invalidator):
    serializer = MySecurityInfoSerializer(instance=request.user)
    return Response({ "user" : serializer.data },status=200)




### principal account views ##


@api_view(['POST'])
@token_required
@founder_only
def create_principal(request, school_id):
    try:
        # Get the school instance
        school = School.objects.get(school_id=school_id)
    except School.DoesNotExist:
        return Response({"error" : "School not found"})
    # Check if the school already has a principal
    if CustomUser.objects.filter(school=school, role="PRINCIPAL").exists():
        return Response({"error" : "This school already has a principal account linked to it"}, status=400)
    # Add the school instance to the request data
    data = request.data.copy()
    data['school'] = school.id
    data['role'] = "PRINCIPAL"
    serializer = PrincipalCreationSerializer(data=data)
    if serializer.is_valid():
        created_user = serializer.save()
        # Create a new Balance instance for the user
        Balance.objects.create(user=created_user)
        user = CustomUser.objects.get(account_id=created_user.account_id)
        try:
            client = boto3.client('ses', region_name='af-south-1')  # AWS region
            # Read the email template from a file
            with open('authentication/templates/authentication/accountcreationnotification.html', 'r') as file:
                email_body = file.read()
            # Replace the {{otp}} placeholder with the actual OTP
            # email_body = email_body.replace('{{name}}', (user.name.title() + user.surname.title()))
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
                        'Data': 'Account Creation Confirmation',
                    },
                },
                Source='seeran grades <authorization@seeran-grades.com>',  # SES verified email address
            )
            # Check the response to ensure the email was successfully sent
            if response['ResponseMetadata']['HTTPStatusCode'] == 200:
                # Generate a random 6-digit number
                # this will invalidate the cache on the frontend
                random_number = random.randint(100000, 999999)
                return Response({"message": "principal account created successfully", "invalidator" : random_number }, status=status.HTTP_200_OK)
            else:
                return Response({"error": "email sent to users email address bounced"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except (BotoCoreError, ClientError) as error:
            # Handle specific errors and return appropriate responses
            return Response({"error": f"couldn't send account creation email to users email address"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except BadHeaderError:
            return Response({"error": "invalid header found"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)    
    return Response({"error" : serializer.errors}, status=400)


@api_view(['GET'])
@cache_control(max_age=300, private=True)
@token_required
@founder_only
def principal_profile(request, user_id, invalidator):
    try:
        # Get the school instance
        principal = CustomUser.objects.get(account_id=user_id)
    except CustomUser.DoesNotExist:
        return Response({"error" : "user not found"})
    # Add the school instance to the request data
    serializer = PrincipalProfileSerializer(data=principal)
    return Response({ "principal" : serializer.data }, status=201)



### user upload views ###


# user profile pictures upload 
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
        # Generate a random 6-digit number
        # this will invalidate the cache on the frontend
        random_number = random.randint(100000, 999999)
        response = Response({"message": "picture updated successfully.", "invalidator" : random_number}, status=200)
        return response
    else:
        return Response({"error" : "No file was uploaded."}, status=400)



