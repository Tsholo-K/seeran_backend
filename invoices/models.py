# python 
import uuid

# django
from django.db import models

# models 
from accounts.models import BaseAccount


class Invoice(models.Model):
    user = models.ForeignKey(BaseAccount, on_delete=models.CASCADE, related_name='bills')
    amount = models.DecimalField(max_digits=10, decimal_places=2)

    authorization_code = models.CharField(max_length=255, null=True, blank=True)

    payment_status = models.CharField(max_length=255)
                
    last_updated = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    Invoice_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)