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
from django.db import transaction

# simple jwt
from rest_framework_simplejwt.tokens import AccessToken as decode, TokenError
from rest_framework_simplejwt.exceptions import TokenError

# models 
from users.models import CustomUser
from schools.models import School
from balances.models import Balance
from auth_tokens.models import AccessToken
from email_bans.models import EmailBan

# utility functions 
from authentication.utils import generate_otp, verify_user_otp, validate_user_email
from email_bans.serializers import EmailBansSerializer, EmailBanSerializer

# serilializers
from users.serializers import SecurityInfoSerializer, PrincipalCreationSerializer, IDSerializer, ProfileSerializer, UsersSerializer, AccountCreationSerializer, ProfilePictureSerializer


@database_sync_to_async
def search_my_school_accounts(user, role):

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
        if details['role'] not in ['ADMIN', 'TEACHER']:
            return { "error" : 'invlaid information provided.. request denied' }

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
        
    except CustomUser.DoesNotExist:
        return { 'error': 'user with the provided credentials does not exist' }
    
    except Exception as e:
        return { 'error': str(e) }