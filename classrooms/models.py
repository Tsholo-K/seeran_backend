# python 
import uuid

# django
from django.core.exceptions import ValidationError
from django.db import models, IntegrityError
from django.utils.translation import gettext_lazy as _

# models
from accounts.models import Teacher, Student
from schools.models import School
from grades.models import Grade
from subjects.models import Subject


class Classroom(models.Model):
    """
    Model representing a classroom in a school. This classroom could either be 
    a register class (the main homeroom class for students) or a subject-specific class.
    
    Attributes:
        classroom_number: Identifies the classroom, typically a unique number or code.
        group: Represents the class group, e.g., "A", "B".
        teacher: The teacher assigned to the classroom.
        students: The students enrolled in this classroom.
        student_count: Count of students in the classroom.
        register_class: Boolean indicating if this is a register class (homeroom).
        subject: The subject taught in this classroom.
        grade: The grade level of the classroom (e.g., Grade 1, Grade 2).
        school: The school to which the classroom belongs.
        last_updated: Timestamp indicating the last update to this classroom's information.
        classroom_id: A unique UUID for identifying the classroom.
    """
    
    classroom_number = models.CharField(_('classroom identifier'), max_length=16, default='1')
    group = models.CharField(_('class group'), max_length=16, default='A')

    teacher = models.ForeignKey(Teacher, on_delete=models.SET_NULL, null=True, blank=True, related_name='taught_classrooms', help_text='The teacher assigned to the classroom.')
    students = models.ManyToManyField(Student, related_name='enrolled_classrooms', help_text='Students enrolled in the classroom.')

    student_count = models.PositiveIntegerField(default=0)

    register_classroom = models.BooleanField(_('is the class a register class'), editable=False, default=False, help_text='Ensure only one register class per teacher.')
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, editable=False, related_name='classrooms', null=True, blank=True, help_text='Subject taught in the classroom.')

    grade = models.ForeignKey(Grade, on_delete=models.CASCADE, editable=False, related_name='classrooms', help_text='Grade level associated with the classroom.')

    school = models.ForeignKey(School, on_delete=models.CASCADE, editable=False, related_name='classrooms', help_text='School to which the classroom belongs.')
    
    last_updated = models.DateTimeField(auto_now=True)

    timestamp = models.DateTimeField(auto_now_add=True)
    classroom_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['group', 'grade', 'subject'], name='unique_group_grade_subject_classroom'),
            models.UniqueConstraint(fields=['group', 'grade', 'register_classroom'], name='unique_group_grade_register_classroom')
        ]

    def __str__(self):
        return f"{self.school} - Grade {self.grade} - {self.classroom_number}"
                
    def save(self, *args, **kwargs):
        """
        Custom save method:
        - Validate before saving.
        - Provide meaningful error messages on IntegrityError.
        """
        self.clean()
        try:
            super().save(*args, **kwargs)
        except IntegrityError as e:
            # Handle any database integrity errors (such as unique or foreign key constraints).
            error_message = str(e).lower()
            # Check for unique constraint violations.
            if 'unique constraint' in error_message:
                if 'classrooms_classroom.subject' in error_message:
                    raise ValidationError(_('Could not proccess your request, a classroom with the provided group, grade, and subject already exists. Please choose a different classroom group and try again.'))
                elif 'classrooms_classroom.register_classroom' in error_message:
                    raise ValidationError(_('Could not proccess your request, a register class with the provided group and grade already exists. Each grade can only have one register class per group. Please choose a different group.'))
            # Re-raise the original exception if it's not related to unique constraints
            raise
        except Exception as e:
            raise ValidationError(_(str(e)))  # Catch and raise any exceptions as validation errors

    def clean(self):
        if not self.school_id:
            raise ValidationError('Could not proccess your request, a classroom must either be a register classroom or be associated with a subject. Please review the provided information and try again.')
        
        elif not self.grade_id:
            raise ValidationError('Could not proccess your request, a classroom must either be a register classroom or be associated with a subject. Please review the provided information and try again.')
        
        elif not self.subject_id and not self.register_classroom:
            raise ValidationError('Could not proccess your request, a classroom must either be a register classroom or be associated with a subject. Please review the provided information and try again.')

        elif self.subject_id and self.subject.grade != self.grade:
            raise ValidationError('Could not proccess your request, the subject associated with this classroom is assigned to a different grade. Ensure that the subject belongs to the same grade as the classroom.')

    def update_students(self, students=None, remove=False):
        try:
            if students:                
                if remove:
                    # Check if students to be removed are actually in the class
                    existing_students = self.students.filter(account_id__in=students).values_list('id', flat=True)
                    if not existing_students.exists():
                        raise ValidationError("could not proccess your request, non of the provided students are part of this classroom.")
                    self.students.remove(*existing_students)

                else:
                    # Check if students are already in a class of the same subject
                    if self.subject:
                        students_in_subject_classrooms = self.grade.students.filter(account_id__in=students, enrolled_classrooms__subject=self.subject).values_list('surname', 'name')
                        if students_in_subject_classrooms:
                            student_names = [f"{surname} {name}" for surname, name in students_in_subject_classrooms]
                            raise ValidationError(f'the following students are already assigned to a classroom in the provided subject and grade: {", ".join(student_names)}')

                    # Check if students are already in any register class
                    elif self.register_classroom:
                        students_in_register_classrooms = self.grade.students.filter(account_id__in=students, enrolled_classrooms__register_classroom=True).values_list('surname', 'name')
                        if students_in_register_classrooms:
                            student_names = [f"{surname} {name}" for surname, name in students_in_register_classrooms]
                            raise ValidationError(f'the following students are already assigned to a register classroom: {", ".join(student_names)}')

                    # Check if students are already in this specific class
                    students_in_provided_classroom = self.students.filter(account_id__in=students).values_list('surname', 'name')
                    if students_in_provided_classroom:
                        student_names = [f"{surname} {name}" for surname, name in students_in_provided_classroom]
                        raise ValidationError(f'the following students are already in this classroom: {", ".join(student_names)}')
                    
                    # Get the list of student primary keys
                    students_in_grade = self.grade.students.filter(account_id__in=students).values_list('id', flat=True)

                    # Add the students by their primary keys
                    self.students.add(*students_in_grade)

                # Save the classroom instance first to ensure student changes are persisted
                self.save()

                # Update the students count in the class
                self.student_count = self.students.count()
                self.save()  # Save again to update students_count field

                if self.subject:
                    # Update the subject student count
                    self.subject.student_count = self.grade.classrooms.filter(subject=self.subject).aggregate(student_count=models.Count('students'))['student_count'] or 0
                    self.subject.save()
            else:
                raise ValidationError("could not proccess your request, no students were provided to be added or removed from the classroom. please provide a valid list of students and try again")
        except Exception as e:
            raise ValidationError(_(str(e)))  # Catch and raise any exceptions as validation errors


    def update_teacher(self, teacher=None):
        try:
            if teacher:
                # Retrieve the CustomUser instance corresponding to the account_id
                teacher = Teacher.objects.get(account_id=teacher, school=self.school)
            
                # Check if the teacher is already assigned to another register class in the school
                if self.register_classroom and teacher.taught_classrooms.filter(register_classroom=True).exclude(pk=self.pk).exists():
                    raise ValidationError("could not proccess your request, the provided teacher is already assigned to a register classroom. teachers can only be assigned to one register classroom in a school")
                
                # Check if the teacher is already assigned to another class in the subject
                elif self.subject and teacher.taught_classrooms.filter(subject=self.subject).exclude(pk=self.pk).exists():
                    raise ValidationError("could not proccess your request, the provided teacher is already assigned to a classroom in the provided subject and grade. teachers can not teach more than one classroom in the same grade and subject")
                
                # Assign the teacher to the classroom
                self.teacher = teacher
            else:
                # Remove the teacher assignment
                self.teacher = None

            # Save the classroom instance with the updated teacher
            self.save()
            
            # Update the teacher count in the subject if applicable
            if self.subject:
                # Count unique teachers assigned to classrooms for this subject
                self.subject.teacher_count =  self.grade.classrooms.filter(subject=self.subject).exclude(teacher=None).values_list('teacher', flat=True).distinct().count()
                self.subject.save()

        except Teacher.DoesNotExist:
            raise ValidationError("a teacher account in your school with the provided credentials does not exist. please check the teachers details and try again")
