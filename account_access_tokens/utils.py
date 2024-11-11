# python 
from datetime import timedelta

# restframework
from rest_framework.response import Response
from rest_framework import status

# django
from django.utils import timezone
from django.db import transaction

# models
from account_access_tokens.models import AccountAccessToken


def manage_user_sessions(account, token, max_sessions=3):
    """
    Manages user sessions by expiring old tokens and limiting the number of active sessions.
    
    Args:
        user: The user for whom the session is being managed.
        token: The new access token generated for the user.
        max_sessions (int): The maximum number of active sessions allowed. Defaults to 3.
        
    Returns:
        response (Response): A DRF Response object indicating the outcome.
        status_code (int): HTTP status code indicating success or error.
    """
    try:
        cutoff_time = timezone.now() - timedelta(hours=24)
        
        # Expire old access tokens (older than 24 hours)
        with transaction.atomic():
            expired_access_tokens = account.access_tokens.filter(timestamp__lt=cutoff_time)
            if expired_access_tokens.exists():
                expired_access_tokens.delete()

        # Check the number of active sessions
        access_tokens_count = account.access_tokens.count()

        if access_tokens_count >= max_sessions:
            return Response({"error": "Could not process your request, you have reached the maximum number of access tokens for your account. Please logout from one of your other devices to proceed."}, status=status.HTTP_403_FORBIDDEN)
        
        # Create a new access token record
        with transaction.atomic():
            AccountAccessToken.objects.create(account=account, access_token_string=token['access'])

        return None  # No error, so return None

    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)