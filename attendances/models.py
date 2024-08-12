# django
from django.db import models

# models
from classes.models import Classroom
from users.models import CustomUser

class Absent(models.Model):
    date = models.DateTimeField(auto_now_add=True)

    classroom = models.ForeignKey(Classroom, on_delete=models.SET_NULL, null=True, related_name='attendances')
    
    absent_students = models.ManyToManyField(CustomUser, related_name='absences')
    absentes = models.BooleanField(default=False) # helps in querying 

    submitted_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, related_name='submitted_attendances')


class Late(models.Model):
    date = models.DateTimeField(auto_now_add=True)

    classroom = models.ForeignKey(Classroom, on_delete=models.SET_NULL, null=True, related_name='late_arrivals')
    late_students = models.ManyToManyField(CustomUser, related_name='late_arrivals')

    submitted_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, related_name='submitted_late_arrivals')


class Emergency(models.Model):
    date = models.DateTimeField(auto_now_add=True)

    emergency = models.CharField(max_length=124, default='fire drill')
    emergency_location = models.CharField(max_length=124, default='')

    special_instructions = models.TextField()

    classroom = models.ForeignKey(Classroom, on_delete=models.SET_NULL, null=True, related_name='emergencies')

    missing_students = models.ManyToManyField(CustomUser, related_name='missing')
    missing = models.BooleanField(default=False)

    submitted_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, related_name='submitted_emergencies')