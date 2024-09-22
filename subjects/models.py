# python 
import uuid

# django 
from django.db import models, IntegrityError
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

# models
from grades.models import Grade


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
    """
    Represents a school subject (e.g., Mathematics, English) and its related properties.

    Each subject is tied to a specific grade, and the subject model includes various fields
    for tracking both static information (subject name, whether it's a major subject, etc.)
    and dynamic information such as student and teacher counts.

    Key features:
    - Subjects are uniquely tied to a grade, preventing duplicate subjects within the same grade.
    - Provides fields for tracking the subject pass mark, counts of students/teachers, and related data.
    """

    # The name of the subject, limited to 64 characters and chosen from a predefined set of subjects.
    # The choices come from a constant `SCHOOL_SUBJECTS_CHOICES` (e.g., [("ENGLISH", "English"), ("MATH", "Mathematics")]).
    subject = models.CharField(_('Subject'), max_length=64, choices=SCHOOL_SUBJECTS_CHOICES, default="ENGLISH")

    # A boolean flag to indicate if this is a "major" subject (e.g., core subjects like Math or Science).
    major_subject = models.BooleanField(default=False)

    # The passing mark for this subject, defaulting to 40.00, with a maximum precision of 5 digits and 2 decimal places.
    # For example, a passing mark could be 40.00%, but this can be adjusted per subject.
    pass_mark = models.DecimalField(max_digits=5, decimal_places=2, default=40.00)

    # The number of students enrolled in this subject. This value should be updated as students are enrolled or leave the subject.
    student_count = models.IntegerField(default=0)

    # The number of teachers assigned to teach this subject. Useful for balancing workload and teacher assignment.
    teacher_count = models.IntegerField(default=0)

    # The number of classrooms associated with this subject. For instance, if a subject is taught across multiple rooms.
    classroom_count = models.IntegerField(default=0)

    # to be implemented at a later if reason be
    # Pass rate
    # pass_rate = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    # # Failure rate (calculated as 100 - pass_rate, but explicitly stored)
    # failure_rate = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)

    # highest_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    # lowest_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    # average_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    # median_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)

    # # Measures the standard deviation of students' scores, providing insight into score variability
    # standard_deviation = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    # # A JSONField storing percentile data, where each key (e.g., "10th", "90th") maps to a list of students who fall within that percentile range
    # # percentile_distribution = models.JSONField(null=True, blank=True)

    # students_failing_the_subject = models.ManyToManyField(Student, related_name='failing_subjects', help_text='Students who are failing the subject.')

    # # Tracks the percentage of students who have improved their scores compared to a previous assessment or term
    # improvement_rate = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    # # Percentage of students who completed all assessments
    # completion_rate = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)

    # Links the subject to a specific grade level, establishing a one-to-many relationship where
    # each grade can have multiple subjects but a subject is associated with only one grade.
    grade = models.ForeignKey(Grade, on_delete=models.CASCADE, editable=False, related_name='subjects')

    # A UUID field to uniquely identify the subject. Using UUID ensures uniqueness even across distributed systems.
    subject_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)

    # Tracks the last time this subject's record was updated in the database.
    # Automatically updates whenever the record is saved, without needing manual intervention.
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        """
        Meta options define constraints, ordering, and indexing for the Subject model.
        """
        # A unique constraint that prevents the same subject from being entered multiple times for the same grade.
        constraints = [
            models.UniqueConstraint(fields=['grade', 'subject'], name='unique_grade_subject')
        ]

        # Default ordering for querying subjects, sorting by subject name alphabetically.
        ordering = ['subject']

        # Adds an index to the combination of subject and grade fields to speed up queries.
        indexes = [models.Index(fields=['subject', 'grade'])]

    def __str__(self):
        """
        The string representation of the Subject model, which returns the subject name.
        This makes it more readable in admin panels and for debugging purposes.
        """
        return self.subject

    def save(self, *args, **kwargs):
        """
        Overrides the default save method to add custom validation and error handling.

        - Ensures that the subject is associated with a grade before saving.
        - Attempts to catch and handle `IntegrityError` related to unique constraint violations, providing
          more user-friendly error messages if a duplicate subject is detected.
        """
        if not self.pk:  # Only perform this check on object creation
            if not self.grade:
                raise ValidationError(_('A subject needs to be associated with a school grade'))

        self.clean()  # Ensure the model's fields are valid before saving.

        try:
            super().save(*args, **kwargs)  # Call the original save method
        except IntegrityError as e:
            error_message = str(e).lower()
            # Handle unique constraint errors gracefully and provide useful feedback.
            if 'unique constraint' in error_message:
                if 'grade_subject' in error_message:
                    raise ValidationError(_('The provided subject already exists for this grade. Duplicate subjects are not permitted.'))
                else:
                    raise ValidationError(_('A unique constraint error occurred.'))
            # If it's not handled, re-raise the original exception
            raise

    def clean(self):
        """
        Custom validation method for ensuring that the pass mark is within a valid range (0 to 100).
        This method is called before the subject is saved to ensure data integrity.
        """
        # Ensure the pass mark is between 0 and 100
        if not (0 <= self.pass_mark <= 100):
            raise ValidationError(_('The subject\'s pass mark must be between 0 and 100'))
        

    # def update_performance_metrics(self):
    #     # Pass rate, completion rate, improvement rate (weighted averages)
    #     students_in_the_subject = self.grade.students.filter(enrolled_classrooms__subject=self.subject)
    #     if not students_in_the_subject.exists():
    #         self.pass_rate = self.completion_rate = self.improvement_rate = self.average_score = None
    #         return

    #     # Get the total number of students enrolled in the subject across all terms
    #     students_in_the_subject_count = students_in_the_subject.count()

    #     # Get all termly performances
    #     subject_termly_performances = self.termly_performances
    #     # Get the number of terms for averaging
    #     number_of_terms = subject_termly_performances.count()

    #     # Pass rate (average across terms)
    #     self.pass_rate = subject_termly_performances.aggregate(weighted_pass_rate=Sum('pass_rate'))['weighted_pass_rate'] / number_of_terms
    #     self.failure_rate = 100 - self.pass_rate

    #     # Completion rate (average across terms)
    #     self.completion_rate = subject_termly_performances.aggregate(completion_rate=Sum('completion_rate'))['completion_rate'] / number_of_terms

    #     # Improvement rate (average across terms)
    #     self.improvement_rate = subject_termly_performances.aggregate(improvement_rate=Sum('improvement_rate'))['improvement_rate'] / number_of_terms

    #     # Average score (average across terms)
    #     self.average_score = subject_termly_performances.aggregate(avg_score=Sum('average_score'))['avg_score'] / number_of_terms

    #     self.highest_score = subject_termly_performances.aggregate(Max('highest_score'))['highest_score__max']
    #     self.lowest_score = subject_termly_performances.aggregate(Min('lowest_score'))['lowest_score__min']

    #     # Query to get all student performances related to this subject
    #     subject_performances = self.student_performances

    #     # Fetch all scores across the terms
    #     all_scores = np.array(subject_performances.values_list('normalized_score', flat=True))

    #     if all_scores:
    #         # Median and standard deviation calculations
    #         self.median_score = np.median(all_scores)
    #         self.standard_deviation = np.std(all_scores)

    #     # Aggregate the total weighted score and the total possible weighted score
    #     student_scores = subject_performances.values('student').annotate(
    #         total_weighted_score=Sum('weighted_score'),  # Total weighted score achieved by the student
    #         total_max_weighted_score=Sum(F('term__weight'))  # Sum of weights for all terms
    #     ).annotate(
    #         normalized_score=ExpressionWrapper(
    #             F('total_weighted_score') / F('total_max_weighted_score') * 100,  # Normalize to percentage
    #             output_field=DecimalField()
    #         )
    #     )

    #     # Step 5: Determine failing students based on the normalized score compared to the pass mark
    #     failing_students_ids = [student_score['student'] for student_score in student_scores if student_score['normalized_score'] < self.pass_mark]

    #     # Update the students_failing_the_subject field
    #     self.students_failing_the_subject.set(failing_students_ids)

    #     self.save()


    # def update_performance_metrics(self):
    #     # Query to get all student performances related to this subject
    #     performances = self.student_performances

    #     scores = [p.normalized_score for p in performances if p.normalized_score is not None]
    #     if not scores:
    #         return  # No data to process

    #     students_in_the_subject_count = performances.count()

    #     # Rank-based Percentile Calculation
    #     percentiles = {'10th': [], '25th': [], '50th': [], '75th': [], '90th': []}
        
    #     # Determine rank boundaries for each percentile
    #     rank_boundaries = {
    #         '10th': int(0.10 * students_in_the_subject_count),
    #         '25th': int(0.25 * students_in_the_subject_count),
    #         '50th': int(0.50 * students_in_the_subject_count),
    #         '75th': int(0.75 * students_in_the_subject_count),
    #         '90th': students_in_the_subject_count
    #     }

    #     for i, (normalized_score, student_id) in enumerate(scores):
    #         if i < rank_boundaries['10th']:
    #             percentiles['10th'].append(student_id)
    #         elif i < rank_boundaries['25th']:
    #             percentiles['25th'].append(student_id)
    #         elif i < rank_boundaries['50th']:
    #             percentiles['50th'].append(student_id)
    #         elif i < rank_boundaries['75th']:
    #             percentiles['75th'].append(student_id)
    #         else:
    #             percentiles['90th'].append(student_id)

    #     self.percentile_distribution = {k: {'count': len(v), 'students': v} for k, v in percentiles.items()}

