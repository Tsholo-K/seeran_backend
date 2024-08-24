# python 
import uuid

# django
from django.core.exceptions import ValidationError
from django.db import models, IntegrityError
from django.utils.translation import gettext_lazy as _

# models
from users.models import BaseUser, Teacher, Student
from schools.models import School
from grades.models import Grade, Subject


class Classroom(models.Model):
    """
    Model representing a classroom in a school.

    Attributes:
        classroom_identifier (str): Identifier for the classroom, e.g., '1', '2A'.
        group (str): Group designation for the classroom, e.g., 'A', 'B'.
        teacher (CustomUser): ForeignKey to CustomUser model representing the teacher of the classroom.
        students (ManyToManyField): Many-to-many relationship with CustomUser model representing enrolled students.
        parents (ManyToManyField): Many-to-many relationship with CustomUser model representing parents of students.
        grade (Grade): ForeignKey to Grade model representing the grade level of the classroom.
        register_class (bool): Boolean indicating if the classroom is a register class.
        subject (Subject): ForeignKey to Subject model representing the subject taught in the classroom.
        school (School): ForeignKey to School model representing the school to which the classroom belongs.
        class_id (str): Unique identifier for the classroom, generated automatically.

    Methods:
        clean(): Custom validation method to ensure data integrity before saving.
        save(*args, **kwargs): Override save method to generate class_id if not provided and validate data.
        generate_unique_id(prefix=''): Static method to generate a unique class_id using UUID.

    Meta:
        verbose_name = 'classroom'
        verbose_name_plural = 'classrooms'

    """

    classroom_number = models.CharField(_('classroom identifier'), max_length=16, default='1')
    group = models.CharField(_('class group'), max_length=16, default='A')

    teacher = models.ForeignKey(Teacher, on_delete=models.SET_NULL, null=True, blank=True, related_name='taught_classes', help_text='The teacher assigned to the classroom.')
    students = models.ManyToManyField(Student, limit_choices_to={'role': 'STUDENT'}, related_name='enrolled_classes', help_text='Students enrolled in the classroom.')

    student_count = models.IntegerField(default=0)

    grade = models.ForeignKey(Grade, on_delete=models.CASCADE, editable=False, related_name='classes', help_text='Grade level associated with the classroom.')

    register_class = models.BooleanField(_('is the class a register class'), editable=False, default=False, help_text='Ensure only one register class per teacher.')
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, editable=False, related_name='classes', null=True, blank=True, help_text='Subject taught in the classroom.')

    school = models.ForeignKey(School, on_delete=models.CASCADE, editable=False, related_name='classes', help_text='School to which the classroom belongs.')

    class_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)

    class Meta:
        unique_together = (
            ('group', 'grade', 'subject'),  # Unique combination in subject classes
            ('group', 'grade', 'register_class')  # Unique combination in register classes
        ) 

    def __str__(self):
        return f"{self.school} - Grade {self.grade} - {self.classroom_number}"
    
    def clean(self):
        if not self.subject and not self.register_class:
            raise ValidationError("a classroom needs to either be a register class or be associated with one subject in your school")

        if self.subject:
            if self.subject.grade != self.grade:
                return {"error": "could not proccess request. the specified subject's grade and the classrooms grade are different"}
                
    def save(self, *args, **kwargs):
        """
        Override save method to validate incoming data.
        """
        self.clean()

        try:
            super().save(*args, **kwargs)

        except IntegrityError as e:
            # Check if the error is related to unique constraints
            if 'unique constraint' in str(e).lower():
                raise ValidationError(_('a combination of classroom group, grade, subject/register already exists for your school. Duplicate classroom groups in the same grade and subject/register are not permitted.'))
            else:
                # Re-raise the original exception if it's not related to unique constraints
                raise

    def update_students(self, students_list=None, remove=False):
        """
        Add or remove the provided list of students (by account_id) to/from the class and update the students count.

        Args:
            students_list (list): List of student account IDs.
            remove (bool): Indicates if students should be removed.
        """
        if students_list:
            # Retrieve CustomUser instances corresponding to the account_ids
            students = self.school.students.prefetch_related('enrolled_classes__subject').filter(account_id__in=students_list)

            if not students.exists():
                return "no valid students found with the provided account IDs."
            
            if remove:
                # Check if students to be removed are actually in the class
                existing_students = self.students.filter(account_id__in=students_list).values_list('account_id', flat=True)
                if not existing_students:
                    return "could not proccess your request, all the provided students are not part of this classroom"

            else:
                # Check if students are already in a class of the same subject
                if self.subject:
                    students_in_subject = self.grade.students.filter(account_id__in=students_list, enrolled_classes__subject=self.subject).values_list('account_id', flat=True)
                    if students_in_subject:
                        return f'the following students are already assigned to a class in the provided subject and grade: {", ".join(students_in_subject)}'

                # Check if students are already in any register class
                if self.register_class:
                    students_in_register_classes = self.grade.students.filter(account_id__in=students_list, enrolled_classes__register_class=True).values_list('account_id', flat=True)
                    if students_in_register_classes:
                        return f'the following students are already assigned to a register class: {", ".join(students_in_register_classes)}'

                # Check if students are already in this specific class
                existing_students = self.students.filter(account_id__in=students_list).values_list('account_id', flat=True)
                if existing_students:
                    return f'the following students are already in this class: {", ".join(existing_students)}'

            # Proceed with adding or removing students
            if remove:
                self.students.remove(*students)
            else:
                self.students.add(*students)

            # Save the classroom instance first to ensure student changes are persisted
            self.save()

            # Update the students count in the class
            self.student_count = self.students.count()
            self.save()  # Save again to update students_count field

            if self.subject:
                # Update the subject student count
                self.subject.student_count = self.grade.classes.filter(subject=self.subject).aggregate(student_count=models.Count('students'))['student_count'] or 0
                self.subject.save()
            
        else:
            return "Validation error: No students were provided."

    def update_teacher(self, teacher):
        """
        Update the class's teacher and update the subject's teacher count if applicable.
        This method ensures that a teacher can only be assigned to one register class per school.
        """
        try:
            if teacher:
                # Retrieve the CustomUser instance corresponding to the account_id
                teacher = Teacher.objects.prefetch_related('taught_classes__subject').get(account_id=teacher, school=self.school)
            
                # Check if the teacher is already assigned to another register class in the school
                if self.register_class and teacher.taught_classes.filter(register_class=True).exclude(pk=self.pk).exists():
                    raise ValueError("the provided teacher is already assigned to a register class. teachers can only be assigned to one register class in a school")
                
                # Check if the teacher is already assigned to another class in the subject
                elif self.subject and teacher.taught_classes.filter(subject=self.subject).exclude(pk=self.pk).exists():
                    raise ValueError("the provided teacher is already assigned to a class in the provided subject and grade. teachers can not teach more than one class in the same grade and subject")
                
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
                self.subject.teacher_count =  self.grade.classes.filter(subject=self.subject).exclude(teacher=None).values_list('teacher', flat=True).distinct().count()
                self.subject.save()

        except Teacher.DoesNotExist:
            raise ValueError("a teacher account in your school with the provided credentials does not exist. please check the teachers details and try again")
