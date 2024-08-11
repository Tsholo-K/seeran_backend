# python 
import uuid

# django
from django.core.exceptions import ValidationError
from django.db import models
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

    classroom_identifier = models.CharField(_('classroom identifier'), max_length=16, default='1')
    group = models.CharField(_('class group'), max_length=16, default='A')

    teacher = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, limit_choices_to={'role': 'teacher'}, null=True, blank=True, related_name='taught_classes', help_text='The teacher assigned to the classroom.')
    students = models.ManyToManyField(CustomUser, related_name='enrolled_classes', help_text='Students enrolled in the classroom.')
    parents = models.ManyToManyField(CustomUser, related_name='children_classes', help_text='Parents or guardians of students in the classroom.')

    grade = models.ForeignKey(Grade, on_delete=models.CASCADE, related_name='grade_classes', help_text='Grade level associated with the classroom.')

    register_class = models.BooleanField(_('is the class a register class'), unique=True, default=False, help_text='Ensure only one register class per teacher.')
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='subject_classes', null=True, blank=True, help_text='Subject taught in the classroom.')

    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='classes', help_text='School to which the classroom belongs.')

    class_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)

    class Meta:
        verbose_name = _('classroom')
        verbose_name_plural = _('classrooms')

    def __str__(self):
        return f"{self.school} - Grade {self.grade} - {self.classroom_identifier}"


