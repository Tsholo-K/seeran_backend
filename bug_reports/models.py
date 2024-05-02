# python 
import uuid

# django
from django.db import models
from django.db import IntegrityError

# models
from users.models import CustomUser

# utility 


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
    
    bugreport_id = models.CharField(max_length=15, unique=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'Bug Report {self.id} by {self.user.username}'

    # overwrite save method 
    def save(self, *args, **kwargs):
        if not self.bugreport_id:
            self.bugreport_id = self.generate_unique_account_id('BR')

        attempts = 0
        while attempts < 5:
            try:
                super().save(*args, **kwargs)
                break
            except IntegrityError:
                # If an IntegrityError is raised, it means the bugreport_id was not unique.
                # Generate a new bugreport_id and try again.
                self.bugreport_id = self.generate_unique_account_id('BR')
                attempts += 1
        if attempts >= 5:
            raise ValueError('Could not create bug report with unique report ID after 5 attempts. Please try again later.')


    @staticmethod
    def generate_unique_account_id(prefix=''):
        while True:
            unique_part = uuid.uuid4().hex
            account_id = prefix + unique_part
            account_id = account_id[:15].ljust(15, '0')

            if not BugReport.objects.filter(bugreport_id=account_id).exists():
                return account_id