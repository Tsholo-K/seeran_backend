# django imports
from django.db import models
from django.utils.translation import gettext_lazy as _

# models



class BouncedComplaintEmail(models.Model):
    email = models.EmailField(_('email'), unique=True)
    reason = models.TextField(_('reason for banned email'), )    


class EmailBanAppeal(models.Model):
    email = models.EmailField(_('email'), unique=True)
    reason = models.TextField(_('reason for appeal'), )
    status = models.CharField(_('status'), max_length=20, choices=[('PENDING', 'Pending'), ('APPROVED', 'Approved'), ('REJECTED', 'Rejected')], default='PENDING')
