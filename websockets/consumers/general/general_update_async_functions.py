# python 
import time

# channels
from channels.db import database_sync_to_async

# django
from django.db import transaction
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.contrib.auth.password_validation import validate_password
from django.core.cache import cache
from django.utils.translation import gettext as _

# simple jwt
from rest_framework_simplejwt.tokens import AccessToken as decode

# models 
from account_access_tokens.models import AccountAccessToken
from accounts.models import BaseAccount
from email_address_bans.models import EmailAddressBan
from private_chat_rooms.models import PrivateChatRoom

# utility functions 
from authentication.utils import verify_user_otp


@database_sync_to_async
def update_email_ban_otp_sends(email_ban_id):
    try:
        # Retrieve the email ban record
        email_ban = EmailAddressBan.objects.get(ban_id=email_ban_id)
        
        # Increment the OTP sends count and update status
        email_ban.otp_send += 1
        if email_ban.status != 'PENDING':
            email_ban.status = 'PENDING'
        email_ban.save()
        
        return {"message": "A new OTP has been sent to your email address."}

    except EmailAddressBan.DoesNotExist:
        return {'error': 'Could not process your request, email ban with the provided ID does not exist. Please verify the ID and try again.'}
    
    except Exception as e:
        return {'error': f'Could not process your request, an unexpected error occurred while updating OTP sends: {str(e)}'}


@database_sync_to_async
def update_email_address(user, details, access_token):
    try:
        validate_password(details.get('new_email'))

        if BaseAccount.objects.filter(email=details.get('new_email')).exists():
            return {"error": "Could not process your request, an account with the provided email address already exists."}

        account = BaseAccount.objects.get(account_id=user)
        
        if details.get('new_email') == account.email:
            return {"error": "Could not process your request, cannot set current email address as new email address."}
    
        hashed_authorization_otp = cache.get(account.email + 'authorization_otp')
        if not hashed_authorization_otp:
            return {"denied": "Could not process your request, OTP expired, taking you back to email verification.."}
    
        if not verify_user_otp(details.get('authorization_otp'), hashed_authorization_otp):
            return {"denied": "Could not process your request, incorrect authorization OTP, action forrbiden"}
    
        EmailAddressBan.objects.filter(email=account.email).delete()
        
        account.email = details.get('new_email')
        account.email_ban_amount = 0
        account.save()
        
        # Decode the token
        token = decode(access_token)
        
        # Calculate the remaining time for the token to expire
        expiration_time = token.payload['exp'] - int(time.time())
        
        if expiration_time > 0:
            cache.set(access_token, 'blacklisted', timeout=expiration_time)
    
        # delete token from database
        AccountAccessToken.objects.filter(token=str(access_token)).delete()
    
        return {"message": "email changed successfully"}
    
    except BaseAccount.DoesNotExist:
        return {'error': 'Could not process your request, an account with the provided credentials does not exist, please check the account details and try again.'}

    except Exception as e:
        return {"error": str(e)}


@database_sync_to_async
def update_password(user, details, access_token):
    try:
        account = BaseAccount.objects.get(account_id=user)

        hashed_authorization_otp = cache.get(account.email + 'authorization_otp')
        if not hashed_authorization_otp:
            return {"denied": "Could not process your request, OTP expired.. taking you back to password verification.."}
    
        if not verify_user_otp(details.get('authorization_otp'), hashed_authorization_otp):
            return {"denied": "Could not process your request, incorrect authorization OTP.. action forrbiden."}
    
        validate_password(details.get('new_password'))
        
        account.set_password(details.get('new_password'))
        account.save()
        
        # Decode the token
        token = decode(access_token)
        
        # Calculate the remaining time for the token to expire
        expiration_time = token.payload['exp'] - int(time.time())
        
        if expiration_time > 0:
            cache.set(access_token, 'blacklisted', timeout=expiration_time)
    
        # delete token from database
        AccountAccessToken.objects.filter(token=str(access_token)).delete()
    
        return {"message": "Your accounts password has been successfully updated, you should use your new credetials to log in into your account."}
    
    except BaseAccount.DoesNotExist:
        return {'error': 'Could not process your request, an account with the provided credentials does not exist, please check the account details and try again.'}
    
    except ValidationError as e:
        return {"error": str(e)}

    except Exception as e:
        return {"error": str(e)}
    

@database_sync_to_async
def update_multi_factor_authentication(user, details):
    try:
        account = BaseAccount.objects.get(account_id=user)
        
        if account.email_banned:
            return { "error" : "your email has been banned"}
        
        with transaction.atomic():
            account.multifactor_authentication = details.get('toggle')
            account.save()
        
        return {'message': 'Your accounts multi-factor authentication status has been successfully toggled {}. Your next login authentication will be subject to these changes.'.format('on' if details['toggle'] else 'off')}
    
    except BaseAccount.DoesNotExist:
        return {'error': 'Could not process your request, an account with the provided credentials does not exist, please check the account details and try again.'}
    
    except Exception as e:
        return {'error': str(e)}
    

@database_sync_to_async
def update_messages_as_read(account, details):
    try:
        # Retrieve the account making the request
        requesting_user = BaseAccount.objects.get(account_id=account)
        # Retrieve the requested user's account
        requested_user = BaseAccount.objects.get(account_id=details.get('account'))
        
        # Find if a chat room exists between the two participants
        chat_room = PrivateChatRoom.objects.filter(
            participants=requesting_user
        ).filter(participants=requested_user).first()

        if chat_room:
            # Query for messages that need to be marked as read
            messages_to_update = chat_room.messages.filter(read_receipt=False).exclude(author=requesting_user)

            # Check if there are any messages that match the criteria
            if messages_to_update.exists():
                # Mark the messages as read
                messages_to_update.update(read_receipt=True)
                return {"read": True, 'user': str(requested_user.account_id), 'chat': str(requesting_user.account_id)}
            
            else:
                # Handle the case where no messages need to be updated (optional)
                return {"read": True}
        
        return {"error": 'Could not process your request, no such chat room exists.'}

    except BaseAccount.DoesNotExist:
        # Handle case where the user does not exist
        return {'error': 'Could not process your request, an account with the provided credentials does not exist. please check the account details and try again.'}
        
    except PrivateChatRoom.DoesNotExist:
        return {'error': 'Chat room not found.'}

    except Exception as e:
        return {'error': str(e)}

