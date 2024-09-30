# python 
import uuid
import numpy as np
from decimal import Decimal

# django
from django.core.exceptions import ValidationError
from django.db import models, IntegrityError
from django.utils.translation import gettext_lazy as _

# models
from accounts.models import Student
from schools.models import School
from classrooms.models import Classroom
from terms.models import Term

# utility functions
from terms import utils as term_utilities

# tasks
from term_subject_performances import tasks as  term_subject_performances_tasks


# Create your models here.
class ClassroomPerformance(models.Model):
    """
    Model representing a classroom in a school. This classroom could either be 
    a register class (the main homeroom class for students) or a subject-specific class.
    
    Attributes:
        student_count: Count of students in the classroom.
        pass_rate: Percentage of students who passed the subject in this classroom.
        failure_rate: Percentage of students who failed (100 - pass_rate).
        highest_score: The highest score achieved by a student in the classroom.
        lowest_score: The lowest score achieved by a student in the classroom.
        average_score: The average score of students in the classroom.
        median_score: The median score of students in the classroom.
        top_performers: List of top-performing students in the classroom.
        students_failing_the_classroom: List of students failing the classroom.
        std_dev_score: Standard deviation of students' scores, indicating score variability.
        percentile_distribution: JSON field storing percentile data of students' performance.
        improvement_rate: Percentage of students who improved their scores compared to previous term.
        completion_rate: Percentage of students who completed all formal assessments.
        school: The school to which the classroom belongs.
        last_updated: Timestamp indicating the last update to this classroom's information.
        classroom_performance_id: A unique UUID for identifying the classroom performane.
    """

    # Reference to the classroom for which the performance data applies.
    # Related to the Classroom model via a ForeignKey.
    classroom = models.ForeignKey(Classroom, editable=False, on_delete=models.CASCADE, related_name='classroom_performances')

    # Reference to the academic term for which the performance data applies.
    # Related to the 'Term' model via a ForeignKey.
    term = models.ForeignKey(Term, editable=False, on_delete=models.CASCADE, related_name='classroom_term_performances')

    # Pass rate
    pass_rate = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    # Failure rate (calculated as 100 - pass_rate, but explicitly stored)
    failure_rate = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)

    highest_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    lowest_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    average_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    median_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)

    # Students who are among the top performers based on their scores
    top_performers = models.ManyToManyField(Student, related_name='top_performers_classes', blank=True)
    # Students who are failing the classroom based on their scores
    students_failing_the_classroom = models.ManyToManyField(Student, related_name='failing_classes', help_text='Students who are failing the classroom.')

    # Measures the standard deviation of students' scores, providing insight into score variability
    std_dev_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    # A JSONField storing percentile data, where each key (e.g., "10th", "90th") maps to a list of students who fall within that percentile range
    percentile_distribution = models.JSONField(null=True, blank=True)

    # Tracks the percentage of students who have improved their scores compared to a previous assessment or term
    improvement_rate = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    # Percentage of students who completed all assessments
    completion_rate = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)

    school = models.ForeignKey(School, on_delete=models.CASCADE, editable=False, related_name='classroom_performances', help_text='School to which the classroom belongs.')
    
    last_updated = models.DateTimeField(auto_now=True)

    classroom_performance_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['classroom', 'term', 'school'], name='unique_classroom_term_performance')
        ]

    def __str__(self):
        return f"Grade {self.classroom.grade.grade} Term {self.term.term} - classroom {self.classroom.group}, classroomnumber {self.classroom.classroom_number} performance data"
                
    def save(self, *args, **kwargs):
        """
        Custom save method:
        - Validate before saving.
        - Provide meaningful error messages on IntegrityError.
        """
        self.clean()
        try:
            super().save(*args, **kwargs)
        except IntegrityError as e:
            # Handle any database integrity errors (such as unique or foreign key constraints).
            error_message = str(e).lower()
            # Check for unique constraint violations.
            if 'unique constraint' in error_message:
                if 'classrooms_classroom.subject' in error_message:
                    raise ValidationError(_('Could not process your request, classroom performance for the specified term already exists. The system will try to update the already existing records instead.'))
            # Re-raise the original exception if it's not related to unique constraints
            raise
        except Exception as e:
            raise ValidationError(_(str(e)))  # Catch and raise any exceptions as validation errors

    def clean(self):
        if not self.classroom_id:
            raise ValidationError('A classroom must either be a register class or be associated with a subject. Please review the provided information and try again.')

        if not self.classroom.subject:
            raise ValidationError('A classroom must either be a register class or be associated with a subject. Please review the provided information and try again.')

        if not self.term_id:
            raise ValidationError('The subject associated with this classroom is assigned to a different grade. Ensure that the subject belongs to the same grade as the classroom.')

    def update_performance_metrics(self):
        """
        Update the classroom's performance metrics based on the current term's student performance.
        This method calculates and updates:
        - Pass rate
        - Failure rate
        - Average, highest, lowest, median scores
        - Standard deviation of scores
        - Percentile distribution
        - Top performers
        - Improvement and completion rates
        """
        if not self.classroom.subject:
            return
        
        performances = self.classroom.subject.student_performances.filter(student__in=self.classroom.students.all(), term=self.term)            
        if not performances.exists():
            self.pass_rate = self.failure_rate = self.average_score = None
            self.median_score = self.std_dev_score = self.percentile_distribution = None
            return
        
        pass_mark = self.classroom.subject.pass_mark

        performance_data = performances.aggregate(
            highest_score=models.Max('normalized_score'),
            lowest_score=models.Min('normalized_score'),
            average_score=models.Avg('normalized_score'),
            stddev=models.StdDev('normalized_score'),
            students_in_the_classroom_count=models.Count('id'),
            students_passing_the_classroom_count=models.Count('id', filter=models.Q(normalized_score__gte=pass_mark)),
        )
        # print(f'performance_data {performance_data}')

        # Find students who passed the subject in the current term
        self.pass_rate = (performance_data['students_passing_the_classroom_count'] / performance_data['students_in_the_classroom_count']) * 100
        self.failure_rate = 100 - self.pass_rate
        # print(f'pass_rate {self.pass_rate}')

        self.highest_score = performance_data['highest_score']
        self.lowest_score = performance_data['lowest_score']
        self.average_score = performance_data['average_score']
        self.standard_deviation = performance_data['stddev']

        # Retrieve all scores and the associated student for the assessment
        student_scores = np.array(performances.order_by('normalized_score').values_list('normalized_score', 'student_id'))
        # print(f'student_scores {student_scores}')
        # Extract weighted scores for all students
        scores = student_scores[:, 0]  # Extract the first column (weighted_score)
        # print(f'scores {scores}')

        # Calculate median score
        self.median_score = np.median(scores)
        # print(f'median_score {self.median_score}')

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
        # print(f'percentile_distribution {self.percentile_distribution}')

        # Calculate improvement rate
        previous_term = term_utilities.get_previous_term(school=self.school, grade=self.term.grade, end_date=self.term.start_date)
        # print(f'previous_term {previous_term}')
        if previous_term:
            previous_scores = self.classroom.subject.student_performances.filter(student__in=self.students.all(), term=previous_term).values_list('normalized_score', flat=True)
            if previous_scores:
                improved_students = performances.filter(normalized_score__gt=models.F('previous_score')).count()
                self.improvement_rate = (improved_students / performance_data['students_in_the_classroom_count']) * 100 if performance_data['students_in_the_classroom_count'] > 0 else 0
            else:
                self.improvement_rate = None
        else:
            self.improvement_rate = None
        # print(f'improvement_rate {self.improvement_rate}')

        student_submissions = self.classroom.students.annotate(
            submission_count=models.Count(
                'submissions',
                filter=models.Q(~models.Q(submissions__status='NOT_SUBMITTED'), submissions__assessment__classroom=self, submissions__assessment__term=self.term, submissions__assessment__formal=True),
            )
        )
        # print(f'student_submissions {student_submissions}')
        # Track the total number of required assessments per student
        required_assessments = self.classroom.subject.assessments.filter(classroom=self, term=self.term, formal=True).count()
        # print(f'required_assessments {required_assessments}')

        # Calculate the completion rate
        completed_students = student_submissions.filter(submission_count__gte=required_assessments).count()
        self.completion_rate = (completed_students / performance_data['students_in_the_classroom_count']) * 100
        # print(f'completion_rate {self.completion_rate}')

        # Determine top performers
        top_performers_count = 3
        top_performers = performances.filter(normalized_score__gte=self.subject.pass_mark).order_by('-normalized_score').values_list('student_id', flat=True)[:top_performers_count]
        if top_performers.exists():
            self.top_performers.set(top_performers)
        # print(f'top_performers {top_performers}')

        # Query to get students who are failing the subject in the current term
        students_failing_the_classroom = performances.filter(normalized_score__lt=self.classroom.subject.pass_mark).values_list('student_id', flat=True)
        if students_failing_the_classroom.exists():
            self.students_failing_the_classroom.set(students_failing_the_classroom)
        # print(f'students_failing_the_classroom {students_failing_the_classroom}')

        self.save()

        term_performance, created = self.term.subject_performances.get_or_create(subject=self.classroom.subject, defaults={'school':self.school})
        term_subject_performances_tasks.update_term_performance_metrics_task.delay(term_performance_id=term_performance.id)
        # print(f'term_performance {term_performance}')
        print(f'classroom performance metrics calculated successfully')

