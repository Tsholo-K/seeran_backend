# python 
import random
import uuid

# rest framework
from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework import status

# django
from django.views.decorators.cache import cache_control
from django.core.mail import BadHeaderError
from django.db.models import Q

# custom decorators
from authentication.decorators import token_required
from users.decorators import founder_only, admins_only

# models
from users.models import CustomUser
from schools.models import School
from balances.models import Balance

# serilializer
from .serializers import (MySecurityInfoSerializer,
    PrincipalCreationSerializer, ProfileSerializer, AdminsSerializer,
    AdminCreationSerializer
)

# amazon email sending service
import boto3
from botocore.exceptions import BotoCoreError, ClientError

# custom decorators
from authentication.decorators import token_required
from .decorators import founder_only



############################### users infomation views ####################################


# get users security info
@api_view(["GET"])
@token_required
def my_security_info(request):

    serializer = MySecurityInfoSerializer(instance=request.user)
    return Response({ "users_security_info" : serializer.data },status=200)


##########################################################################################



###################### principal account views for founderdashboard #######################


# create principal account
@api_view(['POST'])
@token_required
@founder_only
def create_principal(request, school_id):
  
    try:
        # Get the school instance
        school = School.objects.get(school_id=school_id)
  
    except School.DoesNotExist:
        return Response({"error" : "school with the provided credentials can not be found"})
  
    # Check if the school already has a principal
    if CustomUser.objects.filter(school=school, role="PRINCIPAL").exists():
        return Response({"error" : "school already has a principal account linked to it"}, status=400)
   
    # Add the school instance to the request data
    data = request.data.copy()
    data['school'] = school.id
    data['role'] = "PRINCIPAL"
  
    serializer = PrincipalCreationSerializer(data=data)
   
    if serializer.is_valid():
      
        try:
            client = boto3.client('ses', region_name='af-south-1')  # AWS region
            # Read the email template from a file
      
            with open('authentication/templates/authentication/accountcreationnotification.html', 'r') as file:
                email_body = file.read()
      
            # Replace the {{otp}} placeholder with the actual OTP
            # email_body = email_body.replace('{{name}}', (user.name.title() + user.surname.title()))
            response = client.send_email(
                Destination={
                    'ToAddresses': [data['email']],
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
             
                created_user = serializer.save()
           
                # Create a new Balance instance for the user
                Balance.objects.create(user=created_user)
           
                return Response({"message": "principal account created successfully"}, status=status.HTTP_200_OK)
            
            else:
                return Response({"error": "email sent to users email address bounced"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
      
        except (BotoCoreError, ClientError) as error:
        
            # Handle specific errors and return appropriate responses
            return Response({"error": error}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
        except BadHeaderError:
            return Response({"error": "invalid header found"}, status=status.HTTP_400_BAD_REQUEST)
      
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)    
 
    return Response({"error" : serializer.errors}, status=400)


# delete principal account
@api_view(['POST'])
@token_required
@founder_only
def delete_principal(request):
   
    try:
        # Get the school instance
        user = CustomUser.objects.get(user_id=request.data['user_id'])
 
    except CustomUser.DoesNotExist:
        return Response({"error" : "user with the provided credentials can not be found"})
 
    try:
        # Add the school instance to the request data
        user.delete()
      
        return Response({"message" : "user account successfully deleted",}, status=status.HTTP_200_OK)
 
    except Exception as e:
       
        # if any exceptions rise during return the response return it as the response
        return Response({"error": {str(e)}}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# get principal profile information
@api_view(['GET'])
@token_required
@founder_only
def principal_profile(request, user_id):
 
    try:
        # Get the school instance
        principal = CustomUser.objects.get(user_id=user_id)
 
    except CustomUser.DoesNotExist:
        return Response({"error" : "user with the provided credentials does not exist"})
 
    # Add the school instance to the request data
    serializer = ProfileSerializer(instance=principal)
    return Response({ "principal" : serializer.data }, status=201)


#############################################################################################



########################### admin account views for admindashboard ###########################


# create admin account
@api_view(['POST'])
@token_required
@admins_only
def create_admin(request):
  
    try:
        # Get the school instance
        school = School.objects.get(school_id=request.user.school.school_id)
  
    except School.DoesNotExist:
        return Response({"error" : "school with the provided credentials can not be found"})
   
    # Add the school instance to the request data
    data = request.data.copy()
    data['school'] = school.id
    data['role'] = "ADMIN"
  
    serializer = AdminCreationSerializer(data=data)
   
    if serializer.is_valid():
      
        try:
            client = boto3.client('ses', region_name='af-south-1')  # AWS region
            # Read the email template from a file
      
            with open('authentication/templates/authentication/accountcreationnotification.html', 'r') as file:
                email_body = file.read()
      
            # Replace the {{otp}} placeholder with the actual OTP
            # email_body = email_body.replace('{{name}}', (user.name.title() + user.surname.title()))
            response = client.send_email(
                Destination={
                    'ToAddresses': [data['email']],
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
             
                serializer.save()
           
                return Response({"message": "admin account created successfully"}, status=status.HTTP_200_OK)
            
            else:
                return Response({"error": "email sent to users email address bounced"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
      
        except (BotoCoreError, ClientError) as error:
        
            # Handle specific errors and return appropriate responses
            return Response({"error": error}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
        except BadHeaderError:
            return Response({"error": "invalid header found"}, status=status.HTTP_400_BAD_REQUEST)
      
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)    
 
    return Response({"error" : serializer.errors}, status=400)


# get all admin accounts in the school
@api_view(['GET'])
@token_required
@admins_only
def admins(request):
 
    # Get the school instance
    admin_accounts = CustomUser.objects.filter( Q(role='ADMIN') | Q(role='PRINCIPAL'), school=request.user.school).exclude(user_id=request.user.user_id)
  
    # serialize query set
    serializer = AdminsSerializer(admin_accounts, many=True)
    return Response({ "admins" : serializer.data }, status=201)


# get admin account
@api_view(['GET'])
@token_required
@admins_only
def admin_profile(request, user_id):
 
    # Get the school instance
    admin = CustomUser.objects.get(user_id=user_id)
  
    # serialize query set
    serializer = ProfileSerializer(instance=admin)
    return Response({ "admin" : serializer.data }, status=201)


#############################################################################################



################################# user upload views ##########################################


# user profile pictures upload 
@api_view(['PATCH'])
@parser_classes([MultiPartParser, FormParser])
@token_required
def update_profile_picture(request):
   
    profile_picture = request.FILES.get('profile_picture', None)
 
    if profile_picture:
     
        try:
            user = CustomUser.objects.get(instance=request.user)  # get the current user
    
        except CustomUser.DoesNotExist:
            return Response({"error" : "user with the provided credentials does not exist"})
        
        try:
        
            user.profile_picture.delete()  # delete the old profile picture if it exists

            # Generate a new filename
            ext = profile_picture.name.split('.')[-1]  # Get the file extension
            filename = f'{uuid.uuid4()}.{ext}'  # Create a new filename using a UUID

            user.profile_picture.save(filename, profile_picture)  # save the new profile picture
            user.save()

            return Response({ 'message' : 'profile picture cahnge successfully'},status=200)
        
        except Exception as e:
    
            # if any exceptions rise during return the response return it as the response
            return Response({"error": {str(e)}}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    else:
        return Response({"error" : "No file was uploaded."}, status=400)


##########################################################################################