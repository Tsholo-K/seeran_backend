# python 
import datetime
from dateutil.relativedelta import relativedelta

# django
from django.db import models
from django.utils import timezone

# models 
from users.models import CustomUser

# utility 
from authentication.utils import generate_account_id



class Balance(models.Model):
    
    user = models.OneToOneField( CustomUser, on_delete=models.CASCADE, limit_choices_to={'role__in': ['PRINCIPAL', 'STUDENT']}, related_name='balance' )
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    last_updated = models.DateTimeField(auto_now=True)
    billing_date = models.DateField(default=(timezone.now() + relativedelta(months=1)).replace(day=7))
    
    balance_id = models.CharField(max_length=15, unique=True, default=generate_account_id('BL'))

    def __str__(self):
        return f'{self.user.email if self.user.email else self.user.id_number} owes {self.amount}'


class Bill(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    date_billed = models.DateField()
    is_paid = models.BooleanField(default=False)
    
    bill_id = models.CharField(max_length=15, unique=True, default=generate_account_id('BI'))

    def save(self, *args, **kwargs):
        if not self.id:
            # This is a new bill, so set the billing date to next month.
            self.billing_date = timezone.now().date().replace(day=1) + datetime.timedelta(days=32)
            self.billing_date = self.billing_date.replace(day=1)
        super().save(*args, **kwargs)
