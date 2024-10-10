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
from grades.models import Grade


class Term(models.Model):
    """
    The `Term` model represents a school term within a particular grade and school. 

    It holds details such as the term identifier, the weight of the term in relation to 
    other terms, start and end dates, the number of school days within the term, and the grade 
    and school it is associated with.
    """

    # The term identifier (e.g., "Term 1", "Term 2", etc.)
    term = models.CharField(max_length=16)
    
    # Weight of the term in relation to the final year calculations (e.g., 30.00%)
    weight = models.DecimalField(max_digits=5, decimal_places=2)

    # Start and end dates of the term
    start_date = models.DateField()
    end_date = models.DateField()

    # The number of school days in the term (auto-calculated if not provided)
    school_days = models.PositiveIntegerField(default=0)

    # Foreign keys linking the term to a specific grade and school
    grade = models.ForeignKey(Grade, on_delete=models.CASCADE, editable=False, related_name='terms')
    school = models.ForeignKey(School, on_delete=models.CASCADE, editable=False, related_name='terms')

    # Timestamp for the last time the term was updated
    last_updated = models.DateTimeField(auto_now=True)

    # Unique identifier for each term instance
    term_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)

    class Meta:
        # Ensure that a combination of term, grade, and school is unique
        constraints = [
            models.UniqueConstraint(fields=['term', 'grade', 'school'], name='unique_grade_term')
        ]
        # Order terms by start date, most recent first
        ordering = ['-start_date']
        # Add an index for queries involving grade and school for performance optimization
        indexes = [models.Index(fields=['grade', 'school'])]

    def __str__(self):
        """String representation of the Term object."""
        return f"Term {self.term}"

    def save(self, *args, **kwargs):
        """
        Custom save method to perform additional validations and calculate school days 
        if they are not provided. Also ensures that the term identifier is valid.
        """
        # Validate the model using the custom clean method
        self.clean()
        try:
            # Call the actual save method of the parent class
            super().save(*args, **kwargs)
        except IntegrityError as e:
            # Handle potential unique constraint violation for duplicate terms
            if 'unique_grade_term' in str(e).lower():
                raise ValidationError(_(f'A term with the identifier {self.term} already exists for the specified grade and school. Duplicate terms within the same grade and school are not allowed. Please choose a different term identifier or check existing terms.'))
            else:
                # Re-raise other database exceptions
                raise ValidationError(_(str(e)))
        except Exception as e:
            # Catch any other errors during saving and re-raise them as validation errors
            raise ValidationError(_(str(e).lower()))

    def clean(self):
        """
        Custom validation logic for the Term model.
        
        Ensures the following:
        - The term's start date is before its end date.
        - The term dates do not overlap with other terms in the same grade and school.
        - The total weight of all terms in the grade does not exceed 100% for a given school year.
        """
        if not self.term:
            raise ValidationError(_('The provided term information is missing a term identifier. Please specify a valid term (e.g., "Term 1").'))
        elif len(self.term) > 16:
            raise ValidationError(_('The specified term identifier is too long. A term identifier can have a maximum length of 16 characters. Consider shortening the identifier.'))
        
        # Ensure the start date is before the end date
        if self.start_date >= self.end_date:
            raise ValidationError(_('The term start date must be before the end date. Please provide a valid start and end date range.'))

        # Check for overlapping terms within the same grade and school
        overlapping_terms = Term.objects.filter(school=self.school, grade=self.grade, start_date__lt=self.end_date, end_date__gt=self.start_date).exclude(pk=self.pk)  # Exclude the current term if it's being updated

        if overlapping_terms.exists():
            raise ValidationError(_('The provided start and end dates for this term overlap with one or more existing terms in the same grade and school. Please adjust the term dates to avoid conflicts.'))

        # Ensure the total weight of terms in the grade does not exceed 100%
        total_weight = Term.objects.filter(school=self.school, grade=self.grade).exclude(pk=self.pk).aggregate(total_weight=models.Sum('weight'))['total_weight'] or Decimal('0.00')

        if total_weight + self.weight > Decimal('100.00'):
            raise ValidationError(_('The total weight of all terms in the grade for the specified school exceeds 100%. The maximum allowed weight for all terms combined is 100%. Please adjust the term weight.'))

        if total_weight + self.weight < Decimal('0.00'):
            raise ValidationError(_('The total weight of all terms in the grade must be at least 0%. Please adjust the term weight accordingly.'))

        # Calculate the total number of school days if not provided
        if not self.school_days:
            self.school_days = self.calculate_total_school_days()

    def calculate_total_school_days(self):
        """
        Calculate the total number of school days in the term (Monday to Friday only).
        
        - Iterates through the date range (from start_date to end_date) and counts weekdays.
        - Returns the total number of school days.
        """
        total_days = 0
        current_date = self.start_date

        # Iterate through the dates from start_date to end_date
        while current_date <= self.end_date:
            if current_date.weekday() < 5:  # Monday to Friday are considered school days
                total_days += 1
            current_date += timedelta(days=1)

        return total_days
