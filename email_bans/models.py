# python
import uuid

# django imports
from django.db import models
from django.utils.translation import gettext_lazy as _


class EmailBan(models.Model):
  
    email = models.EmailField(_('email'))
    reason = models.TextField(_('reason for banning email'), )
    can_appeal = models.BooleanField(_('can user appeal the ban'), default=True)
    
    otp_send = models.IntegerField(default=0)
    status = models.CharField(_('status'), max_length=10, choices=[('BANNED', 'Banned'), ('PENDING', 'Pending'), ('APPEALED', 'Appealed')], default='BANNED')
    
    banned_at = models.DateTimeField(_('the date the email was banned'), auto_now_add=True)

    ban_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    
       