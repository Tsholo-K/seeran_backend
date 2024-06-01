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
    
    otp_send = models.IntegerField(default=0)
    status = models.CharField(_('status'), max_length=10, choices=[('BANNED', 'Banned'), ('PENDING', 'Pending'), ('APPEALED', 'Appealed')], default='BANNED')
    
    banned_at = models.DateTimeField(_('the date the email was banned'), auto_now_add=True)

    ban_id = models.CharField(_('email ban id'), max_length=15, unique=True)
    
    def save(self, *args, **kwargs):
        if not self.ban_id:
            self.ban_id = self.generate_unique_id('EB')

        super(EmailBan, self).save(*args, **kwargs)

    @staticmethod
    def generate_unique_id(prefix=''):
        max_attempts = 50
        for _ in range(max_attempts):
            unique_part = uuid.uuid4().hex[:13]  # Take only the first 13 characters
            id = f"{prefix}{unique_part}"
            if not EmailBan.objects.filter(ban_id=id).exists():
                return id
        raise ValueError('failed to generate a unique email ban ID after 10 attempts, please try again later.')            