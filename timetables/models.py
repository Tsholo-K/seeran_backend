# python 
import uuid

# django 
from django.db import models
from django.utils.translation import gettext_lazy as _

# models
from users.models import CustomUser
from grades.models import Grade


class Session(models.Model):
    type = models.CharField(_('session class type'), max_length=32)

    classroom = models.CharField(max_length=6, null=True, blank=True)

    session_from = models.TimeField()
    session_till = models.TimeField()

class Schedule(models.Model):
    DAY_OF_THE_WEEK_CHOICES = [
        ('MONDAY', 'Monday'), ('TUESDAY', 'Tuesday'), 
        ('WEDNESDAY', 'Wednesday'), ('THURSDAY', 'Thursday'), 
        ('FRIDAY', 'Friday'), ('SATURDAY', 'Saturday'), 
        ('SUNDAY', 'Sunday')
    ]
    day = models.CharField(_('schedule day'), max_length=10, choices=DAY_OF_THE_WEEK_CHOICES, default="MONDAY")

    sessions = models.ManyToManyField(Session)

    DAY_OF_THE_WEEK_ORDER = {
        'MONDAY': 1, 'TUESDAY': 2, 'WEDNESDAY': 3, 
        'THURSDAY': 4, 'FRIDAY': 5, 'SATURDAY': 6, 'SUNDAY': 7
    }
    day_order = models.PositiveIntegerField(choices=[(v, k) for k, v in DAY_OF_THE_WEEK_ORDER.items()])

    schedule_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)

    class Meta:
        verbose_name = _('schedule')
        verbose_name_plural = _('schedules')
        ordering = ['-day_order']

    def __str__(self):
        return self.schedule_id


class TeacherSchedule(models.Model):
    teacher = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='teacher_schedule')
    schedules = models.ManyToManyField(Schedule, related_name='teacher_linked_to')

    teacher_schedule_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)

    class Meta:
        verbose_name = _('teacher schedule')
        verbose_name_plural = _('teacher schedules')

    def __str__(self):
        return self.teacher_schedule_id

    def delete(self, *args, **kwargs):
        for schedule in self.schedules.all():
            schedule.sessions.all().delete()
            schedule.delete()
        super(TeacherSchedule, self).delete(*args, **kwargs)


class GroupSchedule(models.Model):
    students = models.ManyToManyField(CustomUser, related_name='my_group_schedule')
    schedules = models.ManyToManyField(Schedule, related_name='group_linked_to')

    group_name = models.CharField(max_length=32)
    grade = models.ForeignKey(Grade, on_delete=models.CASCADE, related_name='grade_group_schedules')

    group_schedule_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)

    class Meta:
        verbose_name = _('group schedule')
        verbose_name_plural = _('group schedules')
        ordering = ['group_name']

    def __str__(self):
        return self.group_schedule_id

    def delete(self, *args, **kwargs):
        for schedule in self.schedules.all():
            schedule.sessions.all().delete()
            schedule.delete()
        super(GroupSchedule, self).delete(*args, **kwargs)


