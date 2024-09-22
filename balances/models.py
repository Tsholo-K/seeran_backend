# python 
from dateutil.relativedelta import relativedelta
import uuid

# django
from django.db import models
from django.utils import timezone

# models 
from users.models import BaseUser


class Balance(models.Model):
    user = models.OneToOneField(BaseUser, on_delete=models.CASCADE, limit_choices_to={'role__in': ['PRINCIPAL', 'STUDENT']}, related_name='balance' )
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    billing_date = models.DateField(default=(timezone.now() + relativedelta(months=1)).replace(day=7))
        
    last_updated = models.DateTimeField(auto_now=True)

    balance_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)

    def __str__(self):
        return f'{self.user.email if self.user.email else self.user.id_number} owes {self.amount}'



