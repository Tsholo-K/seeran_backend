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
            self.balance_id = self.generate_unique_account_id('BL')

        attempts = 0
        while attempts < 5:
            try:
                super().save(*args, **kwargs)
                break
            except IntegrityError:
                # If an IntegrityError is raised, it means the balance_id was not unique.
                # Generate a new balance_id and try again.
                self.balance_id = self.generate_unique_account_id('BL')
                attempts += 1
        if attempts >= 5:
            raise ValueError('Could not create balance with unique balance ID after 5 attempts. Please try again later.')


    @staticmethod
    def generate_unique_account_id(prefix=''):
        while True:
            unique_part = uuid.uuid4().hex
            account_id = prefix + unique_part
            account_id = account_id[:15].ljust(15, '0')

            if not Balance.objects.filter(balance_id=account_id).exists():
                return account_id


class Bill(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    date_billed = models.DateField()
    is_paid = models.BooleanField(default=False)
            
    bill_id = models.CharField(max_length=15, unique=True)

    # overwrite save method
    def save(self, *args, **kwargs):
        # This is a new bill, so update the billing date in the Balance model
        if not self.id:
            balance = self.user.balance
            balance.billing_date = timezone.now().date().replace(day=1) + relativedelta(months=1)
            balance.save()
        super().save(*args, **kwargs)

    def save(self, *args, **kwargs):
        if not self.bill_id:
            self.bill_id = self.generate_unique_account_id('BI')

        attempts = 0
        while attempts < 5:
            try:
                super().save(*args, **kwargs)
                break
            except IntegrityError:
                # If an IntegrityError is raised, it means the bill_id was not unique.
                # Generate a new bill_id and try again.
                self.bill_id = self.generate_unique_account_id('BI')
                attempts += 1
        if attempts >= 5:
            raise ValueError('Could not create user with unique bill ID after 5 attempts. Please try again later.')


    @staticmethod
    def generate_unique_account_id(prefix=''):
        while True:
            unique_part = uuid.uuid4().hex
            account_id = prefix + unique_part
            account_id = account_id[:15].ljust(15, '0')

            if not Bill.objects.filter(bill_id=account_id).exists():
                return account_id
