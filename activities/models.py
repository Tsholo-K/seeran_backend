# python 
import uuid

# django 
from django.db import models
from django.utils.translation import gettext_lazy as _

# models
from users.models import BaseUser, Student
from schools.models import School
from classes.models import Classroom


class Activity(models.Model):
    """
    Model to log activities related to students, such as offences or other notable events.
    
    Attributes:
        logger (ForeignKey): The user (e.g., teacher, principal) who logged the activity.
        recipient (ForeignKey): The student for whom the activity is logged.
        offence (CharField): A short code or description of the offence or activity.
        details (TextField): Additional details about the activity.
        date_logged (DateTimeField): The date and time when the activity was logged.
        classroom (ForeignKey): The classroom associated with the activity (optional).
        school (ForeignKey): The school associated with the activity.
        activity_id (CharField): A unique identifier for the activity, generated if not provided.
    """
    
    # In case the logger is deleted, we keep the log but set the logger to null
    logger = models.ForeignKey(BaseUser, on_delete=models.SET_NULL, related_name='logged_activities', null=True, blank=True)
    recipient = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='my_activities')

    offence = models.CharField(_('offence'), max_length=124)
    details = models.TextField(_('more details about the offence'), max_length=1024)

    date_logged = models.DateTimeField(auto_now_add=True)

    classroom = models.ForeignKey(Classroom, on_delete=models.SET_NULL, related_name='activities', null=True, blank=True)
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='activities')

    # Prevent the activity ID from being edited after creation
    activity_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)

    class Meta:
        ordering = ['-date_logged']

    def __str__(self):
        return f"{self.offence} logged by {self.logger} for {self.recipient}"


