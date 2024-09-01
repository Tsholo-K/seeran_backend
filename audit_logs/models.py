# python
import uuid

# djnago 
from django.db import models

# models
from users.models import BaseUser
from schools.models import School


class AuditLog(models.Model):

    ACTION_CHOICES = [
        ('CREATE', 'Create'),
        ('DELETE', 'Delete'),
        ('UPDATE', 'Update'),
        ('LINK', 'Link'),
    ]

    TARGET_MODEL_CHOICES = [
        ('ACCOUNT', 'Account'),
        ('GRADE', 'Grade'),
        ('TERM', 'Term'),
        ('SUBJECT', 'Subject'),
        ('CLASSROOM', 'Classroom'),
        ('ANNOUNCEMENT', 'Announcement'),
    ]
    
    OUTCOME_CHOICES = [
        ('CREATED', 'Created'),
        ('DELETED', 'Deleted'),
        ('UPDATED', 'Updated'),
        ('DENIED', 'Denied'),
        ('ERROR', 'Error'),
        ('LINKED', 'Linked'),
        ('UNLINKED', 'Unlinked'),
    ]
    
    actor = models.ForeignKey(BaseUser, on_delete=models.CASCADE, related_name='audit_logs')

    action = models.CharField(choices=ACTION_CHOICES, max_length=32)
    timestamp = models.DateTimeField(auto_now_add=True)

    target_model = models.CharField(choices=TARGET_MODEL_CHOICES, max_length=32)

    target_object_id = models.CharField(max_length=36, null=True)

    outcome = models.CharField(choices=OUTCOME_CHOICES, max_length=32)
    response = models.TextField()

    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='audit_logs')

    audit_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.actor.surname} {self.actor.name} performed {self.action} on {self.timestamp}"
    
    def clean(self):
        ...
                
    def save(self, *args, **kwargs):
        self.clean()
        
        try:
            super().save(*args, **kwargs)
        except Exception as e:
            raise e  
