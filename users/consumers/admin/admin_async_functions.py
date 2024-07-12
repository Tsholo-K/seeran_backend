# python 
from decouple import config
import base64
import time

# httpx
import httpx

# channels
from channels.db import database_sync_to_async

# django
from django.core.cache import cache
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.contrib.auth.hashers import check_password
from django.db.models import Q
from django.db import IntegrityError, transaction

# simple jwt
from rest_framework_simplejwt.tokens import AccessToken as decode, TokenError
from rest_framework_simplejwt.exceptions import TokenError

# models 
from users.models import CustomUser
from schools.models import School
from balances.models import Balance
from auth_tokens.models import AccessToken
from email_bans.models import EmailBan
from timetables.models import Session, Schedule, TeacherSchedule

# utility functions 
from authentication.utils import generate_otp, verify_user_otp, validate_user_email, is_valid_human_name
from email_bans.serializers import EmailBansSerializer, EmailBanSerializer

# serilializers
from users.serializers import SecurityInfoSerializer, PrincipalCreationSerializer, AccountUpdateSerializer, IDSerializer, ProfileSerializer, UsersSerializer, AccountCreationSerializer, ProfilePictureSerializer
from timetables.serializers import SchedulesSerializer, SessoinsSerializer


@database_sync_to_async
def search_accounts(user, role):

    try:
        if role not in ['ADMIN', 'TEACHER']:
            return { "error" : 'invalid role request' }
        
        account = CustomUser.objects.get(account_id=user)

        # Get the school admin users
        if role == 'ADMIN':
            accounts = CustomUser.objects.filter( Q(role='ADMIN') | Q(role='PRINCIPAL'), school=account.school).exclude(account_id=user)
    
        if role == 'TEACHER':
            accounts = CustomUser.objects.filter(role=role, school=account.school)

        serializer = UsersSerializer(accounts, many=True)
        return { "users" : serializer.data }
        
    except CustomUser.DoesNotExist:
        return { 'error': 'user with the provided credentials does not exist' }
    
    except Exception as e:
        return { 'error': str(e) }


@database_sync_to_async
def search_teacher_schedules(user, account_id):

    try:
        admin = CustomUser.objects.get(account_id=user)
        account  = CustomUser.objects.get(account_id=account_id)

        if account.role != 'TEACHER' or  admin.school != account.school:
            return { "error" : 'unauthorized access.. permission denied' }
        
        if account.role == 'TEACHER':
            if hasattr(account, 'teacher_schedule'):
            
                teacher_schedule = account.teacher_schedule
                schedules = teacher_schedule.schedules.all()
                serializer = SchedulesSerializer(schedules, many=True)
                schedules_data = serializer.data
            
                # Return the serialized data
                return {"schedules": schedules_data}
        
        else:
            # If there is no associated TeacherSchedule, return an empty list
            return {"schedules": []}
        
    except CustomUser.DoesNotExist:
        return { 'error': 'user with the provided credentials does not exist' }
    
    except Exception as e:
        return { 'error': str(e) }
  
  
@database_sync_to_async
def search_teacher_schedule(user, schedule_id):

    try:
        schedule = Schedule.objects.get(schedule_id=schedule_id)
    
        sessions = schedule.sessions.all()
        serializer = SessoinsSerializer(sessions, many=True)
        
        # Return the response
        return { "sessions" : serializer.data }
    
    except Schedule.DoesNotExist:
        return {"error" : "schedule with the provided ID does not exist"}
        
    except CustomUser.DoesNotExist:
        return { 'error': 'user with the provided credentials does not exist' }
    
    except Exception as e:
        return { 'error': str(e) }
      

@database_sync_to_async
def search_account_profile(user, account_id):

    try:
        admin = CustomUser.objects.get(account_id=user)
        account  = CustomUser.objects.get(account_id=account_id)

        if account.role == 'FOUNDER' or (account.role != 'PARENT' and admin.school != account.school) or (account.role == 'PARENT' and not account.children.filter(school=admin.school).exists()):
            return { "error" : 'unauthorized access.. permission denied' }

        # return the users profile
        serializer = ProfileSerializer(instance=account)
        return { "user" : serializer.data }
        
    except CustomUser.DoesNotExist:
        return { 'error': 'user with the provided credentials does not exist' }
    
    except Exception as e:
        return { 'error': str(e) }
    
    
@database_sync_to_async
def search_account_id(user, account_id):

    try:
        admin = CustomUser.objects.get(account_id=user)
        account  = CustomUser.objects.get(account_id=account_id)

        if account.role == 'FOUNDER' or (account.role != 'PARENT' and admin.school != account.school) or (account.role == 'PARENT' and not account.children.filter(school=admin.school).exists()):
            return { "error" : 'unauthorized access.. permission denied' }

        # return the users profile
        serializer = IDSerializer(instance=account)
        return { "user" : serializer.data }
        
    except CustomUser.DoesNotExist:
        return { 'error': 'user with the provided credentials does not exist' }
    
    except Exception as e:
        return { 'error': str(e) }
    
    
@database_sync_to_async
def create_account(user, details):

    try:
        account = CustomUser.objects.get(account_id=user)

        details['school'] = account.school.id
        
        serializer = AccountCreationSerializer(data=details)
        
        if serializer.is_valid():

            # Extract validated data
            validated_data = serializer.validated_data
            
            with transaction.atomic():
                # Try to create the user using the manager's method
                user = CustomUser.objects.create_user(**validated_data)
            
            return {'user' : user}
            
        return {"error" : serializer.errors}
    
    except IntegrityError as e:
        return {'error': 'account with the provided email address already exists'}
           
    except CustomUser.DoesNotExist:
        return { 'error': 'user with the provided credentials does not exist' }
    
    except Exception as e:
        return { 'error': str(e) }


@database_sync_to_async
def update_account(user, updates, account_id):

    try:        
        admin = CustomUser.objects.get(account_id=user)
        account  = CustomUser.objects.get(account_id=account_id)

        if account.role == 'FOUNDER' or (account.role in ['PRINCIPAL', 'ADMIN'] and admin.role != 'PRINCIPAL') or (account.role != 'PARENT' and admin.school != account.school) or account.role == 'PARENT':
            return { "error" : 'unauthorized access.. permission denied' }
        
        serializer = AccountUpdateSerializer(instance=account, data=updates)
        
        if serializer.is_valid():
            
            with transaction.atomic():
                serializer.save()
                account.refresh_from_db()  # Refresh the user instance from the database
            
            serializer = IDSerializer(instance=account)
            return { "user" : serializer.data }
            
        return {"error" : serializer.errors}
    
    except IntegrityError as e:
        return {'error': 'account with the provided email address already exists'}
    
    except CustomUser.DoesNotExist:
        return { 'error': 'user with the provided credentials does not exist' }
    
    except Exception as e:
        return { 'error': str(e) }
    
    
@database_sync_to_async
def delete_account(user, account_id):

    try:
        admin = CustomUser.objects.get(account_id=user)
        account  = CustomUser.objects.get(account_id=account_id)

        if account.role == 'FOUNDER' or (account.role in ['PRINCIPAL', 'ADMIN'] and admin.role != 'PRINCIPAL') or (account.role != 'PARENT' and admin.school != account.school) or account.role == 'PARENT':
            return { "error" : 'unauthorized access.. permission denied' }
        
        account.delete()
                            
        return {"message" : 'account successfully deleted'}
        
    except CustomUser.DoesNotExist:
        return { 'error': 'user with the provided credentials does not exist' }
    
    except Exception as e:
        return { 'error': str(e) }