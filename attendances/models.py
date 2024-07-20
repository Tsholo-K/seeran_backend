# django
from django.db import models

# models
from classes.models import Classroom
from users.models import CustomUser

class Absent(models.Model):
    date = models.DateField(auto_now_add=True)
    classroom = models.ForeignKey(Classroom, on_delete=models.SET_NULL, null=True, related_name='attendances')
    absent_students = models.ManyToManyField(CustomUser, related_name='absences')
    absentes = models.BooleanField(default=False)
    submitted_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, related_name='submitted_attendances')

    class Meta:
        unique_together = ('date', 'classroom')


class Late(models.Model):
    date = models.DateField(auto_now_add=True)
    classroom = models.ForeignKey(Classroom, on_delete=models.SET_NULL, null=True, related_name='late_arrivals')
    late_students = models.ManyToManyField(CustomUser, related_name='late_arrivals')
    submitted_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, related_name='submitted_late_arrivals')

    class Meta:
        unique_together = ('date', 'classroom')