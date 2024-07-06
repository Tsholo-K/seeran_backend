# python 
import uuid

# django
from django.db import models

# models
from users.models import CustomUser


class BugReport(models.Model):

    # User who reported the bug
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='my_bug_reports')
    section = models.CharField(max_length=124)

    DASHBOARD_CHOICES = [ ('STUDENT', 'Student'), ('TEACHER', 'Teacher'), ('ADMIN', 'Admin'), ('PRINCIPAL', 'Principal') ]
    dashboard = models.CharField(choices=DASHBOARD_CHOICES, max_length=10)

    # Detailed description of the bug
    description = models.TextField()

    # Status of the bug report
    STATUS_CHOICES = [ ('NEW', 'New'), ('IN_PROGRESS', 'In Progress'), ('RESOLVED', 'Resolved') ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='NEW')
    
    bugreport_id = models.CharField(max_length=15, unique=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'Bug Report {self.id} by {self.user.username}'

    # overwrite save method 
    def save(self, *args, **kwargs):
        if not self.bugreport_id:
            self.bugreport_id = self.generate_unique_id('BR')

        super(BugReport, self).save(*args, **kwargs)

    @staticmethod
    def generate_unique_id(prefix=''):
        max_attempts = 10
        for _ in range(max_attempts):
            unique_part = uuid.uuid4().hex[:13]  # Take only the first 13 characters
            id = f"{prefix}{unique_part}"
            if not BugReport.objects.filter(bugreport_id=id).exists():
                return id
        raise ValueError('failed to generate a unique bug report ID after 10 attempts, please try again later.')