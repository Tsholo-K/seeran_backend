# python 
import uuid

# django
from django.db import models

# models
from users.models import BaseUser


DASHBOARD_CHOICES = [
    ('STUDENT', 'Student'),
    ('TEACHER', 'Teacher'),
    ('ADMIN', 'Admin'),
    ('PRINCIPAL', 'Principal')
]

STATUS_CHOICES = [
    ('NEW', 'New'),
    ('IN_PROGRESS', 'In Progress'),
    ('RESOLVED', 'Resolved')
]

class BugReport(models.Model):
    # User who reported the bug
    reporter = models.ForeignKey(BaseUser, on_delete=models.CASCADE, related_name='my_bug_reports')
    section = models.CharField(max_length=124)

    dashboard = models.CharField(choices=DASHBOARD_CHOICES, max_length=10)

    # Detailed description of the bug
    description = models.TextField(max_length=1024)

    # Status of the bug report
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='NEW')

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)
    
    bugreport_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)

    def __str__(self):
        return f'Bug Report by {self.reporter.surname} {self.reporter.name}'
