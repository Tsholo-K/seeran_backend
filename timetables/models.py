# python 
import uuid

# django 
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.db import IntegrityError

# models
from users.models import CustomUser


class Schedule(models.Model):
    
    teacher = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='teachers_schedules')

    # schedule day of the week choices
    DAY_OF_THE_WEEK_CHOICES = [
        ('MONDAY', 'Monday'),
        ('TUESDAY', 'Tuesday'),
        ('WEDNESDAY', 'Wednesday'),
        ('THURSDAY', 'Thursday'),
        ('FRIDAY', 'Friday'),
        ('SATURDAY', 'Saturday'),
        ('SUNDAY', 'Sunday'),
    ]
    day = models.CharField(_('schedule day'), max_length=10, choices=DAY_OF_THE_WEEK_CHOICES, default="MONDAY")

    # schedule id 
    schedule_id = models.CharField(max_length=15, unique=True)  

    class Meta:
        verbose_name = _('schedule')
        verbose_name_plural = _('schedules')

    def __str__(self):
        return self.name

    # assessment id creation handler
    def save(self, *args, **kwargs):
        if not self.schedule_id:
            self.schedule_id = self.generate_unique_account_id('SC')

        attempts = 0
        while attempts < 5:
            try:
                super().save(*args, **kwargs)
                break
            except IntegrityError:
                self.schedule_id = self.generate_unique_account_id('SC') # schedule
                attempts += 1
        if attempts >= 5:
            raise ValueError('Could not create school with unique account ID after 5 attempts. Please try again later.')

    @staticmethod
    def generate_unique_account_id(prefix=''):
        while True:
            unique_part = uuid.uuid4().hex
            account_id = prefix + unique_part
            account_id = account_id[:15].ljust(15, '0')

            if not Schedule.objects.filter(schedule_id=account_id).exists():
                return account_id


class Session(models.Model):
    
    schedule = models.ForeignKey(Schedule, on_delete=models.CASCADE, related_name='schedule_sessions')

    type = models.CharField(max_length=32)
    classroom = models.CharField(max_length=6, null=True, blank=True)
    session_from = models.TimeField()
    session_till = models.TimeField()
