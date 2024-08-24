# python 
import time

# httpx

# channels
from channels.db import database_sync_to_async

# django
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.contrib.auth.password_validation import validate_password
from django.core.cache import cache
from django.utils.translation import gettext as _

# simple jwt
from rest_framework_simplejwt.tokens import AccessToken as decode

# models 
from users.models import BaseUser
from auth_tokens.models import AccessToken
from email_bans.models import EmailBan
from chats.models import ChatRoom, ChatRoomMessage

# serializers

# utility functions 
from authentication.utils import verify_user_otp, validate_user_email

# checks


@database_sync_to_async
def update_email_ban_otp_sends(email_ban_id):
    """
    Updates the OTP sends count for a specific email ban and sets the ban status to 'PENDING'.

    This function increments the count of OTP sends for the specified email ban and updates the status
    to 'PENDING' if it is not already set to that status.

    Args:
        email_ban_id (int): The ID of the email ban to be updated.

    Returns:
        dict: A dictionary containing:
            - 'message': A message indicating that a new OTP has been sent.
            - 'error': A string containing an error message if an exception is raised.

    Raises:
        EmailBan.DoesNotExist: If the email ban with the provided ID does not exist.
        Exception: For any other unexpected errors.

    Example:
        response = await update_email_ban_otp_sends(123)
        if 'error' in response:
            # Handle error
        else:
            message = response['message']
            # Process OTP update
    """
    try:
        # Retrieve the email ban record
        email_ban = EmailBan.objects.get(ban_id=email_ban_id)
        
        # Increment the OTP sends count and update status
        email_ban.otp_send += 1
        if email_ban.status != 'PENDING':
            email_ban.status = 'PENDING'
        email_ban.save()
        
        return {"message": "A new OTP has been sent to your email address."}

    except EmailBan.DoesNotExist:
        return {'error': 'Email ban with the provided ID does not exist. Please verify the ID and try again.'}
    
    except Exception as e:
        return {'error': f'An unexpected error occurred while updating OTP sends: {str(e)}'}


@database_sync_to_async
def update_email(user, details, access_token):
    
    try:
        if not validate_user_email(details.get('new_email')):
            return {'error': 'Invalid email format'}
        
        if BaseUser.objects.filter(email=details.get('new_email')).exists():
            return {"error": "an account with the provided email address already exists"}

        account = BaseUser.objects.get(account_id=user)
        
        if details.get('new_email') == account.email:
            return {"error": "cannot set current email as new email"}
    
        hashed_authorization_otp = cache.get(account.email + 'authorization_otp')
        if not hashed_authorization_otp:
            return {"denied": "OTP expired, taking you back to email verification.."}
    
        if not verify_user_otp(details.get('authorization_otp'), hashed_authorization_otp):
            return {"denied": "incorrect authorization OTP, action forrbiden"}
    
        EmailBan.objects.filter(email=account.email).delete()
        
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
        AccessToken.objects.filter(token=str(access_token)).delete()
    
        return {"message": "email changed successfully"}
    
    except BaseUser.DoesNotExist:
        return {'error': 'user with the provided credentials does not exist'}

    except Exception as e:
        return {"error": str(e)}


@database_sync_to_async
def update_password(user, details, access_token):
    
    try:
        account = BaseUser.objects.get(account_id=user)

        hashed_authorization_otp = cache.get(account.email + 'authorization_otp')
        if not hashed_authorization_otp:
            return {"denied": "OTP expired.. taking you back to password verification.."}
    
        if not verify_user_otp(details.get('authorization_otp'), hashed_authorization_otp):
            return {"denied": "incorrect authorization OTP.. action forrbiden"}
    
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
        AccessToken.objects.filter(token=str(access_token)).delete()
    
        return {"message": "password changed successfully"}
    
    except BaseUser.DoesNotExist:
        return {'error': 'user with the provided credentials does not exist'}
    
    except ValidationError as e:
        return {"error": str(e)}

    except Exception as e:
        return {"error": str(e)}
    

@database_sync_to_async
def update_multi_factor_authentication(user, details):

    try:
        account = BaseUser.objects.get(account_id=user)
        
        if account.email_banned:
            return { "error" : "your email has been banned"}
    
        account.multifactor_authentication = details.get('toggle')
        account.save()
        
        return {'message': 'Multifactor authentication {} successfully'.format('enabled' if details.get('toggle') else 'disabled')}
    
    except BaseUser.DoesNotExist:
        return { 'error': 'user with the provided credentials does not exist' }
    
    except Exception as e:
        return { 'error': str(e) }
    

@database_sync_to_async
def mark_messages_as_read(user, details):
    try:
        # Retrieve the account making the request
        account = BaseUser.objects.get(account_id=user)
        # Retrieve the requested user's account
        requested_user = BaseUser.objects.get(account_id=details.get('account_id'))
        
        # Check if a chat room exists between the two users
        chat_room = ChatRoom.objects.filter(Q(user_one=account, user_two=requested_user) | Q(user_one=requested_user, user_two=account)).first()

        if chat_room:

            # Query for messages that need to be marked as read
            messages_to_update = ChatRoomMessage.objects.filter(chat_room=chat_room, read_receipt=False).exclude(sender=account)

            # Check if there are any messages that match the criteria
            if messages_to_update.exists():

                # Mark the messages as read
                messages_to_update.update(read_receipt=True)
                return {"read": True, 'user': str(requested_user.account_id), 'chat': str(account.account_id)}
            
            else:
                # Handle the case where no messages need to be updated (optional)
                return {"read": True}
        
        return {"error": 'no such chat room exists'}

    except BaseUser.DoesNotExist:
        # Handle case where the user does not exist
        return {'error': 'An account with the provided credentials does not exist. Please check the account details and try again.'}
        
    except ChatRoom.DoesNotExist:
        return {'error': 'Chat room not found.'}

    except Exception as e:
        return {'error': str(e)}

