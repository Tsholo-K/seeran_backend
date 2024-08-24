# django
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError

# models
from users.models import BaseUser, Student
from classes.models import Classroom

class Absent(models.Model):
    date = models.DateTimeField(auto_now_add=True)

    classroom = models.ForeignKey(Classroom, on_delete=models.SET_NULL, null=True, related_name='attendances')
    
    absent_students = models.ManyToManyField(Student, related_name='absences')
    absentes = models.BooleanField(default=False) # helps in querying 

    submitted_by = models.ForeignKey(BaseUser, on_delete=models.SET_NULL, null=True, related_name='submitted_attendances')

    class Meta:
        unique_together = ('date', 'classroom') # this will prevent the creation of duplicate instances
        ordering = ['-date']
        indexes = [models.Index(fields=['date'])]  # Index for performance

    def clean(self):
        super().clean()

        if self.submitted_by and self.submitted_by.role not in ['PRINCIPAL', 'ADMIN', 'TEACHER']:
            raise ValidationError('Submitted by user must be an Admin or Teacher.')


class Late(models.Model):
    date = models.DateTimeField(auto_now_add=True)

    classroom = models.ForeignKey(Classroom, on_delete=models.SET_NULL, null=True, related_name='late_arrivals')
    late_students = models.ManyToManyField(Student, related_name='late_arrivals')

    submitted_by = models.ForeignKey(BaseUser, on_delete=models.SET_NULL, null=True, related_name='submitted_late_arrivals')

    class Meta:
        unique_together = ('date', 'classroom') # this will prevent the creation of duplicate instances
        ordering = ['-date']
        indexes = [models.Index(fields=['date'])]  # Index for performance

class Emergency(models.Model):
    date = models.DateTimeField(auto_now_add=True)

    emergency = models.CharField(max_length=124, default='fire drill')
    emergency_location = models.CharField(max_length=124, default='')

    special_instructions = models.TextField()

    classroom = models.ForeignKey(Classroom, on_delete=models.SET_NULL, null=True, related_name='emergencies')

    missing_students = models.ManyToManyField(Student, related_name='missing')
    missing = models.BooleanField(default=False)

    submitted_by = models.ForeignKey(BaseUser, on_delete=models.SET_NULL, null=True, related_name='submitted_emergencies')

    def __str__(self):
        return f"{self.emergency} on {self.date}"

    class Meta:
        ordering = ['-date']
        indexes = [models.Index(fields=['date'])] 

    def clean(self):
        super().clean()

        if self.submitted_by and self.submitted_by.role not in ['PRINCIPAL', 'ADMIN', 'TEACHER']:
            raise ValidationError('Submitted by user must be an Admin or Teacher.')
