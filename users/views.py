# python 
import uuid
import urllib.parse
from decouple import config
import base64

# rest framework
from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework import status

# django
from django.db.models import Q
from django.core.cache import cache
from django.db import transaction

# custom decorators
from authentication.decorators import token_required
from users.decorators import founder_only, admins_only

# models
from users.models import CustomUser
from schools.models import School
from balances.models import Balance

# serilializers
from .serializers import (SecurityInfoSerializer, PrincipalCreationSerializer, ProfileSerializer, UsersSerializer, AccountCreationSerializer, ProfilePictureSerializer)

# custom decorators
from authentication.decorators import token_required
from .decorators import founder_only


################################################## general views ###########################################################


@api_view(["GET"])
@token_required
def my_profile(request):
   
    # if the user is authenticated, return their profile information 
    if request.user:
        serializer = ProfileSerializer(instance=request.user)
        return Response({"user" : serializer.data}, status=status.HTTP_200_OK)

    else:
        return Response({"error" : "unauthenticated",}, status=status.HTTP_401_UNAUTHORIZED)


# get user profile information
@api_view(['GET'])
@token_required
def user_profile(request, account_id):

    # try to get the user instance
    try:
        user = CustomUser.objects.get(account_id=account_id)
 
    except CustomUser.DoesNotExist:
        return Response({"error" : "user with the provided credentials does not exist"}, status=status.HTTP_404_NOT_FOUND)
         
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


############################################################################################################################


################################################# admindashboard views #####################################################  


# delete user account
@api_view(['POST'])
@token_required
@admins_only
def delete_user(request):
   
    account_id = request.data.get('account_id')

    if not account_id:
        return Response({"error": "missing information"}, status=status.HTTP_400_BAD_REQUEST)

    # try to get user
    try:
        user = CustomUser.objects.get(account_id=account_id)
 
        if (user.role == 'PRINCIPAL' or (user.role == 'ADMIN' and request.user.role != 'PRINCIPAL') or request.user.school != user.school):
            return Response({ "error" : 'permission denied' }, status=status.HTTP_400_BAD_REQUEST)

        # try to delete the user instance
        user.delete()
        return Response({"message" : "user account successfully removed from system",}, status=status.HTTP_200_OK)
    
    except CustomUser.DoesNotExist:
        return Response({"error" : "user with the provided credentials can not be found"}, status=status.HTTP_404_NOT_FOUND)
 
    except Exception as e:
        # if any exceptions rise during return the response return it as the response
        return Response({"error": {str(e)}}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# get all ['ADMIN', 'TEACHER', 'PRINCIPAL'] accounts in the school
@api_view(['GET'])
@token_required
@admins_only
def students(request, grade):

    accounts = CustomUser.objects.filter( role='STUDENT', school=request.user.school, grade=grade)

    # serialize query set
    serializer = UsersSerializer(accounts, many=True)
    return Response({ "users" : serializer.data }, status=201)


#############################################################################################



################################# user upload views ##########################################


# user profile pictures upload 
@api_view(['PATCH'])
@parser_classes([MultiPartParser, FormParser])
@token_required
def update_profile_picture(request):
   
    profile_picture = request.FILES.get('profile_picture', None)
 
    if not profile_picture:
        return Response({"error" : "No file was uploaded."}, status=status.HTTP_400_BAD_REQUEST)

    try:
        user = CustomUser.objects.get(account_id=request.user.account_id)  # get the current user

        with transaction.atomic():
            user.profile_picture.delete()  # delete the old profile picture if it exists

            # Generate a new filename
            ext = profile_picture.name.split('.')[-1]  # Get the file extension
            filename = f'{uuid.uuid4()}.{ext}'  # Create a new filename using a UUID

            # URL-encode the filename
            filename = urllib.parse.quote(filename)

            user.profile_picture.save(filename, profile_picture)  # save the new profile picture
            user.save()

        if cache.get(user.account_id + 'profile_picture'):
            cache.delete(user.account_id + 'profile_picture')
        
        else:
            user.refresh_from_db()  # Refresh the user instance from the database

            serializer = ProfilePictureSerializer(instance=user)
            return Response({"profile_picture" : serializer.data}, status=status.HTTP_200_OK)
        
    except CustomUser.DoesNotExist:
        return Response({"error" : "user with the provided credentials does not exist"}, status=status.HTTP_404_NOT_FOUND)

    except Exception as e:
        # if any exceptions rise during return the response return it as the response
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# remove users picture
@api_view(['POST'])
@token_required
def remove_profile_picture(request):
     
    try:
        user = CustomUser.objects.get(account_id=request.user.account_id)  # get the current user

    except CustomUser.DoesNotExist:
        return Response({"error" : "user with the provided credentials does not exist"}, status=status.HTTP_404_NOT_FOUND)
    
    try:
        
        if user.profile_picture:
            user.profile_picture.delete()  # delete the old profile picture if it exists

        else:
            return Response({"error" : 'you already dont have a custom profile picture to remove'}, status=status.HTTP_200_OK)
        
        user.refresh_from_db()  # Refresh the user instance from the database

        serializer = ProfilePictureSerializer(instance=user)
        return Response({"profile_picture" : serializer.data}, status=status.HTTP_200_OK)
    
    except Exception as e:

        # if any exceptions rise during return the response return it as the response
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    

##########################################################################################