# django imports
from django.db import models
from django.utils.translation import gettext_lazy as _

# utility functions
from authentication.utils import generate_account_id

# models



class EmailBan(models.Model):
    email = models.EmailField(_('email'), unique=True)
    reason = models.TextField(_('reason for banned email'), )
    can_appeal = models.BooleanField(default=True)
    
    ban_id = models.CharField(max_length=15, unique=True, default=generate_account_id('EB')) # email bans


class EmailBanAppeal(models.Model):
    email = models.EmailField(_('email'))
    reason = models.TextField(_('reason for appeal'), )
    status = models.CharField(_('status'), max_length=10, choices=[('PENDING', 'Pending'), ('APPROVED', 'Approved'), ('REJECTED', 'Rejected')], default='PENDING')

    appeal_id = models.CharField(max_length=15, unique=True, default=generate_account_id('BA')) # ban appeals