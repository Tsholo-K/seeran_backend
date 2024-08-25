# django
from django.db import models

# models
from users.models import BaseUser


class AccessToken(models.Model):
    user = models.ForeignKey(BaseUser, on_delete=models.CASCADE, related_name='access_tokens')

    token = models.CharField(max_length=255, unique=True)
    
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.email} Refresh Token"
