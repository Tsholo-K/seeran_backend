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

# simple jwt
from rest_framework_simplejwt.tokens import AccessToken as decode, TokenError
from rest_framework_simplejwt.exceptions import TokenError

# models 
from users.models import CustomUser
from auth_tokens.models import AccessToken

# utility functions 
from authentication.utils import generate_otp, verify_user_otp, validate_user_email


@database_sync_to_async
def fetch_security_info(user):

    try:
        account = CustomUser.objects.get(account_id=user)
        return { 'multifactor_authentication': account.multifactor_authentication, 'event_emails': account.event_emails }
        
    except CustomUser.DoesNotExist:
        return { 'error': 'user with the provided credentials does not exist' }
    
    except Exception as e:
        return { 'error': str(e) }


@database_sync_to_async
def update_email(user, new_email, authorization_otp, access_token):
    
    try:
        account = CustomUser.objects.get(account_id=user)
    
        if new_email == account.email:
            return {"error": "cannot set current email as new email"}
    
        hashed_authorization_otp = cache.get(account.email + 'authorization_otp')
        if not hashed_authorization_otp:
            return {"denied": "OTP expired, taking you back to email verification.."}
    
        if not verify_user_otp(authorization_otp, hashed_authorization_otp):
            return {"denied": "incorrect authorization OTP, action forrbiden"}
            
        if not validate_user_email(new_email):
            return {'error': 'Invalid email format'}
    
        account.email = new_email
        account.save()
        
        # Decode the token
        token = decode(access_token)
        
        # Calculate the remaining time for the token to expire
        expiration_time = token.payload['exp'] - int(time.time())
        
        if expiration_time > 0:
            cache.set(access_token, 'blacklisted', timeout=expiration_time)
    
        # delete token from database
        AccessToken.objects.filter(token=str(access_token)).delete()
    
        return {"message": "email changed successfully"}
      
    except Exception as e:
        return {"error": {str(e)}}


@database_sync_to_async
def update_password(user, new_password, authorization_otp, access_token):
    
    try:
        account = CustomUser.objects.get(account_id=user)
    
        hashed_authorization_otp = cache.get(account.email + 'authorization_otp')
        if not hashed_authorization_otp:
            return {"denied": "OTP expired, taking you back to email verification.."}
    
        if not verify_user_otp(authorization_otp, hashed_authorization_otp):
            return {"denied": "incorrect authorization OTP, action forrbiden"}
    
        account.set_password(new_password)
        account.save()
        
        # Decode the token
        token = decode(access_token)
        
        # Calculate the remaining time for the token to expire
        expiration_time = token.payload['exp'] - int(time.time())
        
        if expiration_time > 0:
            cache.set(access_token, 'blacklisted', timeout=expiration_time)
    
        # delete token from database
        AccessToken.objects.filter(token=str(access_token)).delete()
    
        return {"message": "password changed successfully"}
      
    except Exception as e:
        return {"error": {str(e)}}
    

@database_sync_to_async
def verify_email(email):

    try:
        validate_email(email)
        
        account = CustomUser.objects.get(email=email)
        
        # check if users email is banned
        if account.email_banned:
            return { "error" : "your email address has been banned.. request denied"}
        
        return {'user' : account}
    
    except CustomUser.DoesNotExist:
        return {'error': 'user with the provided credentials does not exist'}

    except ValidationError:
        return {"error": "invalid email"}
        
    except Exception as e:
        return {"error": str(e)}


@database_sync_to_async
def verify_password(user, password):
    
    try:
        account = CustomUser.objects.get(account_id=user)
        
        # check if the users email is banned
        if account.email_banned:
            return { "error" : "your email address has been banned, request denied"}
            
        # Validate the password
        if not check_password(password, account.password):
            return {"error": "invalid password, please try again"}
        
        return {"user" : account}
       
    except CustomUser.DoesNotExist:
        return {'error': 'user with the provided credentials does not exist'}

    except Exception as e:
        return {"error": str(e)}


@database_sync_to_async
def verify_otp(user, otp):

    try:
        account = CustomUser.objects.get(account_id=user)
        
        stored_hashed_otp_and_salt = cache.get(account.email)

        if not stored_hashed_otp_and_salt:
            return {"denied": "OTP expired.. please generate a new one"}

        if verify_user_otp(user_otp=otp, stored_hashed_otp_and_salt=stored_hashed_otp_and_salt):
            
            # OTP is verified, prompt the user to set their password
            cache.delete(account.email)
            
            authorization_otp, hashed_authorization_otp, salt = generate_otp()
            cache.set(account.email+'authorization_otp', (hashed_authorization_otp, salt), timeout=300)  # 300 seconds = 5 mins
            
            return {"message": "OTP verified successfully..", "authorization_otp" : authorization_otp}
        
        else:

            attempts = cache.get(account.email + 'attempts', 3)
            
            if attempts <= 0:
                cache.delete(account.email)
                cache.delete(account.email + 'attempts')
                return {"denied": "maximum OTP verification attempts exceeded.."}
            
            # Incorrect OTP, decrement attempts and handle expiration
            attempts -= 1
            cache.set(account.email + 'attempts', attempts, timeout=300)  # Update attempts with expiration

            return {"error": f"incorrect OTP.. {attempts} remaining"}
       
    except CustomUser.DoesNotExist:
        return { 'error': 'user with the provided credentials does not exist' }
 
    except Exception as e:
        return {"error": str(e)}
    

@database_sync_to_async
def update_multi_factor_authentication(user, toggle):

    try:
        account = CustomUser.objects.get(account_id=user)
        
        if account.email_banned:
            return { "error" : "your email has been banned"}
    
        account.multifactor_authentication = toggle
        account.save()
        
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
    
    try:
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
    
    except Exception as e:
        return {"error": str(e)}


async def send_one_time_pin_email(user, reason):
    
    try:
        otp, hashed_otp, salt = generate_otp()

        # Define your Mailgun API URL
        mailgun_api_url = "https://api.eu.mailgun.net/v3/" + config('MAILGUN_DOMAIN') + "/messages"

        # Define your email data
        email_data = {
            "from": "seeran grades <authorization@" + config('MAILGUN_DOMAIN') + ">",
            "to": user.surname.title() + " " + user.name.title() + "<" + user.email + ">",
            "subject": "One Time Passcode",
            "template": "one-time passcode",
            "v:onetimecode": otp,
            "v:otpcodereason": reason
        }

        # Define your headers
        headers = {
            "Authorization": "Basic " + base64.b64encode(f"api:{config('MAILGUN_API_KEY')}".encode()).decode(),
            "Content-Type": "application/x-www-form-urlencoded"
        }

        # Send the email via Mailgun
        async with httpx.AsyncClient() as client:
            response = await client.post( mailgun_api_url, headers=headers, data=email_data )

        if response.status_code == 200:
                
            # if the email was successfully delivered cache the hashed otp against the users 'email' address for 5 mins( 300 seconds)
            # this is cached to our redis database for faster retrieval when we verify the otp
            cache.set(user.email, (hashed_otp, salt), timeout=300)  # 300 seconds = 5 mins
            
            return {"message": "a new OTP has been sent to your email address"}
            
        else:
            return {"error": "failed to send OTP to your  email address"}
    
    except Exception as e:
        return {"error": str(e)}
