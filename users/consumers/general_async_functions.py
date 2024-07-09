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

# simple jwt
from rest_framework_simplejwt.tokens import AccessToken as decode, TokenError
from rest_framework_simplejwt.exceptions import TokenError

# models 
from users.models import CustomUser
from auth_tokens.models import AccessToken


@database_sync_to_async
def fetch_security_info(user):

    try:
        user = CustomUser.objects.get(account_id=user)
        return { 'multifactor_authentication': user.multifactor_authentication, 'event_emails': user.event_emails }
        
    except CustomUser.DoesNotExist:
        return { 'error': 'user with the provided credentials does not exist' }
    
    except Exception as e:
        return { 'error': str(e) }


@database_sync_to_async
def update_multi_factor_authentication(user, toggle):

    try:
        user = CustomUser.objects.get(account_id=user)
        
        if user.email_banned:
            return { "error" : "your email has been banned"}
    
        user.multifactor_authentication = toggle
        user.save()
        
        return {'message': 'Multifactor authentication {} successfully'.format('enabled' if toggle else 'disabled')}
    
    except CustomUser.DoesNotExist:
        return { 'error': 'user with the provided credentials does not exist' }
    
    except Exception as e:
        return { 'error': str(e) }
    
    
@database_sync_to_async
def log_user_out(access_token):
         
    try:
        # Decode the token
        token = decode(access_token)
        
        # Calculate the remaining time for the token to expire
        expiration_time = token.payload['exp'] - int(time.time())
        
        if expiration_time > 0:
            cache.set(access_token, 'blacklisted', timeout=expiration_time)
    
        # delete token from database
        AccessToken.objects.filter(token=str(access_token)).delete()
        
        return {"message": "logged you out successful"}
    
    except TokenError as e:
        return {"error": str(e)}

    except Exception as e:
        return {"error": str(e)}


async def send_account_confirmation_email(user):
    
    mailgun_api_url = "https://api.eu.mailgun.net/v3/" + config('MAILGUN_DOMAIN') + "/messages"
    
    email_data = {
        "from": "seeran grades <accounts@" + config('MAILGUN_DOMAIN') + ">",
        "to": user.surname.title() + " " + user.name.title() + "<" + user.email + ">",
        "subject": "Account Creation Confirmation",
        "template": "account creation confirmation",
    }
    
    headers = {
        "Authorization": "Basic " + base64.b64encode(f"api:{config('MAILGUN_API_KEY')}".encode()).decode(),
        "Content-Type": "application/x-www-form-urlencoded"
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post( mailgun_api_url, headers=headers, data=email_data )
        
    if response.status_code == 200:
        return {"message": "principal account created successfully"}
        
    else:
        return {"error": "failed to send OTP to users email address"}