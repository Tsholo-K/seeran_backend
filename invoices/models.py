# python 
import uuid

# django
from django.db import models

# models 
from users.models import BaseUser


class Invoice(models.Model):
    user = models.ForeignKey(BaseUser, on_delete=models.CASCADE, related_name='bills')
    amount = models.DecimalField(max_digits=10, decimal_places=2)

    date_billed = models.DateField()

    is_paid = models.BooleanField(default=False)
    date_settled = models.DateField(null=True, blank=True)
                
    last_updated = models.DateTimeField(auto_now=True)

    Invoice_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)