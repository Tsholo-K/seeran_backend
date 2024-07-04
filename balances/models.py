# python 
from dateutil.relativedelta import relativedelta
import uuid

# django
from django.db import models
from django.utils import timezone
from django.db import IntegrityError

# models 
from users.models import CustomUser


class Balance(models.Model):
    
    user = models.OneToOneField( CustomUser, on_delete=models.CASCADE, limit_choices_to={'role__in': ['PRINCIPAL', 'STUDENT']}, related_name='balance' )
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    last_updated = models.DateTimeField(auto_now=True)
    billing_date = models.DateField(default=(timezone.now() + relativedelta(months=1)).replace(day=7))
        
    balance_id = models.CharField(max_length=15, unique=True)

    def __str__(self):
        return f'{self.user.email if self.user.email else self.user.id_number} owes {self.amount}'
    
    # overwrite save method
    def save(self, *args, **kwargs):
        if not self.balance_id:
            self.balance_id = self.generate_unique_id('BL')

        super().save(*args, **kwargs)

    @staticmethod
    def generate_unique_id(prefix=''):
      
        max_attempts = 10
       
        for _ in range(max_attempts):
            unique_part = uuid.uuid4().hex[:13]  # Take only the first 13 characters
            id = f"{prefix}{unique_part}"
            if not Balance.objects.filter(balance_id=id).exists():
                return id
            
        raise ValueError('failed to generate a unique balance ID after 10 attempts, please try again later.')


class Bill(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='my_bills')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    date_billed = models.DateField()

    paid_by = models.ForeignKey(CustomUser, on_delete=models.DO_NOTHING, null=True, blank=True, related_name='bills_paid')
    is_paid = models.BooleanField(default=False)
            
    bill_id = models.CharField(max_length=15, unique=True)

    # overwrite save method
    def save(self, *args, **kwargs):
        if not self.bill_id:
            self.bill_id = self.generate_unique_id('BI')

        super(Bill, self).save(*args, **kwargs)

    @staticmethod
    def generate_unique_id(prefix=''):
      
        max_attempts = 10
       
        for _ in range(max_attempts):
            unique_part = uuid.uuid4().hex[:13]  # Take only the first 13 characters
            id = f"{prefix}{unique_part}"
            if not Bill.objects.filter(bill_id=id).exists():
                return id
            
        raise ValueError('failed to generate a unique bill ID after 10 attempts, please try again later.')
