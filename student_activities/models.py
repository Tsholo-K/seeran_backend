# python 
import uuid

# django 
from django.db import models
from django.utils.translation import gettext_lazy as _


class StudentActivity(models.Model):
    # In case the logger is deleted, we keep the log but set the logger to null
    logger = models.ForeignKey('accounts.BaseUser', on_delete=models.SET_NULL, related_name='logged_activities', null=True, blank=True)
    recipient = models.ForeignKey('accounts.Student', on_delete=models.CASCADE, related_name='my_activities')

    activity_summary = models.CharField(_('offence'), max_length=124)
    activity_details = models.TextField(_('more details about the offence'), max_length=1024)

    classroom = models.ForeignKey('classrooms.Classroom', on_delete=models.SET_NULL, related_name='activities', null=True, blank=True)

    school = models.ForeignKey('schools.School', on_delete=models.CASCADE, related_name='activities')

    timestamp = models.DateTimeField(auto_now_add=True)
    # Prevent the activity ID from being edited after creation
    activity_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.activity_summary} logged by {self.logger} for {self.recipient}"


