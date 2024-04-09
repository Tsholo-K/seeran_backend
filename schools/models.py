from django.db import models
from authentication.models import CustomUser

from authentication.utils import generate_account_id

class School(models.Model):
    name = models.CharField(max_length=100)
    location = models.CharField(max_length=100)
    contact_number = models.CharField(max_length=15)
    email = models.EmailField(max_length=255, blank=True, null=True)
    website = models.URLField(max_length=200, blank=True, null=True)
    logo = models.ImageField(upload_to='school_logos/', blank=True, null=True)
    established_date = models.DateField(blank=True, null=True)
    accreditation = models.CharField(max_length=100, blank=True, null=True)
    principal = models.OneToOneField(CustomUser, on_delete=models.SET_NULL, related_name='school_principal', blank=True, null=True)
    operating_hours = models.CharField(max_length=100, blank=True, null=True)
    academic_calendar = models.TextField(blank=True, null=True)
    # Add more fields as needed
    
    school_id = models.CharField(max_length=13, unique=True, default=generate_account_id)

    def __str__(self):
        return self.name
