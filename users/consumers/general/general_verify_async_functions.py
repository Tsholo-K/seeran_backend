# python

# httpx

# channels
from channels.db import database_sync_to_async

# django
from django.core.exceptions import ValidationError
from django.core.cache import cache
from django.contrib.auth.hashers import check_password
from django.utils.translation import gettext as _

# simple jwt

# models 
from users.models import BaseUser
from email_bans.models import EmailBan

# serializers

# utility functions 
from authentication.utils import generate_otp, verify_user_otp, validate_user_email

# checks


@database_sync_to_async
def validate_email_revalidation(user, details):
    """
    Validates whether a user can appeal an email ban and handles OTP limits.

    This function checks if the email ban can be appealed based on the user's account email and
    current status of the email ban. It also updates the email ban status if OTP limits are exceeded.

    Args:
        user (str): The account ID of the user making the request.
        details (dict): A dictionary containing:
            - 'email_ban_id': The ID of the email ban to be validated.

    Returns:
        dict: A dictionary containing:
            - 'user': The user account information if the email ban can be appealed.
            - 'error': A string containing an error message if the appeal is not possible.
            - 'denied': A string containing a denial message if OTP limits are exceeded.

    Raises:
        CustomUser.DoesNotExist: If the user with the provided account ID does not exist.
        EmailBan.DoesNotExist: If the email ban with the provided ID does not exist.
        Exception: For any other unexpected errors.

    Example:
        response = await validate_email_revalidation('user123', {'email_ban_id': 123})
        if 'error' in response:
            # Handle error
        elif 'denied' in response:
            # Handle denial
        else:
            user_info = response['user']
            # Process user information
    """
    try:
        # Retrieve the user account
        account = BaseUser.objects.get(account_id=user)

        # Retrieve the email ban record
        email_ban = EmailBan.objects.get(ban_id=details.get('email_ban_id'))
        
        # Check if the email in the ban matches the user's email
        if email_ban.email != account.email:
            return {"error": "Invalid request: the banned email differs from the account email."}

        # Check the status and appeal possibility of the email ban
        if email_ban.status == 'APPEALED':
            return {"error": "The email ban has already been appealed."}

        if not email_ban.can_appeal:
            return {"error": "This email ban cannot be appealed."}
        
        # Check if the maximum OTP sends have been reached
        if email_ban.otp_send >= 3:
            email_ban.can_appeal = False
            email_ban.status = 'BANNED'
            email_ban.save()
            return {"denied": "Maximum number of OTP sends reached. The email is now permanently banned."}
        
        return {'user': account}

    except BaseUser.DoesNotExist:
        return {'error': 'An account with the provided ID does not exist. Please check the account details and try again.'}

    except EmailBan.DoesNotExist:
        return {'error': 'Email ban with the provided ID does not exist. Please verify the ID and try again.'}
    
    except Exception as e:
        return {'error': f'An unexpected error occurred while validating email revalidation: {str(e)}'}


