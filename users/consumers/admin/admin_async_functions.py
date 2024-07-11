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

# simple jwt
from rest_framework_simplejwt.tokens import AccessToken as decode, TokenError
from rest_framework_simplejwt.exceptions import TokenError

# models 
from users.models import CustomUser
from auth_tokens.models import AccessToken
from email_bans.models import EmailBan

# utility functions 
from authentication.utils import generate_otp, verify_user_otp, validate_user_email
from email_bans.serializers import EmailBansSerializer, EmailBanSerializer

# serilializers
from users.serializers import SecurityInfoSerializer, PrincipalCreationSerializer, ProfileSerializer, UsersSerializer, UserCreationSerializer, ProfilePictureSerializer


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