# python 
import uuid
import statistics

# import logging

# django 
from django.db import models, IntegrityError
from django.db.models import Count, F, Sum, FloatField, ExpressionWrapper
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError

# logging
# logger = logging.getLogger(__name__)

# models
from users.models import Student
from grades.models import Grade

# utility functions
from terms import utils as term_utilities


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

class Subject(models.Model):
    subject = models.CharField(_('Subject'), max_length=64, choices=SCHOOL_SUBJECTS_CHOICES, default="ENGLISH")

    # field to indicate if it's a major subject
    major_subject = models.BooleanField(default=False)
    # subject-specific pass mark
    pass_mark = models.DecimalField(max_digits=5, decimal_places=2, default=40.00)

    student_count = models.IntegerField(default=0)
    teacher_count = models.IntegerField(default=0)
    classroom_count = models.IntegerField(default=0)

    pass_rate = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)

    average_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    median_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)

    students_failing_the_subject = models.ManyToManyField(Student, related_name='failing_subjects', help_text='Students who are failing the subject.')

    # grade linked to
    grade = models.ForeignKey(Grade, on_delete=models.CASCADE, editable=False, related_name='subjects')

    last_updated = models.DateTimeField(auto_now=True)

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
        if not self.pk:
            if not self.grade:
                raise ValidationError(_('a subject needs to be associated with a school grade'))
            
        self.clean()
            
        try:
            super().save(*args, **kwargs)
        except IntegrityError as e:
            error_message = str(e).lower()
            # logger.error('Integrity error occurred while saving Subject: %s', str(e))

            # Handle unique constraint errors
            if 'unique constraint' in error_message:
                
                if 'grade_subject' in error_message:
                    raise ValidationError(_('The provided subject already exists for this grade. Duplicate subjects are not permitted.'))
                
                else:
                    raise ValidationError(_('A unique constraint error occurred.'))

            # Re-raise the original exception if it's not handled
            raise

    def update_performance_metrics(self):
        # Query TermSubjectPerformance for the current subject
        term_performances = self.termly_performances

        total_scores = []
        all_pass_rates = []
        all_medians = []

        for performance in term_performances:
            if performance.average_score is not None:
                total_scores.append(performance.average_score)
            if performance.pass_rate is not None:
                all_pass_rates.append(performance.pass_rate)
            if performance.median_score is not None:
                all_medians.append(performance.median_score)

        # Aggregate pass rate
        self.pass_rate = sum(all_pass_rates) / len(all_pass_rates) if all_pass_rates else None

        # Aggregate average score
        self.average_score = sum(total_scores) / len(total_scores) if total_scores else None

        # Aggregate median score
        self.median_score = statistics.median(all_medians) if all_medians else None

        self.save()

    def update_students_failing_the_subject(self):
        # Step 1: Retrieve all student performances for the subject across all terms
        performances = self.student_performances

        # Step 2: Aggregate the total weighted score and the total possible weighted score
        student_scores = performances.values('student').annotate(
            total_weighted_score=Sum('weighted_score'),  # Total weighted score achieved by the student
            total_max_weighted_score=Sum(F('term__weight'))  # Sum of weights for all terms (if term weight is stored)
        ).annotate(
            normalized_score=ExpressionWrapper(
                F('total_weighted_score') / F('total_max_weighted_score') * 100,  # Normalize to percentage
                output_field=FloatField()
            )
        )

        # Step 5: Determine failing students based on the normalized score compared to the pass mark
        failing_students_ids = [student_score['student'] for student_score in student_scores if student_score['normalized_score'] < self.pass_mark]

        # Fetch Student instances from the list of IDs
        failing_students_instances = Student.objects.filter(id__in=failing_students_ids)

        # Update the students_failing_the_subject field
        self.students_failing_the_subject.set(failing_students_instances)
        self.save()
