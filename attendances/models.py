# django 
from django.db import models, IntegrityError
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError

# models
from users.models import BaseUser, Student
from schools.models import School
from classrooms.models import Classroom


class Attendance(models.Model):
    date = models.DateTimeField(auto_now_add=True)

    classroom = models.ForeignKey(Classroom, on_delete=models.SET_NULL, null=True, related_name='attendances')
    
    absent_students = models.ManyToManyField(Student, related_name='absences')
    absentes = models.BooleanField(default=False)

    late_students = models.ManyToManyField(Student, related_name='late_arrivals')

    submitted_by = models.ForeignKey(BaseUser, on_delete=models.SET_NULL, null=True, related_name='submitted_attendances')

    school = models.ForeignKey(School, on_delete=models.CASCADE, editable=False, related_name='attendances', help_text='School to which the attendace belong.')

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['date', 'classroom'], name='unique_date_classroom')
        ]
        unique_together = ('date', 'classroom')
        ordering = ['-date']
        indexes = [models.Index(fields=['date', 'classroom'])]  # Index for performance
        
    def save(self, *args, **kwargs):
        """
        Overrides the save method to run custom validation logic via the `clean` method.
        Also handles potential integrity errors related to unique constraints.
        """
        self.clean()

        try:
            super().save(*args, **kwargs)

        except IntegrityError as e:
            # Check if the error is related to unique constraints
            if 'unique_date_classroom' in str(e).lower():
                raise ValidationError(_('attendance has already been taken for this classroom today, instead submit late arrivals.'))
            else:
                # Re-raise the original exception if it's not related to unique constraints
                raise

        except Exception as e:
            raise ValidationError(_(str(e).lower()))

    def clean(self):
        if self.submitted_by and self.submitted_by.role not in ['PRINCIPAL', 'ADMIN', 'TEACHER']:
            raise ValidationError('only principals, admins or teachers can submit a classrooms attendance record')


class EmergencyAttendance(models.Model):
    date = models.DateTimeField(auto_now_add=True)

    emergency = models.CharField(max_length=124, default='fire drill')
    emergency_location = models.CharField(max_length=124, default='')

    special_instructions = models.TextField()

    classroom = models.ForeignKey(Classroom, on_delete=models.SET_NULL, null=True, related_name='emergencies')

    missing_students = models.ManyToManyField(Student, related_name='missing')
    missing = models.BooleanField(default=False)

    submitted_by = models.ForeignKey(BaseUser, on_delete=models.SET_NULL, null=True, related_name='submitted_emergencies')

    school = models.ForeignKey(School, on_delete=models.CASCADE, editable=False, related_name='emergencies', help_text='School to which the emergency belongs.')

    def __str__(self):
        return f"{self.emergency} on {self.date}"

    class Meta:
        ordering = ['-date']
        indexes = [models.Index(fields=['date'])] 

    def clean(self):
        if self.submitted_by and self.submitted_by.role not in ['PRINCIPAL', 'ADMIN', 'TEACHER']:
            raise ValidationError('only principals, admins or teachers can submit a classroom attendance record')
