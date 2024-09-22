# python 
import uuid

# django 
from django.db import models, IntegrityError
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

class Grade(models.Model):

    # grade level
    grade = models.CharField(_('school grade'), choices=SCHOOL_GRADES_CHOICES, max_length=4, editable=False)
    grade_order = models.PositiveIntegerField() # used for odering grades

    student_count = models.IntegerField(default=0)

    # set by school
    major_subjects = models.PositiveIntegerField() # how many major subjects a student in the grade needs to fail to fail a term
    none_major_subjects = models.PositiveIntegerField() # how many none major subjects a student in the grade needs to fail to fail a term

    last_updated = models.DateTimeField(auto_now_add=True)

    # school linked to
    school = models.ForeignKey(School, on_delete=models.CASCADE, editable=False, related_name='grades')
    
    last_updated = models.DateTimeField(auto_now=True)

    # grade  id 
    grade_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)

    class Meta:
        unique_together = ('school', 'grade') # this will prevent the creation of duplicate grades within the same school
        ordering = ['grade_order']
        indexes = [models.Index(fields=['grade', 'school'])]  # Index for performance

    def __str__(self):
        return f"Grade {self.grade} (Order: {self.grade_order})"
    
    def clean(self):
        """
        Ensure that major_subjects and non-major_subjects are non-negative and logically valid.
        """
        if self.major_subjects < 0 or self.none_major_subjects < 0:
            raise ValidationError(_('Major subjects and non-major subjects must be non-negative integers.'))

        if self.major_subjects + self.none_major_subjects <= 0:
            raise ValidationError(_('There must be at least one major or non-major subject for the grading criteria.'))
        
        # Grade validation
        if not self.grade:
            raise ValidationError(_('grades need to have a grade level'))

        if self.school.type == 'PRIMARY' and int(self.grade) > 7:
            raise ValidationError(_('primary schools cannot assign grades higher than 7'))

        if self.school.type == 'SECONDARY' and int(self.grade) <= 7:
            raise ValidationError(_('secondary schools must assign grades higher than 7'))


    def save(self, *args, **kwargs):
        """
        Override save method to validate incoming data and set grade_order.
        """
        if not self.pk:
            # Set grade_order only for new instances
            if self.grade:
                try:
                    grade_keys = [choice[0] for choice in SCHOOL_GRADES_CHOICES]
                    self.grade_order = grade_keys.index(self.grade)
                except ValueError:
                    raise ValidationError(_('the provided grade level is invalid'))
                
            else:
                raise ValidationError(_('validation error, a grade cannot have an empty level'))
            
            if not self.school:
                raise ValidationError(_('validation error, a grade needs to be associated with a school'))
            
        self.clean()

        try:
            super().save(*args, **kwargs)
        except IntegrityError as e:
            error_message = str(e).lower()
            # Check if the error is related to unique constraints
            if 'unique constraint' in error_message:
                raise ValidationError(_('the provided grade already exists for your school, duplicate grades are not permitted. please choose a different grade.'))
            
            elif 'foreign key constraint' in error_message:
                raise ValidationError(_('The school referenced does not exist. please check and select a valid school'))
            
            elif 'check constraint' in error_message:
                raise ValidationError(_('The data provided does not meet the required constraints. please review and correct the provided information'))

            # Re-raise the original exception if it's not handled
            raise

    