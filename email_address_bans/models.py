# python
import uuid

# django imports
from django.db import models
from django.utils.translation import gettext_lazy as _


class EmailAddressBan(models.Model):
    banned_email_address = models.EmailField(_('email'))
    reason_for_ban = models.TextField(_('reason for banning email'), )
    
    is_ban_appealable = models.BooleanField(_('can user appeal the ban'), default=True)
    
    email_address_otp_send = models.IntegerField(default=0)
    appeal_status = models.CharField(_('status'), max_length=10, choices=[('BANNED', 'Banned'), ('PENDING', 'Pending'), ('APPEALED', 'Appealed')], default='BANNED')
    
    last_updated = models.DateTimeField(auto_now=True)

    timestamp = models.DateTimeField(auto_now_add=True)
    email_address_ban_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    
       