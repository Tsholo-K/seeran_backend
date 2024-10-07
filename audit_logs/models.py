# python
import uuid

# djnago 
from django.db import models
from django.core.exceptions import ValidationError


class AuditLog(models.Model):

    ACTION_CHOICES = [
        ('CREATE', 'Create'),
        ('UPDATE', 'Update'),
        ('VIEW', 'View'),
        ('ASSIGN', 'Assign'),
        ('DELETE', 'Delete'),
        ('SUBMIT', 'Submit'),
        ('GENERATE', 'Generate'),
        ('LINK', 'Link'),
        ('UNLINK', 'Unlink'),
    ]

    TARGET_MODEL_CHOICES = [
        ('ACCOUNT', 'Account'),
        ('PERMISSION', 'Permission'),
        ('AUDIT_ENTRY', 'Audit Entry'),
        ('ANNOUNCEMENT', 'Announcement'),
        ('GRADE', 'Grade'),
        ('TERM', 'Term'),
        ('SUBJECT', 'Subject'),
        ('PROGRESS_REPORT', 'Progress Report'),
        ('CLASSROOM', 'Classroom'),
        ('ATTENDANCE', 'Attendance'),
        ('ASSESSMENT', 'Assessment'),
        ('TRANSCRIPT', 'Transcript'),
        ('DAILY_SCHEDULE', 'Daily Schedule'),
        ('GROUP_TIMETABLE', 'Group Timetable'),
        ('TEACHER_TIMETABLE', 'Teacher Timetable'),
    ]

    OUTCOME_CHOICES = [
        ('CREATED', 'Created'),
        ('UPDATED', 'Updated'),
        ('ASSIGNED', 'Assigned'),
        ('DELETED', 'Deleted'),
        ('SUBMITTED', 'Submitted'),
        ('GENERATED', 'Generated'),
        ('LINKED', 'Linked'),
        ('UNLINKED', 'Unlinked'),
        ('DENIED', 'Denied'),
        ('ERROR', 'Error'),
    ]

    actor = models.ForeignKey('accounts.BaseAccount', on_delete=models.CASCADE, related_name='audited_actions')

    action = models.CharField(choices=ACTION_CHOICES, max_length=32)
    target_model = models.CharField(choices=TARGET_MODEL_CHOICES, max_length=32)

    target_object_id = models.CharField(max_length=36, null=True)

    outcome = models.CharField(choices=OUTCOME_CHOICES, max_length=32)
    server_response = models.TextField()

    school = models.ForeignKey('schools.School', on_delete=models.CASCADE, related_name='audit_logs')

    timestamp = models.DateTimeField(auto_now_add=True)
    audit_entry_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.actor.surname} {self.actor.name} performed {self.action} on {self.timestamp}"
                
    def save(self, *args, **kwargs):
        # self.clean()
        try:
            super().save(*args, **kwargs)
        except Exception as e:
            raise e  

    def clean(self):
        """
        Custom validation method to ensure the integrity of the model's data.
        """
        if self.action not in dict(self.ACTION_CHOICES).keys():
            raise ValidationError(_('The specified action is not valid. Please check the available audit log actions and ensure your input is correct.'))

        if self.target_model not in dict(self.TARGET_MODEL_CHOICES).keys():
            raise ValidationError(_('The specified target entity is invalid. Please verify the available audit log target entities and ensure your input is correct.'))
