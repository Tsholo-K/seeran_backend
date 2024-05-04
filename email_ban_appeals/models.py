# python
import uuid

# django imports
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.db import IntegrityError


class EmailBan(models.Model):
    email = models.EmailField(_('email'))
    reason = models.TextField(_('reason for banning email'), )
    can_appeal = models.BooleanField(_('can user appeal the ban'), default=True)
    
    appeal = models.TextField(_('users request to appeal ban'), null=True )
    status = models.CharField(_('status'), max_length=10, choices=[('PENDING', 'Pending'), ('APPROVED', 'Approved'), ('REJECTED', 'Rejected')], default='PENDING')
    
    # Timestamps
    banned_at = models.DateTimeField(_('the date the email was banned'), auto_now_add=True)
    appealed_at = models.DateTimeField(_('the date the user submitted an appeal'), null=True)
    updated_at = models.DateTimeField(_('the last date the ban was updated'), auto_now=True)

    ban_id = models.CharField(_('email ban id'), max_length=15, unique=True)
    
    
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
            