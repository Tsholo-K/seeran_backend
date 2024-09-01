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
    date_settled = models.DateField(null=True, blank=True)

    paid_by = models.ForeignKey(BaseUser, on_delete=models.DO_NOTHING, null=True, blank=True, related_name='bills_paid')
    is_paid = models.BooleanField(default=False)
            
    Invoice_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)