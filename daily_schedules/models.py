# python 
import uuid

# django 
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError

# models
from teacher_timetables.models import TeacherTimetable
from student_group_timetables.models import StudentGroupTimetable


class DailySchedule(models.Model):

    DAY_OF_THE_WEEK_CHOICES = [
        ('MONDAY', 'Monday'), 
        ('TUESDAY', 'Tuesday'), 
        ('WEDNESDAY', 'Wednesday'), 
        ('THURSDAY', 'Thursday'), 
        ('FRIDAY', 'Friday'), 
        ('SATURDAY', 'Saturday'), 
        ('SUNDAY', 'Sunday'),
    ]

    DAY_OF_THE_WEEK_ORDER = {
        'MONDAY': 1, 
        'TUESDAY': 2, 
        'WEDNESDAY': 3, 
        'THURSDAY': 4, 
        'FRIDAY': 5, 
        'SATURDAY': 6, 
        'SUNDAY': 7
    }

    day_of_week  = models.CharField(_('schedule day'), max_length=10, choices=DAY_OF_THE_WEEK_CHOICES, default="MONDAY")
    day_of_week_order  = models.PositiveIntegerField(choices=[(v, k) for k, v in DAY_OF_THE_WEEK_ORDER.items()])

    teacher_timetable = models.ForeignKey(TeacherTimetable, on_delete=models.CASCADE, related_name='daily_schedules')
    student_group_timetable = models.ForeignKey(StudentGroupTimetable, on_delete=models.CASCADE, related_name='daily_schedules')

    daily_schedule_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)

    class Meta:
        ordering = ['-day_of_week_order']

    def __str__(self):
        return self.daily_schedule_id
    
    def clean(self):
        # Ensure that only one of the foreign keys is set
        if self.teacher_timetable and self.student_group_timetable:
            raise ValidationError("a daily schedule can only be linked to either a teacher timetable or a student group timetable, not both.")

        if not self.teacher_timetable and not self.student_group_timetable:
            raise ValidationError("a daily schedule must be linked to either a teacher timetable or a student group timetable.")

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)