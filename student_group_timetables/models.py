# python 
import uuid

# django 
from django.db import models
from django.utils.translation import gettext_lazy as _


class StudentGroupTimetable(models.Model):
    group_name = models.CharField(max_length=64)
    subscribers = models.ManyToManyField('accounts.Student', related_name='timetables')
    
    students_count = models.PositiveIntegerField(default=0)
    timetables_count = models.PositiveIntegerField(default=0)
 
    grade = models.ForeignKey('grades.Grade', on_delete=models.CASCADE, related_name='group_timetables')
    
    school = models.ForeignKey('schools.School', on_delete=models.CASCADE, related_name='group_timetables')

    last_updated = models.DateTimeField(auto_now=True)

    timestamp = models.DateTimeField(auto_now_add=True)
    group_timetable_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)

    class Meta:
        ordering = ['group_name']

    def __str__(self):
        return self.group_timetable_id
