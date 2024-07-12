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
from email_bans.models import EmailBan

# utility functions 
from authentication.utils import generate_otp, verify_user_otp, validate_user_email
from email_bans.serializers import EmailBansSerializer, EmailBanSerializer


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
def fetch_email_information(user):

    try:
        account = CustomUser.objects.get(account_id=user)
        
        email_bans = EmailBan.objects.filter(email=account.email).order_by('-banned_at')
        serializer = EmailBansSerializer(email_bans, many=True)
    
        return {'information' : { "email_bans" : serializer.data, 'strikes' : account.email_ban_amount, 'banned' : account.email_banned }}
        
    except CustomUser.DoesNotExist:
        return { 'error': 'user with the provided credentials does not exist' }
    
    except Exception as e:
        return { 'error': str(e) }
    
    
@database_sync_to_async
def fetch_email_information(user):

    try:
        account = CustomUser.objects.get(account_id=user)
        
        email_bans = EmailBan.objects.filter(email=account.email).order_by('-banned_at')
        serializer = EmailBansSerializer(email_bans, many=True)
    
        return {'information' : { "email_bans" : serializer.data, 'strikes' : account.email_ban_amount, 'banned' : account.email_banned }}
        
    except CustomUser.DoesNotExist:
        return { 'error': 'user with the provided credentials does not exist' }
    
    except Exception as e:
        return { 'error': str(e) }
    

@database_sync_to_async
def search_email_ban(email, email_ban_id):

    try:
        email_ban = EmailBan.objects.get(ban_id=email_ban_id)
        
        if cache.get(email + 'email_revalidation_otp'):
            can_request = False
        else:
            can_request = True
            
        serializer = EmailBanSerializer(email_ban)
        return { "email_ban" : serializer.data , 'can_request': can_request}
        
    except EmailBan.DoesNotExist:
        return { 'error': 'ban with the provided credentials does not exist' }
    
    except Exception as e:
        return { 'error': str(e) }


@database_sync_to_async
def validate_email_revalidation(user, email_ban_id):

    try:
        account = CustomUser.objects.get(account_id=user)

        email_ban = EmailBan.objects.get(ban_id=email_ban_id)
        
        if not email_ban.email == account.email:
            return { "error" : "invalid request, banned email different from account email" }

        if email_ban.status == 'APPEALED':
            return { "error" : "ban already appealed" }

        if not email_ban.can_appeal:
            return { "error" : "can not appeal this email ban" }
        
        if email_ban.otp_send >= 3 :
            email_ban.can_appeal = False
            email_ban.status = 'BANNED'
            email_ban.save()
            
            return { "denied" : "maximum amount of OTP sends reached, email permanently banned",  }
        
        return {'user' : account}
    
    except CustomUser.DoesNotExist:
        return {'error': 'user with the provided credentials does not exist'}

    except EmailBan.DoesNotExist:
        return {'error': 'ban with the provided credentials does not exist'}
    
    except Exception as e:
        return {'error': str(e)}


@database_sync_to_async
def update_email_ban(email_ban_id):

    try:
        email_ban = EmailBan.objects.get(ban_id=email_ban_id)
        
        email_ban.otp_send += 1
        if email_ban.status != 'PENDING':
            email_ban.status = 'PENDING'
        email_ban.save()
        
        return {"message": "a new OTP has been sent to your email address"}

    except EmailBan.DoesNotExist:
        return {'error': 'ban with the provided credentials does not exist'}
    
    except Exception as e:
        return {'error': str(e)}


