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


def manage_user_sessions(user, token, max_sessions=3):
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
            expired_access_tokens = user.access_tokens.filter(created_at__lt=cutoff_time)
            if expired_access_tokens.exists():
                expired_access_tokens.delete()

        # Check the number of active sessions
        access_tokens_count = user.access_tokens.count()

        if access_tokens_count >= max_sessions:
            return Response({"error": "You have reached the maximum number of connected devices. Please disconnect another device to proceed"}, status=status.HTTP_403_FORBIDDEN)
        
        # Create a new access token record
        with transaction.atomic():
            AccountAccessToken.objects.create(user=user, token=token['access'])

        return None  # No error, so return None

    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)