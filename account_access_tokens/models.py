# django
from django.db import models


class AccountAccessToken(models.Model):
    # The user who owns this access token. If the user is deleted, all associated tokens will be deleted as well.
    account = models.ForeignKey('accounts.BaseAccount', on_delete=models.CASCADE, related_name='access_tokens')

    # The unique token string. Ensures that each token is distinct across all users.
    access_token_string = models.CharField(max_length=255, unique=True)
    
    # Timestamp of when the token was created. Automatically set to the current date and time when the token is created.
    timestamp = models.DateTimeField(auto_now_add=True)


