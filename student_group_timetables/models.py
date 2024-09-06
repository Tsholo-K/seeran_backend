# python 
import uuid

# django 
from django.db import models
from django.utils.translation import gettext_lazy as _

# models
from users.models import Student
from grades.models import Grade


class StudentGroupTimetable(models.Model):
    subscribers = models.ManyToManyField(Student, related_name='timetables')

    group_name = models.CharField(max_length=32)
    grade = models.ForeignKey(Grade, on_delete=models.CASCADE, related_name='group_timetables')

    group_timetable_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)

    class Meta:
        ordering = ['group_name']

    def __str__(self):
        return self.group_schedule_id