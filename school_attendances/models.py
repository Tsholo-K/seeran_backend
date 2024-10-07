# python
import uuid

# django 
from django.db import models, IntegrityError
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError

# models
from accounts.models import BaseAccount, Student
from schools.models import School
from classrooms.models import Classroom


class ClassroomAttendanceRegister(models.Model):
    classroom = models.ForeignKey(Classroom, on_delete=models.SET_NULL, null=True, related_name='attendances')
    
    absent_students = models.ManyToManyField(Student, related_name='absences')
    absentes = models.BooleanField(default=False)

    late_students = models.ManyToManyField(Student, related_name='late_arrivals')

    attendance_taker = models.ForeignKey(BaseAccount, on_delete=models.SET_NULL, null=True, related_name='submitted_attendances')

    school = models.ForeignKey(School, on_delete=models.CASCADE, editable=False, related_name='school_attendances', help_text='School to which the attendace belong.')
    
    timestamp = models.DateTimeField(auto_now_add=True)
    # A unique identifier for each attendance (UUID).
    attendance_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['timestamp', 'classroom'], name='unique_date_classroom'),
        ]
        unique_together = ('timestamp', 'classroom')
        ordering = ['-timestamp']
        indexes = [models.Index(fields=['timestamp', 'classroom'])]  # Index for performance
        
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
            raise ValidationError(_(str(e)))

    def clean(self):
        if self.attendance_taker and self.attendance_taker.role not in ['PRINCIPAL', 'ADMIN', 'TEACHER']:
            raise ValidationError('Could not process your request, only principals, admins and the classroom teacher can submit a classrooms attendance register. You do not havev the necessary role to perform this action.')
        if not self.classroom.register_classroom:
            raise ValidationError('Could not process your request, the classroom you are trying to submit an attendance register for is not a register classroom. Attendance register can only be submitted for register classrooms, review the classroom details and try again.')
        if self.absentes and self.late_students and self.absent_students.filter(id__in=self.late_students.values_list('id', flat=True)).exists():
            raise ValidationError('Could not process your request, a student cannot be both late and absent for any one day in the school day. Please review the list of submitted students and then try again.')

    def update_attendance_register(self, students=None, absent=False):
        try:
            if absent:
                if students:
                    # Check if students to be removed are actually in the class
                    present_students = self.classroom.students.filter(account_id__in=students).values_list('id', flat=True)
                    if not present_students:
                        raise ValidationError("Could not proccess your request, none of the provided students are part of this classroom. Please review the list of students and try again.")
                    
                    absent_students = self.classroom.students.exclude(account_id__in=students).values_list('id', flat=True)
                
                else:
                    absent_students = self.classroom.students.values_list('id', flat=True)
                    
                if absent_students:
                    self.absentes = True
                    self.absent_students.add(*absent_students)

            else:
                if students:
                    # Check if students are already marked as absent
                    late_students = self.absent_students.filter(account_id__in=students).values_list('id', flat=True)
                    if not late_students:
                        raise ValidationError(f"Could not proccess your request, the the provided list of students have not been marked as absent for this classroom. Please review the list of students and try again.")

                    self.absent_students.remove(*late_students)
                    # Add the students by their primary keys
                    self.late_students.add(*late_students)
                
                else:
                    raise ValidationError(f"Could not proccess your request, no students were provided to be marked as late. Please review the provided list of students and try again.")

            # Save the classroom instance first to ensure student changes are persisted
            self.save()

        except Exception as e:
            raise ValidationError(_(str(e)))  # Catch and raise any exceptions as validation errors

# class EmergencyAttendance(models.Model):
#     date = models.DateTimeField(auto_now_add=True)

#     emergency = models.CharField(max_length=124, default='fire drill')
#     emergency_location = models.CharField(max_length=124, default='')

#     special_instructions = models.TextField()

#     classroom = models.ForeignKey(Classroom, on_delete=models.SET_NULL, null=True, related_name='emergencies')

#     missing_students = models.ManyToManyField(Student, related_name='missing')
#     missing = models.BooleanField(default=False)

#     submitted_by = models.ForeignKey(BaseAccount, on_delete=models.SET_NULL, null=True, related_name='submitted_emergencies')

#     school = models.ForeignKey(School, on_delete=models.CASCADE, editable=False, related_name='emergencies', help_text='School to which the emergency belongs.')

#     def __str__(self):
#         return f"{self.emergency} on {self.date}"

#     class Meta:
#         ordering = ['-date']
#         indexes = [models.Index(fields=['date'])] 

#     def clean(self):
#         if self.submitted_by and self.submitted_by.role not in ['PRINCIPAL', 'ADMIN', 'TEACHER']:
#             raise ValidationError('only principals, admins or teachers can submit a classroom attendance record')
