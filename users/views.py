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
from .serializers import (SecurityInfoSerializer,
    PrincipalCreationSerializer, ProfileSerializer, UsersSerializer,
    UserCreationSerializer
)

# amazon email sending service
import boto3
from botocore.exceptions import BotoCoreError, ClientError

# custom decorators
from authentication.decorators import token_required
from .decorators import founder_only



###################################### general views ###########################################


# get users security info
@api_view(["GET"])
@token_required
def my_security_info(request):

    serializer = SecurityInfoSerializer(instance=request.user)
    return Response({ "users_security_info" : serializer.data },status=200)


# get user profile information
@api_view(['GET'])
@token_required
def user_profile(request):
    
    user_id = request.data.get('user_id')

    if not user_id:
        return Response({"error": "missing information"}, status=status.HTTP_400_BAD_REQUEST)

    # try to get the user instance
    try:
        user = CustomUser.objects.get(user_id=user_id)
 
    except CustomUser.DoesNotExist:
        return Response({"error" : "user with the provided credentials does not exist"})
         
    if request.user.role == 'FOUNDER' and user.role != 'PRINCIPAL':
        return Response({ "error" : 'permission denied' }, status=status.HTTP_400_BAD_REQUEST)

    # permission check
    if request.user.role != 'FOUNDER':

        if user.role == 'FOUNDER' or (request.user.role != 'PARENT' and user.school != request.user.school):
            return Response({ "error" : 'permission denied' }, status=status.HTTP_400_BAD_REQUEST)
        
        # students 
        if request.user.role == 'STUDENT':

            if user.role == 'PRINCIPAL' or user.role == 'STUDENT':
                return Response({ "error" : 'permission denied' }, status=status.HTTP_400_BAD_REQUEST)
            
            if user.role == 'PARENT' and request.user not in user.children:
                return Response({ "error" : 'permission denied' }, status=status.HTTP_400_BAD_REQUEST)

            if user.role == 'TEACHER':

                teachers = []

                for clas in request.user.classes:
                    teachers.append(clas.teacher)

                if user not in teachers:
                    return Response({ "error" : 'permission denied' }, status=status.HTTP_400_BAD_REQUEST)

        # parents
        if request.user.role == 'PARENT':

            if user.role == 'PRINCIPAL' or ( user.role == 'STUDENT' and user not in request.user.children ):
                return Response({ "error" : 'permission denied' }, status=status.HTTP_400_BAD_REQUEST)
            
            if user.role == 'STUDENT':
                pass
            
            else:
                schools = []
                teachers = []

                for child in request.user.children:
                    schools.append(child.school)
                    for clas in child.classes:
                        teachers.append(clas.teacher)

                if user.role == 'ADMIN'  and user.school not in schools:
                    return Response({ "error" : 'permission denied' }, status=status.HTTP_400_BAD_REQUEST)
                
                if user.role == 'TEACHER' and user not in teachers:
                    return Response({ "error" : 'permission denied' }, status=status.HTTP_400_BAD_REQUEST)
                
        # teacher
        if request.user.role == 'TEACHER':

            if user.role == 'PARENT' or user.role == 'STUDENT':
                in_class = False

                if user.role == 'STUDENT':
                    for clas in request.user.classes:
                        if user in clas.students:
                            in_class = True
                            break
                
                if user.role == 'PARENT':
                    for clas in request.user.classes:
                        if user in clas.parents:
                            in_class = True
                            break

                if not in_class:
                    return Response({ "error" : 'permission denied' }, status=status.HTTP_400_BAD_REQUEST)

    # return the users profile
    serializer = ProfileSerializer(instance=user)
    return Response({ "user" : serializer.data }, status=201)


################################################################################################



############################## founderdashboard view functions #################################


# create principal account
@api_view(['POST'])
@token_required
@founder_only
def create_principal(request, school_id):
          
    # try to get the school instance
    try:
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


################################################################################################



#################################### admindashboard views ######################################


# create user account
@api_view(['POST'])
@token_required
@admins_only
def create_user(request):

    role = request.data.get('role')

    if not role:
        return Response({"error": "missing information"}, status=status.HTTP_400_BAD_REQUEST)

    if role == 'FOUNDER' or role == 'PRINCIPAL':
        return Response({ "error" : 'permission denied' }, status=status.HTTP_400_BAD_REQUEST)

    # try to get the school instance
    try:
        school = School.objects.get(school_id=request.user.school.school_id)
  
    except School.DoesNotExist:
        return Response({"error" : "school with the provided credentials can not be found"})
    
    # retrieve the provided information
    name = request.data.get('name')
    surname = request.data.get('surname')
    id_number = request.data.get('id_number')
    email = request.data.get('email')

    # if anyone of these is missing return a 400 error
    if not name or not surname:
        return Response({"error": "missing information"}, status=status.HTTP_400_BAD_REQUEST)

    if role == 'ADMIN' or  role == 'PARENT' or  role == 'TEACHER':

        # if anyone of these is missing return a 400 error
        if not email:
            return Response({"error": "missing information"}, status=status.HTTP_400_BAD_REQUEST)

    if role == 'STUDENT':

        # if anyone of these is missing return a 400 error
        if not id_number:
            return Response({"error": "missing information"}, status=status.HTTP_400_BAD_REQUEST)
        
    # copy the request data to a data variable and add school
    data = request.data.copy()
    data['school'] = school.id
    
    serializer = UserCreationSerializer(data=data)
   
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
           
                return Response({"message": "{} account created successfully".format(role.title()) }, status=status.HTTP_200_OK)
            
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


# delete admin account
@api_view(['POST'])
@token_required
@admins_only
def delete_user(request):
   
    # try to get user
    try:
        user = CustomUser.objects.get(user_id=request.data.get('user_id'))
 
    except CustomUser.DoesNotExist:
        return Response({"error" : "user with the provided credentials can not be found"})
 
    if user.role == 'PRINCIPAL' or request.user.school != user.school or (user.role == 'ADMIN' and request.user.role != 'PRINCIPAL'):
        return Response({ "error" : 'permission denied' }, status=status.HTTP_400_BAD_REQUEST)

    # try to delete the user instance
    try:

        user.delete()
        return Response({"message" : "user account successfully deleted",}, status=status.HTTP_200_OK)
 
    except Exception as e:
       
        # if any exceptions rise during return the response return it as the response
        return Response({"error": {str(e)}}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# get all 'role' accounts in the school
@api_view(['GET'])
@token_required
@admins_only
def users(request, role):

    if role == 'ADMIN':
        # Get the school admin users
        accounts = CustomUser.objects.filter( Q(role='ADMIN') | Q(role='PRINCIPAL'), school=request.user.school).exclude(user_id=request.user.user_id)
   
    if role == 'STUDENT':
        grade = request.data.get('grade')

        if not grade:
            return Response({"error": "missing information"}, status=status.HTTP_400_BAD_REQUEST)

        accounts = CustomUser.objects.filter(role=role, grade=grade, school=request.user.school)
  
    if role == 'TEACHER':
        accounts = CustomUser.objects.filter(role=role, school=request.user.school)

    # serialize query set
    serializer = UsersSerializer(accounts, many=True)
    return Response({ "users" : serializer.data }, status=201)


# get admin account
@api_view(['GET'])
@token_required
@admins_only
def admin_profile(request, user_id):
 
    # Get the school instance
    try:
        admin = CustomUser.objects.get(user_id=user_id)

    except CustomUser.DoesNotExist:
        return Response({"error" : "user with the provided credentials doesnot exist"})

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