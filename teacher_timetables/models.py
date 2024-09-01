# python 
import uuid

# django 
from django.db import models
from django.utils.translation import gettext_lazy as _

# models
from users.models import Teacher



class TeacherTimetable(models.Model):
    teacher = models.OneToOneField(Teacher, on_delete=models.CASCADE, related_name='teacher_schedule')

    timetable_id  = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)

    class Meta:
        ...

    def __str__(self):
        return self.timetable_id
