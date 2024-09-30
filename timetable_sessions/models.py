# python 
import uuid

# django 
from django.db import models
from django.utils.translation import gettext_lazy as _


class TimetableSession(models.Model):
    session_type = models.CharField(_('session class type'), max_length=64)
    session_location = models.CharField(max_length=6, null=True, blank=True)

    seesion_start_time = models.TimeField()
    seesion_end_time = models.TimeField()

    timetable = models.ForeignKey('timetables.Timetable', on_delete=models.CASCADE, related_name='sessions')

    school = models.ForeignKey('schools.School', on_delete=models.CASCADE, related_name='timetable_sessions')

    timestamp = models.DateTimeField(auto_now_add=True)
    session_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)

