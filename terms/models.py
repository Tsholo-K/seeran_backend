# python 
import uuid
from datetime import timedelta
from decimal import Decimal
# import logging

# django 
from django.db import models, IntegrityError
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError

# models
from schools.models import School
from grades.models import Grade

# logger = logging.getLogger(__name__)


class Term(models.Model):

    # the term identifier
    term = models.CharField(max_length=16, editable=False)
    # Weight of the term in final year calculations in relation to other terms
    weight = models.DecimalField(max_digits=5, decimal_places=2)

    # The first day of the term
    start_date = models.DateField()
    # The final day of the term
    end_date = models.DateField()

    # number of school days in the term
    school_days = models.IntegerField(default=0)

    # grade linked to
    grade = models.ForeignKey(Grade, on_delete=models.CASCADE, editable=False, related_name='terms')

    # The school the term is linked to
    school = models.ForeignKey(School, on_delete=models.CASCADE, editable=False, related_name='terms')

    # term id 
    term_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)

    class Meta:
        ordering = ['term']
        unique_together = ('term', 'grade', 'school')
        indexes = [models.Index(fields=['term', 'school'])]

    def __str__(self):
        return f"Term {self.term}"
    
    def clean(self):
        """
        Ensure that the term dates do not overlap with other terms in the same school and validate term dates.
        """
        if self.start_date >= self.end_date:
            raise ValidationError(_('a terms start date must be before it\'s end date'))

        overlapping_terms = Term.objects.filter(school=self.school, grade=self.grade, start_date__lt=self.end_date, end_date__gt=self.start_date).exclude(pk=self.pk)
        if overlapping_terms.exists():
            raise ValidationError(_('the provided start and end dates for the term overlap with one or more existing terms'))
        
        total_weight = Term.objects.filter(school=self.school, grade=self.grade).exclude(pk=self.pk).aggregate(total_weight=models.Sum('weight'))['total_weight'] or '0.00'

        # Ensure the total weight does not exceed 100%
        if Decimal(total_weight) + Decimal(self.weight) > Decimal('100.00') or Decimal(total_weight) + Decimal(self.weight) < Decimal('0.00'):
            raise ValidationError(_('The total weight of all terms in the grade should be between 0% and 100% for any given school calendar year.'))
        
        if not self.school_days:
            self.school_days = self.calculate_total_school_days()
        
    def save(self, *args, **kwargs):
        """
        Override save method to calculate the total amount of school days in the term if not provided.
        """
        if not self.pk:
            if not self.term:
                raise ValidationError(_('the provided term information is missing a term identifier'))
            
            elif len(self.term) > 16:
                raise ValidationError(_('the specified term identifier is too long, max length of a term identifier is 16 characters'))

        self.clean()

        try:
            super().save(*args, **kwargs)
        except IntegrityError as e:
            # Check if the error is related to unique constraints
            if 'unique constraint' in str(e).lower():
                raise ValidationError(_('a term with the provided term identifier in the specified grade is already there for your school. duplicate terms within the same grade and school is not permitted.'))
            else:
                # Re-raise the original exception if it's not related to unique constraints
                raise

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