@database_sync_to_async
def verify_email_revalidate_otp(user, details):
    """
    Verifies the OTP for email revalidation and updates the email ban status accordingly.

    This function checks if the provided OTP is correct and matches the OTP stored in cache.
    If the OTP is valid, it updates the email ban status to 'APPEALED' and unbans the email. 
    If the OTP is invalid or the maximum number of attempts is reached, it updates the ban status as needed.

    Args:
        user (str): The account ID of the user making the request.
        details (dict): A dictionary containing:
            - 'email_ban_id': The ID of the email ban.
            - 'otp': The OTP provided by the user.

    Returns:
        dict: A dictionary containing:
            - 'message': A message indicating the success of email revalidation or a denial message if OTP limits are exceeded.
            - 'error': A string containing an error message if OTP verification fails.
            - 'denied': A string containing a denial message if OTP limits are exceeded.

    Raises:
        CustomUser.DoesNotExist: If the user with the provided account ID does not exist.
        EmailBan.DoesNotExist: If the email ban with the provided ID does not exist.
        Exception: For any other unexpected errors.

    Example:
        response = await verify_email_revalidate_otp('user123', {'email_ban_id': 123, 'otp': '456789'})
        if 'error' in response:
            # Handle error
        elif 'denied' in response:
            # Handle denial
        else:
            message = response['message']
            # Process successful OTP verification
    """
    try:
        # Retrieve the user account
        account = BaseUser.objects.get(account_id=user)

        # Retrieve the email ban record
        email_ban = EmailBan.objects.get(ban_id=details.get('email_ban_id'))
        
        # Retrieve the OTP from cache
        hashed_otp = cache.get(account.email + 'email_revalidation_otp')
        if not hashed_otp:
            cache.delete(account.email + 'email_revalidation_attempts')
            return {"error": "OTP expired. Please request a new OTP."}

        # Verify the provided OTP
        if verify_user_otp(user_otp=details.get('otp'), stored_hashed_otp_and_salt=hashed_otp):
            # OTP is valid, update ban status and user account
            email_ban.status = 'APPEALED'
            account.email_banned = False
            account.save()
            email_ban.save()

            return {"message": "Email successfully revalidated. The email ban has been lifted.", 'status': email_ban.status.title()}

        else:
            # OTP is invalid, update remaining attempts and handle expiration
            attempts = cache.get(account.email + 'email_revalidation_attempts', 3)
            attempts -= 1
            
            if attempts <= 0:
                cache.delete(account.email + 'email_revalidation_otp')
                cache.delete(account.email + 'email_revalidation_attempts')
                
                if email_ban.otp_send >= 3:
                    email_ban.can_appeal = False
                    email_ban.status = 'BANNED'
                    email_ban.save()
                
                return {"denied": "Maximum OTP verification attempts exceeded. The email ban remains in place."}
            
            cache.set(account.email + 'email_revalidation_attempts', attempts, timeout=300)  # Update attempts with expiration

            return {"error": f"Revalidation error: incorrect OTP. {attempts} attempts remaining."}

    except BaseUser.DoesNotExist:
        return {'error': 'An account with the provided ID does not exist. Please check the account details and try again.'}

    except EmailBan.DoesNotExist:
        return {'error': 'Email ban with the provided ID does not exist. Please verify the ID and try again.'}
    
    except Exception as e:
        return {'error': f'An unexpected error occurred while verifying OTP: {str(e)}'}


@database_sync_to_async
def verify_email(details):

    try:
        if not validate_user_email(details.get('email')):
            return {'error': 'Invalid email format'}
        
        account = BaseUser.objects.get(email=details.get('email'))
        
        # check if users email is banned
        if account.email_banned:
            return { "error" : "your email address has been banned.. request denied"}
        
        return {'user' : account}
    
    except BaseUser.DoesNotExist:
        return {'error': 'invalid email address'}

    except ValidationError:
        return {"error": "invalid email address"}
        
    except Exception as e:
        return {"error": str(e)}


@database_sync_to_async
def verify_password(user, details):
    
    try:
        account = BaseUser.objects.get(account_id=user)
        
        # check if the users email is banned
        if account.email_banned:
            return { "error" : "your email address has been banned, request denied"}
            
        # Validate the password
        if not check_password(details.get('password'), account.password):
            return {"error": "invalid password, please try again"}
        
        return {"user" : account}
       
    except BaseUser.DoesNotExist:
        return {'error': 'user with the provided credentials does not exist'}

    except Exception as e:
        return {"error": str(e)}


@database_sync_to_async
def verify_otp(user, details):

    try:
        account = BaseUser.objects.get(account_id=user)

        stored_hashed_otp_and_salt = cache.get(account.email + 'account_otp')

        if not stored_hashed_otp_and_salt:
            cache.delete(account.email + 'account_otp_attempts')
            return {"denied": "OTP expired.. please generate a new one"}

        if verify_user_otp(user_otp=details.get('otp'), stored_hashed_otp_and_salt=stored_hashed_otp_and_salt):
            
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
       
    except BaseUser.DoesNotExist:
        return { 'error': 'user with the provided credentials does not exist' }
 
    except Exception as e:
        return {"error": str(e)}
    
