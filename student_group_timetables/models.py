# python 
import uuid

# django 
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError


class StudentGroupTimetable(models.Model):
    group_name = models.CharField(max_length=64)
    description = models.TextField(max_length=1024, null=True, blank=True)

    subscribers = models.ManyToManyField('accounts.Student', related_name='timetables')
    
    students_count = models.PositiveIntegerField(default=0)
    timetables_count = models.PositiveIntegerField(default=0)
 
    grade = models.ForeignKey('grades.Grade', on_delete=models.CASCADE, related_name='group_timetables')
    
    school = models.ForeignKey('schools.School', on_delete=models.CASCADE, related_name='group_timetables')

    last_updated = models.DateTimeField(auto_now=True)

    timestamp = models.DateTimeField(auto_now_add=True)
    group_timetable_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)

    class Meta:
        ordering = ['group_name']

    def __str__(self):
        return self.group_timetable_id
    
    def update_subscribers(self, student_ids=None, subscribe=False):
        try:
            if student_ids:
                if subscribe:
                    # Check if students are already in this specific group timetable
                    students_in_the_group = self.subscribers.filter(account_id__in=student_ids).values_list('surname', 'name')
                    if students_in_the_group:
                        student_names = [f"{surname} {name}" for surname, name in students_in_the_group]
                        raise ValidationError(f'the following students are already in this group timetable: {", ".join(student_names)}')

                    # Retrieve CustomUser instances corresponding to the account_ids
                    students = self.grade.students.filter(account_id__in=student_ids)

                    if not students.exists():
                        raise ValidationError("Could not proccess your request, no valid students were found in the provided list of student account IDs.")
                    
                    self.subscribers.add(students)

                else:
                    # Check if students to be removed are actually in the class
                    existing_students = self.subscribers.filter(account_id__in=student_ids)
                    if not existing_students.exists():
                        raise ValidationError("could not proccess your request, all the provided students are not part of this classroom")
                    
                    self.subscribers.remove(existing_students)

                # Save the classroom instance first to ensure student changes are persisted
                self.save()

                # Update the students count in the class
                self.student_count = self.subscribers.count()
                self.save()  # Save again to update students_count field
            else:
                raise ValidationError(f"Could not proccess your request, no students were provided to be {'subscribed to' if subscribe else 'unsubscribed from'} the group timetable. please provide a valid list of students and try again")
        except Exception as e:
            raise ValidationError(_(str(e)))  # Catch and raise any exceptions as validation errors