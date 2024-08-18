# python 
import uuid

# django
from django.core.exceptions import ValidationError
from django.db import models, IntegrityError
from django.utils.translation import gettext_lazy as _

# models
from users.models import CustomUser
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

    teacher = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, limit_choices_to={'role': 'TEACHER'}, null=True, blank=True, related_name='taught_classes', help_text='The teacher assigned to the classroom.')
    students = models.ManyToManyField(CustomUser, limit_choices_to={'role': 'STUDENT'}, related_name='enrolled_classes', help_text='Students enrolled in the classroom.')
    parents = models.ManyToManyField(CustomUser, related_name='children_classes', help_text='Parents or guardians of students in the classroom.')

    student_count = models.IntegerField(default=0)

    grade = models.ForeignKey(Grade, on_delete=models.CASCADE, related_name='grade_classes', help_text='Grade level associated with the classroom.')

    register_class = models.BooleanField(_('is the class a register class'), default=False, help_text='Ensure only one register class per teacher.')
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='subject_classes', null=True, blank=True, help_text='Subject taught in the classroom.')

    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='classes', help_text='School to which the classroom belongs.')

    class_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)

    class Meta:
        unique_together = (
            ('group', 'grade', 'subject'),  # Unique combination in subject classes
            ('group', 'grade', 'register_class')  # Unique combination in register classes
        ) 

    def __str__(self):
        return f"{self.school} - Grade {self.grade} - {self.classroom_number}"
    
    def clean(self):
        # Validate unique group in subject/register classes
        if self.register_class:
            if Classroom.objects.filter(group=self.group, grade=self.grade, school=self.school, register_class=True).exclude(pk=self.pk).exists():
                raise ValidationError("a register class with the same group in the same grade already exists.. duplicate groups in the same register and grade is not permitted")
        else:
            if self.subject:
                if Classroom.objects.filter(group=self.group, grade=self.grade, subject=self.subject, school=self.school).exclude(pk=self.pk).exists():
                    raise ValidationError("a class with the same group in the same subject and grade already exists. duplicate groups in the same subject and grade is not permitted")
                
                if self.subject.grade != self.grade:
                    return {"error": "could not proccess request. the specified subject's grade and the classrooms grade are different"}

            else:
                raise ValidationError("a class needs to either be a register class or be added to a subject")
                
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
                raise ValidationError(_('a combination of group, grade, subject/register already exists for your school. Duplicate classroom groups in the same grade and subject/register are not permitted.'))
            else:
                # Re-raise the original exception if it's not related to unique constraints
                raise

    def update_students(self, students_list=None, remove=False):
        """
        Add the provided list of students (by account_id) to the class and update the students count.
        """
        if students_list:
            # Retrieve the CustomUser instances corresponding to the account_ids
            students = CustomUser.objects.filter(account_id__in=students_list, role='STUDENT')
            
            if not students.exists():
                raise ValueError("No valid students found with the provided account_ids.")
            
            if remove:
                self.students.remove(*students)
            else:
                self.students.add(*students)

            self.students_count = self.students.count()

            if self.subject:
                self.subject.student_count = self.grade.grade_classes.filter(subject=self.subject).aggregate(count=models.Sum('students__count'))['count'] or 0
                self.subject.save()
            
            self.save()
        else:
            raise ValueError("validation error.. no students were provided.")

    def update_teacher(self, teacher=None):
        """
        Update the class's teacher and update the subject's teacher count if applicable.
        This method ensures that a teacher can only be assigned to one register class per school.
        """
        if teacher:
            # Check if the teacher is already assigned to another register class in the school
            if self.register_class and teacher.taught_classes.filter(register_class=True).exclude(pk=self.pk).exists():
                raise ValueError("the provided teacher is already assigned to a register class. teachers can only be assigned to one register class in a school")
            
            # Assign the teacher to the classroom
            self.teacher = teacher
        else:
            # Check if the teacher is already assigned to another class in the subject
            if self.subject and teacher.taught_classes.filter(subject=self.subject).exclude(pk=self.pk).exists():
                raise ValueError("the provided teacher is already assigned to a class in this grade and subject. teachers can not teach more than one class in the same grade and subject")

            # Remove the teacher assignment
            self.teacher = None

        # Update the teacher count in the subject if applicable
        if self.subject:
            # Count unique teachers assigned to classrooms for this subject
            self.subject.teacher_count = self.grade.grade_classes.filter(subject=self.subject).values_list('teacher', flat=True).distinct().count()
            self.subject.save()

        # Save the classroom instance with the updated teacher
        self.save()
