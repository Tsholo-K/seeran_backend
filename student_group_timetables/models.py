# python 
import uuid

# django 
from django.db import models
from django.utils.translation import gettext_lazy as _

# models
from accounts.models import Student
from schools.models import School
from grades.models import Grade


class StudentGroupTimetable(models.Model):
    subscribers = models.ManyToManyField(Student, related_name='timetables')

    group_name = models.CharField(max_length=32)
    grade = models.ForeignKey(Grade, on_delete=models.CASCADE, related_name='group_timetables')
    
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='group_timetables')
    
    last_updated = models.DateTimeField(auto_now=True)

    group_timetable_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)

    class Meta:
        ordering = ['group_name']

    def __str__(self):
        return self.group_schedule_id
