# python 
import uuid
import numpy as np

# django 
from django.db import models, IntegrityError
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError

# models
from users.models import Student
from schools.models import School
from grades.models import Grade
from terms.models import Term
from subjects.models import Subject


class StudentSubjectPerformance(models.Model):
    """
    Tracks the performance of an individual student in a specific subject for a given academic term.

    Performance metrics include:
    - Raw and normalized scores
    - Weighted scores
    - Statistical data (average, highest, lowest, median, mode scores)
    - Completion and pass rates
    """

    # The student whose performance is being recorded.
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='subject_performances')

    # The raw score achieved by the student
    score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)

    # The student's score normalized against the total possible score for all assessments in the subject.
    normalized_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    
    # The weighted score reflects the importance of this subject in the term's final mark.
    weighted_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)

    # The student's pass rate based on the assessments' pass marks.
    pass_rate = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)

    # Statistical fields for tracking the student's performance relative to other students in the subject.
    highest_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    lowest_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    average_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    median_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)

    # Percentage of assessments completed by the student.
    completion_rate = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)

    # The most common score among all students in the subject.
    mode_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)

    # Boolean indicating if the student passed the subject based on their normalized score.
    passed = models.BooleanField(default=False)

    # ForeignKey to the academic term, linking the performance to a specific term.
    term = models.ForeignKey(Term, editable=False, on_delete=models.CASCADE, related_name='student_subject_performances')

    # ForeignKey to the subject being assessed.
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, editable=False, related_name='student_performances')

    # ForeignKey to the student's grade level.
    grade = models.ForeignKey(Grade, on_delete=models.CASCADE, editable=False, related_name='student_subject_performances')

    # ForeignKey to the school where the student is enrolled.
    school = models.ForeignKey(School, on_delete=models.CASCADE, editable=False, related_name='student_subject_performances')

    # Timestamp of the last update to this record.
    last_updated = models.DateTimeField(auto_now=True)

    # Unique identifier for the student's subject performance.
    student_score_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)

    class Meta:
        """
        Meta class options:
        - Enforces a unique constraint, ensuring that no duplicate performance records exist for the same student, subject, term, and school.
        """
        constraints = [
            models.UniqueConstraint(fields=['student', 'subject', 'term', 'school'], name='unique_student_subject_term_performance')
        ]

    def __str__(self):
        """
        String representation of the model instance for easy identification in Django admin or logs.
        """
        return f"{self.subject} - {self.student} - Term {self.term}"

    def clean(self):
        """
        Custom validation to ensure valid score ranges:
        - Ensures raw and weighted scores are between 0 and 100.
        """
        if self.score and not (0 <= self.score <= 100):
            raise ValidationError(_('Student subject score for any given term must be between 0 and 100'))
        
        if self.weighted_score and not (0 <= self.weighted_score <= 100):
            raise ValidationError(_('A student\'s subject weighted score for any given term must be between 0 and 100'))

    def save(self, *args, **kwargs):
        """
        Overrides the save method to validate data before saving.
        - Handles unique constraint violations for duplicate subject scores.
        """
        self.clean()

        try:
            super().save(*args, **kwargs)
        except IntegrityError as e:
            if 'unique_student_subject_term_performance' in str(e):
                raise IntegrityError(_('A student cannot have duplicate subject scores for the same subject in the same term. Consider regenerating new subject scores for the term, which will discard the current ones.'))
            else:
                raise

    def update_performance_metrics(self):
        """
        Updates the student's performance metrics by calculating:
        - Scores, pass rates, and completion rates.
        - Statistical data like highest, lowest, median, and mode scores.
        - Determines whether the student passed the subject.
        """

        # Fetch all formal assessments for the subject in this term.
        grade_assessments = self.subject.assessments.filter(term=self.term, formal=True, grades_released=True)

        # If no assessments exist, set relevant scores to None.
        if not grade_assessments.exists():
            self.score = self.normalized_score = self.weighted_score = self.average_score = None
            print('no assessments')
            return

        grade_assessments_count = grade_assessments.count()
        pass_mark = self.subject.pass_mark

        # Fetch the student's transcripts and submissions for the subject's assessments.
        students_transcripts = self.student.transcripts.filter(assessment__in=grade_assessments)
        students_transcripts_data = students_transcripts.aggregate(
            score=models.Sum('weighted_score'),
            maximum_score_achievable=models.Sum('assessment__percentage_towards_term_mark'),
            passed_assessments_count=models.Count('id', filter=models.Q(weighted_score__gte=pass_mark)),
            average=models.Avg('weighted_score'),
            highest=models.Max('weighted_score'),
            lowest=models.Min('weighted_score')
        )

        # Calculate the student's total score across all assessments.
        self.score = students_transcripts_data['score']

        # Update normalized and weighted scores if valid scores exist.
        if self.score > 0 and students_transcripts_data['maximum_score_achievable'] > 0:
            self.normalized_score = (self.score / students_transcripts_data['maximum_score_achievable']) * 100
            self.weighted_score = self.normalized_score * (self.term.weight / 100)
        else:
            self.normalized_score = 0
            self.weighted_score = 0

        # Determine if the student passed based on the normalized score and pass mark.
        if self.normalized_score:
            self.passed = self.normalized_score >= pass_mark

        # Calculate the pass rate: number of assessments passed by the student.
        self.pass_rate = (students_transcripts_data['passed_assessments_count'] / grade_assessments_count) * 100

        # Calculate the average score across all assessments.
        self.average_score = students_transcripts_data['average']
        self.highest_score = students_transcripts_data['highest']
        self.lowest_score = students_transcripts_data['lowest']

        # Retrieve all scores for further statistical analysis.
        scores = np.array(students_transcripts.values_list('weighted_score', flat=True))
        if scores.size > 0:
            # Calculate highest, lowest, median, and mode scores.
            self.median_score = np.median(scores)

            # Calculate the mode score (most frequent score).
            unique_scores, counts = np.unique(scores, return_counts=True)
            self.mode_score = unique_scores[np.argmax(counts)]

        # Calculate the completion rate: percentage of assessments the student has submitted.
        submitted_assessments_count = self.student.submissions.filter(assessment__in=grade_assessments).exclude(status='NOT_SUBMITTED').count()
        self.completion_rate = (submitted_assessments_count / grade_assessments_count) * 100

        # Save the updated performance metrics.
        self.save()

