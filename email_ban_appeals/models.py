# python
import uuid

# django imports
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.db import IntegrityError



class EmailBan(models.Model):
    email = models.EmailField(_('email'), unique=True)
    reason = models.TextField(_('reason for banned email'), )
    can_appeal = models.BooleanField(default=True)

    ban_id = models.CharField(max_length=15, unique=True)

    def save(self, *args, **kwargs):
        if not self.ban_id:
            self.ban_id = self.generate_unique_account_id('EB')

        attempts = 0
        while attempts < 5:
            try:
                super().save(*args, **kwargs)
                break
            except IntegrityError:
                # If an IntegrityError is raised, it means the ban_id was not unique.
                # Generate a new ban_id and try again.
                self.ban_id = self.generate_unique_account_id('EB')
                attempts += 1
        if attempts >= 5:
            raise ValueError('Could not create email ban with unique ban ID after 5 attempts. Please try again later.')


    @staticmethod
    def generate_unique_account_id(prefix=''):
        while True:
            unique_part = uuid.uuid4().hex
            account_id = prefix + unique_part
            account_id = account_id[:15].ljust(15, '0')

            if not EmailBan.objects.filter(ban_id=account_id).exists():
                return account_id
            

class EmailBanAppeal(models.Model):
    email = models.EmailField(_('email'))
    reason = models.TextField(_('reason for appeal'), )
    status = models.CharField(_('status'), max_length=10, choices=[('PENDING', 'Pending'), ('APPROVED', 'Approved'), ('REJECTED', 'Rejected')], default='PENDING')
   
    appeal_id = models.CharField(max_length=15, unique=True) # ban appeals

    def save(self, *args, **kwargs):
        if not self.appeal_id:
            self.appeal_id = self.generate_unique_account_id('BA')

        attempts = 0
        while attempts < 5:
            try:
                super().save(*args, **kwargs)
                break
            except IntegrityError:
                # If an IntegrityError is raised, it means the appeal_id was not unique.
                # Generate a new appeal_id and try again.
                self.appeal_id = self.generate_unique_account_id('BA')
                attempts += 1
        if attempts >= 5:
            raise ValueError('Could not create ban appeal with unique appeal ID after 5 attempts. Please try again later.')

    @staticmethod
    def generate_unique_account_id(prefix=''):
        while True:
            unique_part = uuid.uuid4().hex
            account_id = prefix + unique_part
            account_id = account_id[:15].ljust(15, '0')

            if not EmailBanAppeal.objects.filter(appeal_id=account_id).exists():
                return account_id