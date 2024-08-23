# python 
import uuid
from datetime import timedelta
from decimal import Decimal

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

    student_count = models.IntegerField(default=0)

    # set by school
    major_subjects = models.PositiveIntegerField() # how many major subjects a student in the grade needs to fail to fail a term
    none_major_subjects = models.PositiveIntegerField() # how many none major subjects a student in the grade needs to fail to fail a term
    
    # school linked to
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='school_grades')

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
            
        self.clean()

        try:
            super().save(*args, **kwargs)
        except IntegrityError as e:
            # Check if the error is related to unique constraints
            if 'unique constraint' in str(e).lower():
                raise ValidationError(_('the provided grade already exists for your school. duplicate grades are not permitted'))
            else:
                # Re-raise the original exception if it's not related to unique constraints
                raise


class Term(models.Model):

    # the term number
    term = models.IntegerField(editable=False, default=1)
    # Weight of the term in final year calculations in relation to other terms
    weight = models.DecimalField(max_digits=5, decimal_places=2)

    # The first day of the term
    start_date = models.DateField()
    # The final day of the term
    end_date = models.DateField()

    # number of school days in the term
    school_days = models.IntegerField(default=0)

    # grade linked to
    grade = models.ForeignKey(Grade, on_delete=models.CASCADE, related_name='grade_terms')

    # The school the term is linked to
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='school_terms')

    # term id 
    term_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)

    class Meta:
        unique_together = ('term', 'grade', 'school')
        indexes = [models.Index(fields=['term', 'school'])]

    def __str__(self):
        return f"Term {self.term}"
    
    def clean(self):
        """
        Ensure that the term dates do not overlap with other terms in the same school and validate term dates.
        """
        if Term.objects.filter(school=self.school, grade=self.grade, term=self.term).exclude(pk=self.pk).exists():
            raise ValidationError(f"a term with the provided term number already exists in the school")

        if self.start_date >= self.end_date:
            raise ValidationError(_('a terms start date must be before it\'s end date'))

        overlapping_terms = Term.objects.filter(school=self.school, grade=self.grade, start_date__lt=self.end_date, end_date__gt=self.start_date).exclude(pk=self.pk)
        if overlapping_terms.exists():
            raise ValidationError(_('the provided start and end dates for the term overlap with one or more existing terms'))
        
        total_weight = Term.objects.filter(school=self.school, grade=self.grade).exclude(pk=self.pk).aggregate(total_weight=models.Sum('weight'))['total_weight'] or '0.00'

        # Ensure the total weight does not exceed 100%
        if Decimal(total_weight) + Decimal(self.weight) > Decimal('100.00') or Decimal(total_weight) + Decimal(self.weight) < Decimal('0.00'):
            raise ValidationError(_('The total weight of all terms should be between 0% and 100%.'))
        
        if not self.school_days:
            self.school_days = self.calculate_total_school_days()
        
    def save(self, *args, **kwargs):
        """
        Override save method to calculate the total amount of school days in the term if not provided.
        """

        self.clean()

        try:
            super().save(*args, **kwargs)
        except IntegrityError as e:
            # Check if the error is related to unique constraints
            if 'unique constraint' in str(e).lower():
                raise ValidationError(_('a term with the specified term number in the specified grade is already there for your school. Duplicate terms within the same grade and school is not permitted.'))
            else:
                # Re-raise the original exception if it's not related to unique constraints
                raise

        except Exception as e:
            raise ValidationError(_(str(e).lower()))

    def calculate_total_school_days(self):
        """
        Calculate the total number of school days (weekdays) between start_date and end_date, excluding weekends.
        """
        start_date = self.start_date
        end_date = self.end_date

        total_days = 0
        current_date = start_date

        while current_date <= end_date:
            if current_date.weekday() < 5:  # Monday to Friday are considered school days
                total_days += 1
            current_date += timedelta(days=1)

        return total_days


class Subject(models.Model):

    # grade linked to
    grade = models.ForeignKey(Grade, on_delete=models.CASCADE, related_name='grade_subjects')
    subject = models.CharField(_('grade subject'), max_length=64, choices=SCHOOL_SUBJECTS_CHOICES, default="ENGLISH")

    student_count = models.IntegerField(default=0)
    teacher_count = models.IntegerField(default=0)
    classes_count = models.IntegerField(default=0)

    # field to indicate if it's a major subject
    major_subject = models.BooleanField(default=False)
    # subject-specific pass mark
    pass_mark = models.DecimalField(max_digits=5, decimal_places=2, default=40.00)

    # subject id
    subject_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)

    class Meta:
        unique_together = ('grade', 'subject')
        ordering = ['subject']
        indexes = [
            models.Index(fields=['subject', 'grade'])
        ]  # Index for performance

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
            
        try:
            super().save(*args, **kwargs)
        except IntegrityError as e:
            # Check if the error is related to unique constraints
            if 'unique constraint' in str(e).lower():
                raise ValidationError(_('the provided subject already exists for your school. duplicate subjects are not permitted'))
            else:
                # Re-raise the original exception if it's not related to unique constraints
                raise
    