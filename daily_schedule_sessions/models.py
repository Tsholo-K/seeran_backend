# python 
import uuid

# django 
from django.db import models
from django.utils.translation import gettext_lazy as _

# models
from daily_schedules.models import DailySchedule


class DailyScheduleSession(models.Model):
    session_type = models.CharField(_('session class type'), max_length=64)

    classroom = models.CharField(max_length=6, null=True, blank=True)

    start_time = models.TimeField()
    end_time = models.TimeField()

    schedule = models.ForeignKey(DailySchedule, on_delete=models.CASCADE, related_name='sessions')