@database_sync_to_async
def verify_email_revalidate_otp(user, otp, email_ban_id):

    try:
        account = CustomUser.objects.get(account_id=user)
        email_ban = EmailBan.objects.get(ban_id=email_ban_id)
        
        # try to get revalidation otp from cache
        hashed_otp = cache.get(account.email + 'email_revalidation_otp')
        if not hashed_otp:
            cache.delete(account.email + 'email_revalidation_attempts')
            return {"error": "OTP expired"}

        # check if both otps are valid
        if verify_user_otp(user_otp=otp, stored_hashed_otp_and_salt=hashed_otp):
            
            
            email_ban.status = 'APPEALED'
            account.email_banned = False
            account.save()
            email_ban.save()

            return {"message": "email successfully revalidated email ban lifted", 'status' : email_ban.status.title()}

        else:
            attempts = cache.get(account.email + 'email_revalidation_attempts', 3)
            
            # Incorrect OTP, decrement attempts and handle expiration
            attempts -= 1
            
            if attempts <= 0:

                cache.delete(account.email + 'email_revalidation_otp')
                cache.delete(account.email + 'email_revalidation_attempts')
                
                if email_ban.otp_send >= 3 :
                    email_ban.can_appeal = False
                    email_ban.status = 'BANNED'
                    email_ban.save()
                
                return {"denied": "maximum OTP verification attempts exceeded.."}
            
            cache.set(account.email + 'email_revalidation_attempts', attempts, timeout=300)  # Update attempts with expiration

            return {"error": f"revalidation error, incorrect OTP.. {attempts} attempts remaining"}
    
    except CustomUser.DoesNotExist:
        return {'error': 'user with the provided credentials does not exist'}

    except EmailBan.DoesNotExist:
        return {'error': 'ban with the provided credentials does not exist'}
    
    except Exception as e:
        return {'error': str(e)}
    

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
    
        EmailBan.objects.filter(email=account.email).delete()
        
        account.email = new_email
        account.email_ban_amount = 0
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
    
    except CustomUser.DoesNotExist:
        return {'error': 'user with the provided credentials does not exist'}

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
    
    except CustomUser.DoesNotExist:
        return {'error': 'user with the provided credentials does not exist'}

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
        
        stored_hashed_otp_and_salt = cache.get(account.email + 'account_otp')

        if not stored_hashed_otp_and_salt:
            cache.delete(account.email + 'account_otp_attempts')
            return {"denied": "OTP expired.. please generate a new one"}

        if verify_user_otp(user_otp=otp, stored_hashed_otp_and_salt=stored_hashed_otp_and_salt):
            
            # OTP is verified, prompt the user to set their password
            cache.delete(account.email)
            
            authorization_otp, hashed_authorization_otp, salt = generate_otp()
            cache.set(account.email + 'authorization_otp', (hashed_authorization_otp, salt), timeout=300)  # 300 seconds = 5 mins
            
            return {"message": "OTP verified successfully..", "authorization_otp" : authorization_otp}
        
        else:

            attempts = cache.get(account.email + 'account_otp_attempts', 3)
            
            # Incorrect OTP, decrement attempts and handle expiration
            attempts -= 1
            
            if attempts <= 0:
                cache.delete(account.email + 'account_otp')
                cache.delete(account.email + 'account_otp_attempts')
                
                return {"denied": "maximum OTP verification attempts exceeded.."}
            
            cache.set(account.email + 'account_otp_attempts', attempts, timeout=300)  # Update attempts with expiration

            return {"error": f"incorrect OTP.. {attempts} attempts remaining"}
       
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
            return {"message": f"{user.role.lower()} account created successfully, an account confirmation email has been sent to the user email address"}
            
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
            cache.set(user.email + 'account_otp', (hashed_otp, salt), timeout=300)  # 300 seconds = 5 mins
            
            return {"message": "a new OTP has been sent to your email address"}
        
        if response.status_code in [ 400, 401, 402, 403, 404 ]:
            return {"error": f"there was an error sending the email, please open a new bug ticket with the issue. error code {response.status_code}"}
        
        if response.status_code == 429:
            return {"error": f"there was an error sending the email, please try again in a few moments"}

        else:
            return {"error": "failed to send OTP to your  email address"}
    
    except Exception as e:
        return {"error": str(e)}


async def send_email_revalidation_one_time_pin_email(user):
    
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
            "v:otpcodereason": 'This OTP was generated for your account in response to your email revalidation request'
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
            cache.set(user.email + 'email_revalidation_otp', (hashed_otp, salt), timeout=300)  # 300 seconds = 5 mins
            
            return {"message": "email sent"}
        
        if response.status_code in [ 400, 401, 402, 403, 404 ]:
            return {"error": f"there was an error sending the email, please open a new bug ticket with the issue. error code {response.status_code}"}
        
        if response.status_code == 429:
            return {"error": f"there was an error sending the email, please try again in a few moments"}
        
        else:
            return {"error": "failed to send OTP to your  email address"}

    except Exception as e:
        return {"error": str(e)}
            
