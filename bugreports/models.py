from django.db import models

# models
from users.models import CustomUser


class BugReport(models.Model):

    # User who reported the bug
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    
    # Detailed description of the bug
    section = models.CharField(max_length=124)

    # Detailed description of the bug
    description = models.TextField()

    # Status of the bug report
    STATUS_CHOICES = [
        ('NEW', 'New'),
        ('IN_PROGRESS', 'In Progress'),
        ('RESOLVED', 'Resolved'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='NEW')

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'Bug Report {self.id} by {self.user.username}'
