# django
from django.db import models

# models
from users.models import BaseUser


class AccessToken(models.Model):
    # The user who owns this access token. If the user is deleted, all associated tokens will be deleted as well.
    user = models.ForeignKey(BaseUser, on_delete=models.CASCADE, related_name='access_tokens')

    # The unique token string. Ensures that each token is distinct across all users.
    token = models.CharField(max_length=255, unique=True)
    
    # Timestamp of when the token was created. Automatically set to the current date and time when the token is created.
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    def __str__(self):
        # Returns a string representation of the access token, showing the user's email.
        return f"{self.user.email} Access Token"


