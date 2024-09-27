# python 
import uuid
import numpy as np
from decimal import Decimal, ROUND_HALF_UP

# django 
from django.db import models, IntegrityError
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError

# models
from users.models import Student
from schools.models import School
from terms.models import Term
from subjects.models import Subject

# utility functions
from terms import utils as term_utilities


class TermSubjectPerformance(models.Model):
    """
    Tracks the performance of a particular subject during a specific academic term.
    
    This model records various performance metrics such as:
    - Pass and failure rates
    - Statistical analysis of scores (e.g., highest, lowest, average, median)
    - Percentile distributions
    - Completion rates and improvement rates
    
    Additionally, it records student achievements and failures for a given term.
    """

    # Reference to the academic term for which the performance data applies.
    # Related to the 'Term' model via a ForeignKey.
    term = models.ForeignKey(Term, editable=False, on_delete=models.CASCADE, related_name='subject_performances')

    # Percentage of students who passed the subject during this term.
    pass_rate = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)

    # Percentage of students who failed the subject, calculated as 100 - pass_rate.
    failure_rate = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)

    # Highest score achieved in the subject during the term.
    highest_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)

    # Lowest score achieved in the subject during the term.
    lowest_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)

    # The average score of students in this subject during the term.
    average_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)

    # The median score of students in this subject during the term.
    median_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)

    # The standard deviation of student scores, reflecting the variability in performance.
    standard_deviation = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)

    # JSONField to store the percentile distribution of student scores, mapping percentile ranges to lists of student IDs.
    percentile_distribution = models.JSONField(null=True, blank=True)

    # The percentage of students who improved their scores compared to previous terms.
    improvement_rate = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)

    # The percentage of students who completed all required assessments for this subject in the term.
    completion_rate = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)

    # Many-to-many relationship with students who are top performers in this subject for the term.
    top_performers = models.ManyToManyField(Student, related_name='subject_term_top_performers', blank=True)

    # Many-to-many relationship with students who failed the subject in this term.
    students_failing_the_subject_in_the_term = models.ManyToManyField(Student, related_name='subject_term_in_danger', help_text='Students who failed the term.')

    # Reference to the specific subject for which the performance data is tracked.
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, editable=False, related_name='termly_performances')

    # Reference to the school where this term's performance is assessed.
    school = models.ForeignKey(School, on_delete=models.CASCADE, editable=False, related_name='termly_subject_performances')

    # Automatically updated timestamp for the last time this performance data was modified.
    last_updated = models.DateTimeField(auto_now=True)

    # A UUID field to uniquely identify each term subject performance record.
    term_score_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)

    class Meta:
        """
        Meta class options:
        - Enforces unique combination of subject, term, and school to avoid duplicate performance records for the same subject in the same term.
        """
        constraints = [
            models.UniqueConstraint(fields=['subject', 'term', 'school'], name='unique_subject_term_performance')
        ]

    def __str__(self):
        """
        Returns a string representation of the model instance.
        Useful for displaying in the Django admin panel or when debugging.
        """
        return f"{self.subject} - Term {self.term}"

    def clean(self):
        """
        Custom validation method:
        - Ensures that rates (pass, failure, improvement, completion) are valid percentages between 0 and 100.
        - Can be expanded to include additional validation if necessary.
        """
        if self.pass_rate and not (0 <= self.pass_rate <= 100):
            raise ValidationError(_('Pass rate must be between 0 and 100'))
        if self.failure_rate and not (0 <= self.failure_rate <= 100):
            raise ValidationError(_('Failure rate must be between 0 and 100'))
        if self.improvement_rate and not (0 <= self.improvement_rate <= 100):
            raise ValidationError(_('Improvement rate must be between 0 and 100'))
        if self.completion_rate and not (0 <= self.completion_rate <= 100):
            raise ValidationError(_('Completion rate must be between 0 and 100'))

    def save(self, *args, **kwargs):
        """
        Overrides the default save method to:
        - Validate the model data before saving.
        - Handle potential unique constraint violations, ensuring that no duplicate performance records are created.
        """
        self.clean()  # Ensure fields are valid before saving.
        try:
            super().save(*args, **kwargs)  # Call the original save method.
        except IntegrityError as e:
            # If a unique constraint error occurs, raise an appropriate exception.
            if 'unique constraint' in str(e).lower():
                raise ValidationError(_('A student cannot have duplicate subject scores for the same subject in the same term. Consider regenerating new subject scores for the term, which will discard the current ones.'))
            else:
                raise

    def update_performance_metrics(self):
        """
        Calculates and updates key performance metrics for the subject in this term:
        - Pass rate, failure rate, and score statistics (average, highest, lowest, median, standard deviation).
        - Percentile distribution of student scores.
        - Improvement rate and completion rate.

        Also updates top performers and students failing the subject for the term.
        """
        # Retrieve all performances for the subject in the current term.
        performances = self.subject.student_performances.filter(term=self.term)
        # print(f'performances: {performances}')
        if not performances.exists():
            self.pass_rate = self.average_score = self.median_score = None
            return
        
        performance_data = performances.aggregate(
            highest_score=models.Max('normalized_score'),
            lowest_score=models.Min('normalized_score'),
            average_score=models.Avg('normalized_score'),
            stddev=models.StdDev('normalized_score'),
            students_passing_the_term=models.Count('id', filter=models.Q(normalized_score__gte=self.subject.pass_mark)),
            students_in_the_subject_count=models.Count('student')
        )
        # print(f'performance_data: {performance_data}')

        self.highest_score = performance_data['highest_score']
        self.lowest_score = performance_data['lowest_score']
        self.average_score = performance_data['average_score']
        self.standard_deviation = performance_data['stddev']
        
        # Calculate pass rate
        self.pass_rate = (performance_data['students_passing_the_term'] / performance_data['students_in_the_subject_count']) * 100
        # print(f'pass_rate: {self.pass_rate}')
        self.failure_rate = 100 - self.pass_rate

        # Retrieve and sort scores for statistical calculations.
        student_scores = performances.order_by('normalized_score').values_list('normalized_score', 'student_id')
        scores = np.array([score[0] for score in student_scores])
        # print(f'scores: {scores}')

        if scores.size > 0:
            # Calculate median score
            self.median_score = np.median(scores)

            # Calculate percentile boundaries
            percentiles = np.percentile(scores, [Decimal(10), Decimal(25), Decimal(50), Decimal(75), Decimal(90)])

            # Create empty lists for student IDs based on percentile ranges
            students_in_10th_percentile = []
            students_in_25th_percentile = []
            students_in_50th_percentile = []
            students_in_75th_percentile = []
            students_in_90th_percentile = []

            # Assign students to percentiles based on their weighted score
            for weighted_score, student_id in student_scores:
                if weighted_score <= percentiles[0]:
                    students_in_10th_percentile.append(student_id)
                elif weighted_score <= percentiles[1]:
                    students_in_25th_percentile.append(student_id)
                elif weighted_score <= percentiles[2]:
                    students_in_50th_percentile.append(student_id)
                elif weighted_score <= percentiles[3]:
                    students_in_75th_percentile.append(student_id)
                else:
                    students_in_90th_percentile.append(student_id)

            # Store the percentile distribution
            self.percentile_distribution = {
                '10th': {'count': len(students_in_10th_percentile), 'students': students_in_10th_percentile},
                '25th': {'count': len(students_in_25th_percentile), 'students': students_in_25th_percentile},
                '50th': {'count': len(students_in_50th_percentile), 'students': students_in_50th_percentile},
                '75th': {'count': len(students_in_75th_percentile), 'students': students_in_75th_percentile},
                '90th': {'count': len(students_in_90th_percentile), 'students': students_in_90th_percentile},
            }
            # print(f'percentile_distribution: {self.percentile_distribution}')

        students_in_the_subject = Student.objects.filter(id__in=performances.values_list('student_id', flat=True)).distinct()

        # Calculate improvement rate.
        previous_term = term_utilities.get_previous_term(self.school, self.term.grade)
        if previous_term:
            previous_scores = self.subject.student_performances.filter(student__in=students_in_the_subject, term=previous_term).values('student_id', 'normalized_score')
            if previous_scores.exists():
                previous_subject_scores_dict = {score['student_id']: score['normalized_score'] for score in previous_scores}

                improved_students = sum(
                    1 for performance in performances
                    if previous_subject_scores_dict.get(performance.student_id) is not None and performance.normalized_score > previous_subject_scores_dict[performance.student_id]
                )
                self.improvement_rate = (improved_students / performance_data['students_in_the_subject_count']) * 100
            else:
                self.improvement_rate = None
        else:
            self.improvement_rate = None
            
        student_submissions = students_in_the_subject.annotate(
            submission_count=models.Count(
                'submissions',
                filter=models.Q(~models.Q(submissions__status='NOT_SUBMITTED'), submissions__assessment__subject=self.subject, submissions__assessment__term=self.term, submissions__assessment__formal=True),
            )
        )
        # print(f'student_submissions: {student_submissions}')

        required_assessments = self.subject.assessments.filter(formal=True, term=self.term).count()
        # print(f'required_assessments: {required_assessments}')

        completed_students = student_submissions.filter(submission_count__gte=required_assessments).count()
        self.completion_rate = (completed_students / performance_data['students_in_the_subject_count']) * 100
        # print(f'completion_rate: {self.completion_rate}')

        # Identify top performers.
        top_performers_count = 3
        top_performers = performances.filter(normalized_score__gte=self.subject.pass_mark).values_list('student_id', flat=True).order_by('-normalized_score')[:top_performers_count]
        if top_performers.exists():
            self.top_performers.set(top_performers)
        # print(f'top_performers: {top_performers}')

        # Update the students_failing_the_subject_in_the_term field.
        students_failing_the_term = performances.filter(normalized_score__lt=self.subject.pass_mark).values_list('student_id', flat=True)
        if students_failing_the_term.exists():
            self.students_failing_the_subject_in_the_term.set(students_failing_the_term)
        # print(f'students_failing_the_term: {students_failing_the_term}')

        # Save the updated performance metrics.
        self.save()
        
        # print(f'term performance metrics calculated successfully')


