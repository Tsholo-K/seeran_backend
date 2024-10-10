# python 
import uuid

# django 
from django.db import models
from django.utils.translation import gettext_lazy as _

# models
from accounts.models import Teacher



class TeacherTimetable(models.Model):
    teacher = models.OneToOneField(Teacher, on_delete=models.CASCADE, related_name='teacher_timetable')
    
    timetables_count = models.PositiveIntegerField(default=0)

    # Foreign key linking to the school where the assessment took place.
    school = models.ForeignKey('schools.School', on_delete=models.CASCADE, related_name='teacher_timetables')

    last_updated = models.DateTimeField(auto_now=True)

    timestamp = models.DateTimeField(auto_now_add=True)
    timetable_id  = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)

    class Meta:
        ...

    def __str__(self):
        return self.timetable_id
