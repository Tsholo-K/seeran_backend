# python 
import uuid

# django 
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError

# models
from schools.models import School


# grade choices
SCHOOL_GRADES_CHOICES = [
    ('000', 'Grade 000'), 
    ('00', 'Grade 00'), 
    ('R', 'Grade R'), 
    ('1', 'Grade 1'), 
    ('2', 'Grade 2'), 
    ('3', 'Grade 3'), 
    ('4', 'Grade 4'), 
    ('5', 'Grade 5'), 
    ('6', 'Grade 6'), 
    ('7', 'Grade 7'), 
    ('8', 'Grade 8'), 
    ('9', 'Grade 9'), 
    ('10', 'Grade 10'), 
    ('11', 'Grade 11'), 
    ('12', 'Grade 12')
]

# subject choices
SCHOOL_SUBJECTS_CHOICES = [
    ('ENGLISH', 'English'),
    ('SEPEDI', 'Sepedi'),
    ('ZULU', 'Zulu'),
    ('AFRIKAANS', 'Afrikaans'),
    ('MATHEMATICS', 'Mathematics'),
    ('MATHEMATICS LITERACY', 'Mathematics Literacy'),
    ('TECHNICAL MATHEMATICS', 'Technical Mathematics'),
    ('PHYSICAL SCIENCE', 'Physical Science'),
    ('LIFE SCIENCE', 'Life Science'),
    ('BIOLOGY', 'Biology'),
    ('GEOGRAPHY', 'Geography'),
    ('ACCOUNTING', 'Accounting'),
    ('BUSINESS STUDIES', 'Business Studies'),
    ('AGRICULTURE', 'Agriculture'),
    ('TOURISM', 'Tourism'),
    ('LIFE ORIENTATION', 'Life Orientation'),
    ('SOCIAL SCIENCE', 'Social Science'),
    ('ARTS AND CULTURE', 'Arts And Culture'),
]

class Grade(models.Model):

    # grade level
    grade = models.CharField(_('school grade'), choices=SCHOOL_GRADES_CHOICES, max_length=4, default="8")
    grade_order = models.PositiveIntegerField() # used for odering grades 

    # set by school
    major_subjects = models.PositiveIntegerField() # how many major subjects a student in the grade can fail to get a failing grade
    none_major_subjects = models.PositiveIntegerField() # how many none major subjects a student in the grade can fail to get a failing grade
    
    # school linked to
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='school_grades')

    # grade  id 
    grade_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)

    class Meta:
        unique_together = ('school', 'grade') # this will prevent the creation of duplicate grades within the same school
        ordering = ['grade_order']
        indexes = [models.Index(fields=['grade', 'school'])]  # Index for performance

    def __str__(self):
        return self.grade_id
    
    def clean(self):
        """
        Ensure that major_subjects and non-major_subjects are non-negative and logically valid.
        """
        if self.major_subjects < 0 or self.none_major_subjects < 0:
            raise ValidationError(_('Major subjects and non-major subjects must be non-negative integers.'))

        if self.major_subjects + self.none_major_subjects <= 0:
            raise ValidationError(_('There must be at least one major or non-major subject for the grading criteria.'))

    def save(self, *args, **kwargs):
        """
        Override save method to validate incoming data and set grade_order.
        """
        if not self.pk:
            # Set grade_order only for new instances
            if self.grade:
                try:
                    self.grade_order = [choice[0] for choice in SCHOOL_GRADES_CHOICES].index(self.grade)
                except ValueError:
                    raise ValidationError(_('Invalid grade value.'))
                
            else:
                raise ValidationError(_('a grade cannot have an empty level.'))

        self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Grade {self.grade} (Order: {self.grade_order})"
    
    
class Subject(models.Model):

    # grade linked to
    grade = models.ForeignKey(Grade, on_delete=models.CASCADE, related_name='grade_subjects')
    subject = models.CharField(_('grade subject'), max_length=64, choices=SCHOOL_SUBJECTS_CHOICES, default="ENGLISH")

    # field to indicate if it's a major subject
    major_subject = models.BooleanField(default=False)
    # subject-specific pass mark
    pass_mark = models.DecimalField(max_digits=5, decimal_places=2, default=40.00)

    # subject id
    subject_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)

    class Meta:
        unique_together = ('grade', 'subject')
        ordering = ['subject']
        indexes = [models.Index(fields=['subject', 'grade', 'school'])]  # Index for performance

    def __str__(self):
        return self.subject

    def clean(self):
        """
        Validate that the pass mark is within a reasonable range.
        """
        if not (0 <= self.pass_mark <= 100):
            raise ValidationError(_('the subjects pass mark must be between 0 and 100'))

    def save(self, *args, **kwargs):
        """
        Override save method to validate incoming data.
        """
        self.clean()
        super().save(*args, **kwargs)
