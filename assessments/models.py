# python
import uuid
from decimal import Decimal, ROUND_HALF_UP
import numpy as np

# django 
from django.db import models, transaction
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.apps import apps

# utility functions 
from accounts import utils as accounts_utilities

# tasks
from term_subject_performances import tasks as  term_subject_performances_tasks
from classroom_performances import tasks as  classroom_performances_tasks
from assessments import tasks as  assessments_tasks


class Assessment(models.Model):
    """
    This model represents an academic assessment conducted in a school. It tracks various aspects such as 
    who set and moderated the assessment, the start and deadline times, the assessment's weight in the term mark, 
    and statistics related to the assessment (e.g., pass rates, scores). It also maintains relationships to other models 
    such as classrooms, grades, and students.
    """
    
    ASSESSMENT_TYPE_CHOICES = [
        ('EXAMINATION', 'Examination'),
        ('TEST', 'Test'),
        ('PRACTICAL', 'Practical'),
        ('ASSIGNMENT', 'Assignment'),
        ('HOMEWORK', 'Homework'),
        ('QUIZ', 'Quiz'),
        ('PROJECT', 'Project'),
        ('PRESENTATION', 'Presentation'),
        ('LAB_WORK', 'Lab Work'),
        ('FIELD_TRIP', 'Field Trip'),
        ('GROUP_WORK', 'Group Work'),
        ('SELF_ASSESSMENT', 'Self Assessment'),
        ('PEER_ASSESSMENT', 'Peer Assessment'),
        ('PORTFOLIO', 'Portfolio'),
        ('RESEARCH_PAPER', 'Research Paper'),
        ('CASE_STUDY', 'Case Study'),
        ('DISCUSSION', 'Discussion'),
        ('DEBATE', 'Debate'),
        ('ROLE_PLAY', 'Role Play'),
        ('SIMULATION', 'Simulation'),
        ('ESSAY', 'Essay'),
        ('MULTIPLE_CHOICE', 'Multiple Choice'),
        ('OBSERVATION', 'Observation'),
        ('INTERVIEW', 'Interview'),
        ('DIAGNOSTIC', 'Diagnostic'),
        ('FORMATIVE', 'Formative'),
        ('SUMMATIVE', 'Summative'),
    ]

    # The user (assessor) who set the assessment.
    # SET_NULL ensures that if the user is deleted, the assessment isn't deleted, but the assessor field is set to null.
    assessor = models.ForeignKey('accounts.BaseAccount', on_delete=models.SET_NULL, related_name='assessed_assessments', null=True)

    # The user who moderated (oversaw) the assessment.
    # Moderators ensure the fairness and quality of the assessment.
    moderator = models.ForeignKey('accounts.BaseAccount', on_delete=models.SET_NULL, related_name='assessments_moderated', null=True)

    # Optional date and time when the assessment is set to begin.
    start_time = models.DateTimeField(null=True, blank=True)

    # Required date and time by which the assessment must be completed.
    dead_line = models.DateTimeField()

    # Title or name of the assessment (e.g., "Midterm Exam").
    title = models.CharField(max_length=124)

    # Topics covered in the assessment, allowing many-to-many relationships to the Topic model.
    topics = models.ManyToManyField('topics.Topic', related_name='assessments')

    # Type of assessment (e.g., test, exam, or practical). A predefined list of choices must be used.
    assessment_type = models.CharField(max_length=124, choices=ASSESSMENT_TYPE_CHOICES, default='TEST')

    # The total score possible in this assessment (e.g., out of 100 points).
    total = models.DecimalField(max_digits=5, decimal_places=2)

    # Whether this assessment is formal or informal. Formal assessments contribute to the student's final term mark.
    formal = models.BooleanField(default=False)

    # The percentage weight of this assessment towards the term's overall mark.
    # For example, if this assessment counts for 20% of the term's grade.
    percentage_towards_term_mark = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)

    # The term (e.g., "Term 1") in which the assessment takes place.
    term = models.ForeignKey('terms.Term', on_delete=models.CASCADE, related_name='assessments')

    # Whether the assessment has been collected (i.e., whether all students have submitted their work).
    collected = models.BooleanField(default=False)

    # Timestamp indicating when the assessment was collected (if applicable).
    date_collected = models.DateTimeField(null=True, blank=True)

    # Whether the grades for this assessment being released released to the students.
    releasing_grades = models.BooleanField(default=False)

    # Whether the grades for this assessment have been released to the students.
    grades_released = models.BooleanField(default=False)
    # Timestamp when the grades were released (if applicable).
    date_grades_released = models.DateTimeField(null=True, blank=True)

    # Pass and failure rates for the assessment, calculated based on students' scores.
    pass_rate = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    failure_rate = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)

    # The highest score achieved by any student in this assessment.
    highest_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    # The lowest score achieved by any student in this assessment.
    lowest_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    # The average score for this assessment.
    average_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)

    # The median score (the middle value in the distribution of scores).
    median_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)

    # The most frequent score achieved by students in this assessment.
    mode_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)

    # A JSON field that stores the percentile distribution of students' scores (e.g., 10th, 25th, 50th percentile).
    percentile_distribution = models.JSONField(null=True, blank=True)

    # The standard deviation of the scores, a measure of how spread out the scores are.
    standard_deviation = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)

    # The interquartile range (IQR), a measure of statistical spread in the scores.
    interquartile_range = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)

    # The percentage of students who completed the assessment (submitted their work).
    completion_rate = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)

    # Many-to-many relationship to the top-performing students in this assessment.
    top_performers = models.ManyToManyField('accounts.Student', related_name='top_performers_assessments', blank=True)
    # Many-to-many relationship to the students who failed this assessment.
    students_who_failed_the_assessment = models.ManyToManyField('accounts.Student', related_name='failed_assessments', help_text='Students who failed the assessment.')

    # Foreign key linking to the classroom where this assessment was conducted (optional).
    classroom = models.ForeignKey('classrooms.Classroom', on_delete=models.CASCADE, related_name='assessments', null=True, blank=True)

    # Foreign keys linking to the subject and grade for which this assessment is conducted.
    subject = models.ForeignKey('subjects.Subject', on_delete=models.CASCADE, related_name='assessments')
    grade = models.ForeignKey('grades.Grade', on_delete=models.CASCADE, related_name='assessments')

    # Foreign key linking to the school where the assessment took place.
    school = models.ForeignKey('schools.School', on_delete=models.CASCADE, related_name='assessments')

    # This field is automatically updated to the current date and time whenever the
    # assessment is modified.
    last_updated = models.DateTimeField(auto_now=True)

    timestamp = models.DateTimeField(auto_now_add=True)
    # A unique identifier for each assessment (UUID).
    assessment_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)

    class Meta:
        # Order assessments by the due date, with the latest due date first.
        ordering = ['-dead_line']
        # Add an index to improve query performance on commonly filtered fields (subject, grade, school).
        indexes = [models.Index(fields=['subject', 'grade', 'school'])]

    def __str__(self):
        # Returns a string representation of the unique identifier for this assessment.
        return str(self.assessment_id)
        
    @transaction.atomic
    def save(self, *args, **kwargs):
        """
        Overrides the save method to run custom validation logic via the clean method.
        Also handles potential integrity errors related to unique constraints.
        """
        self.clean()
        try:
            super().save(*args, **kwargs)
        except Exception as e:
            raise ValidationError(_(str(e).lower()))

    def clean(self):
        """
        Custom validation to ensure business logic is respected before saving the assessment.
        For example, it ensures the following:
        - The assessment is linked to a valid grade, term, subject, and school.
        - The start time is before the deadline.
        - Moderators and assessors are from the same school and have valid roles.
        - The total percentage towards the term mark does not exceed 100%.
        """
        if not self.grade:
            raise ValidationError(_('Could not proccess your request, assessments must be assigned to a grade.'))

        if not self.term:
            raise ValidationError(_('Could not proccess your request, assessments must be assigned to a term.'))

        if not self.subject:
            raise ValidationError(_('Could not proccess your request, assessments must be assigned to a subject.'))

        if not self.school:
            raise ValidationError(_('Could not proccess your request, assessments must be assigned to a school.'))

        if self.total < 1:
            raise ValidationError(_('Could not proccess your request, assessments total can not be less than 1.'))
        
        # Validating the assessor's role and ensuring they belong to the same school as the assessment.
        if self.assessor:
            if self.assessor.role not in ['PRINCIPAL', 'ADMIN', 'TEACHER']:
                raise ValidationError(_('Could not proccess your request, only principals, admins, and teachers can set assessments.'))
            assessor = accounts_utilities.get_account_and_linked_school(self.assessor.account_id, self.assessor.role)
            if assessor.school != self.school:
                raise ValidationError(_('Could not proccess your request, assessors can only create assessments for their own school.'))

        # Similar validation for the moderator.
        if self.moderator:
            if self.moderator.role not in ['PRINCIPAL', 'ADMIN', 'TEACHER']:
                raise ValidationError(_('Could not proccess your request, only principals, admins, and teachers can moderate assessments.'))
            moderator = accounts_utilities.get_account_and_linked_school(self.moderator.account_id, self.moderator.role)
            if moderator.school != self.school:
                raise ValidationError(_('Could not proccess your request, moderators can only oversee assessments from their own school.'))

        # Ensure the start time is before the deadline.
        if self.start_time and self.dead_line:
            if self.start_time > self.dead_line:
                raise ValidationError(_('Could not proccess your request, the assessment\'s start time cannot be after the deadline.'))

        # Ensure date_collected is after the start time, if applicable.
        if self.date_collected and self.start_time:
            if self.date_collected < self.start_time:
                raise ValidationError(_('Could not proccess your request, you cannot collect an assessment before its start time.'))

        # Calculate the total percentage of all assessments for this term and subject.
        total_percentage = self.term.assessments.filter(subject=self.subject).exclude(pk=self.pk).aggregate(total_percentage=models.Sum('percentage_towards_term_mark'))['total_percentage'] or Decimal('0.00')
               
        # Round the total to avoid float precision issues
        total_percentage = total_percentage.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        
        if self.percentage_towards_term_mark is None:
            self.percentage_towards_term_mark = Decimal('0.00')
        
        # Ensure the percentage is within the valid range
        if not (Decimal('0.00') <= self.percentage_towards_term_mark <= Decimal('100.00')):
            raise ValidationError(_('Could not proccess your request, percentage towards the term mark must be between 0 and 100.'))
        
        # Ensure total percentage doesn't exceed 100%
        if (total_percentage + self.percentage_towards_term_mark) > Decimal('100.00'):
            raise ValidationError(_('Could not proccess your request, total percentage towards the term cannot exceed 100%.'))
        
        if not self.classroom:
            self.unique_identifier = None
        
        # Set assessment as formal if it contributes to the term mark
        self.formal = self.percentage_towards_term_mark > Decimal('0.00')
    
    @transaction.atomic
    def mark_as_collected(self):
        """
        Marks the assessment as collected. This should be called only after the assessment's deadline has passed or all submissions have been received.
        Raises validation errors if the conditions for marking as collected are not met.
        """
        if self.collected:
            raise ValidationError(_('Could not proccess your request, the provided assessment has already been flagged as collected.'))

        if timezone.now() > self.dead_line:
            self.collected = True
            self.date_collected = timezone.now()

        else:
            students_who_have_submitted_count = self.submissions.count()
            students_accessed_count = (self.classroom.students.count() if self.classroom else self.grade.students.count())

            if students_who_have_submitted_count == students_accessed_count:
                self.collected = True
                self.date_collected = timezone.now()
            else:
                raise ValidationError(_('Could not proccess your request, can not flag assessment as collected unless its past the deadline or all students have submitted the assessment.'))
        
        self.save()

    @transaction.atomic
    def release_grades(self):
        """
        Releases the grades for the assessment after verifying all submissions are graded. Grades can only be released if all submissions have been 
        graded. If a student has not submitted their work, their assessment submission will be marked as 'NOT_SUBMITTED' and a score of 0 will be given.
        Raises validation errors if grades cannot be released (e.g., missing submissions).
        """
        if not self.collected:
            raise ValidationError(_('could not proccess your request, the provided assessment has not been collected. can not release grades for an assessment that has not been collected'))

        # Get the list of students who have already submitted the assessment
        students_who_have_submitted_ids = self.submissions.values_list('student_id', flat=True)
        students_who_have_submitted_count = len(students_who_have_submitted_ids)

        graded_student_count = self.scores.count()

        if students_who_have_submitted_count != graded_student_count:
            raise ValidationError(_('could not proccess your request, some submissions have not been graded. please make sure to grade all submissions and try again'))
        
        # Get the Submission model dynamically
        Submission = apps.get_model('submissions', 'Submission')
        # Get the Transcript model dynamically
        Transcript = apps.get_model('transcripts', 'Transcript')

        students_who_have_not_submitted = (self.classroom.students.exclude(id__in=students_who_have_submitted_ids) if self.classroom else self.grade.students.exclude(id__in=students_who_have_submitted_ids))
        if students_who_have_not_submitted.exists():
            non_submissions = []
            penalties = []
            for student in students_who_have_not_submitted:
                non_submissions.append(Submission(assessment=self, student=student, status='NOT_SUBMITTED'))
                penalties.append(Transcript(assessment=self, student=student, score=0, weighted_score=0, percent_score=0, comment='you have failed to submit this assessment and have been penalized for non submission'))
            
            batch_size = 50
            for i in range(0, len(non_submissions), batch_size):
                Submission.objects.bulk_create(non_submissions[i:i + batch_size])

            for i in range(0, len(penalties), batch_size):
                Transcript.objects.bulk_create(penalties[i:i + batch_size])

        self.releasing_grades = False

        self.grades_released = True
        self.date_grades_released = timezone.now()

        self.save()

        accessed_students = (self.classroom.students if self.classroom else self.grade.students)
        for student in accessed_students.all():
            performance, created = student.subject_performances.get_or_create(subject=self.subject, term=self.term, defaults={'grade':self.grade, 'school':self.school})
            performance.update_performance_metrics()
        
        assessments_tasks.update_assessment_performance_metrics_task.delay(assessment_id=self.id)
        print(f'grades released successfully')

    @transaction.atomic
    def update_performance_metrics(self):
        """
        Updates key performance metrics for the assessment, such as pass rate, failure rate, 
        completion rate, highest score, lowest score, standard deviation, and percentile distribution.
        This method is called after grades are released.
        """
        if not self.grades_released:
            raise ValidationError(_('could not process your request, the assessment does not have its grades released. cannot calculate performance metrics for an assessment that does not have its grades released.'))

        transcripts = self.scores
        if not transcripts.exists():
            self.standard_deviation = self.interquartile_range = self.mode_score = None
            self.completion_rate = self.completion_rate = self.pass_rate = self.failure_rate = None
            return
        
        accessed_students_count = (self.classroom.students.count() if self.classroom else self.grade.students.count())

        if accessed_students_count == 0:
            self.completion_rate = self.pass_rate = self.failure_rate = None
            return

        # Completion rate (percentage of students who submitted)
        submission_count = self.submissions.exclude(models.Q(status='NOT_SUBMITTED') | models.Q(status='EXCUSED')).count()
        self.completion_rate = (submission_count / accessed_students_count) * 100

        transcript_data = transcripts.aggregate(
            avg_score=models.Avg('percent_score'),
            passed_students=models.Count('id', filter=models.Q(percent_score__gte=self.subject.pass_mark)),
            highest=models.Max('percent_score'),
            lowest=models.Min('percent_score'),
            stddev=models.StdDev('percent_score'),
        )

        # Calculate pass rate and failure rate
        self.pass_rate = (transcript_data['passed_students'] / accessed_students_count) * 100
        self.failure_rate = 100 - self.pass_rate

        self.average_score = transcript_data['avg_score']
        self.highest_score = transcript_data['highest']
        self.lowest_score = transcript_data['lowest']
        self.standard_deviation = transcript_data['stddev']

        # Retrieve all scores and the associated student for the assessment
        student_scores = np.array(transcripts.order_by('percent_score').values_list('percent_score', 'student_id'))
        # Extract weighted scores for all students
        scores = student_scores[:, 0]  # Extract the first column (weighted_score)

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

        # Get the Transcript model dynamically
        Transcript = apps.get_model('transcripts', 'Transcript')

        # Create a dictionary mapping student IDs to percentiles
        student_to_percentile = {}

        for student_id in students_in_10th_percentile:
            student_to_percentile[student_id] = Decimal(10.0)
        for student_id in students_in_25th_percentile:
            student_to_percentile[student_id] = Decimal(25.0)
        for student_id in students_in_50th_percentile:
            student_to_percentile[student_id] = Decimal(50.0)
        for student_id in students_in_75th_percentile:
            student_to_percentile[student_id] = Decimal(75.0)
        for student_id in students_in_90th_percentile:
            student_to_percentile[student_id] = Decimal(90.0)
        
        # Update each transcript with the calculated percentile
        transcripts_to_update = []
        for transcript in transcripts.all():
            student_id = transcript.student_id
            if student_id in student_to_percentile:
                transcript.percentile = student_to_percentile[student_id].quantize(Decimal('0.01'))
            else:
                transcript.percentile = Decimal(0.0)  # If no percentile found, set to 0.0
            transcripts_to_update.append(transcript)

        # Batch update the transcripts
        batch_size = 50
        for i in range(0, len(transcripts_to_update), batch_size):
            Transcript.objects.bulk_update(transcripts_to_update[i:i + batch_size], ['percentile'])

        # Calculate median score, standard deviation, and interquartile range (IQR)
        self.median_score = np.median(scores)

        # Calculate the mode score (most common score)
        unique_scores, counts = np.unique(scores, return_counts=True)
        self.mode_score = unique_scores[np.argmax(counts)]

        # Interquartile range (IQR)
        q1 = np.percentile(scores, Decimal(25))
        q3 = np.percentile(scores, Decimal(75))
        self.interquartile_range = Decimal(q3 - q1).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

        # Top 5 performers
        top_performers_count = 3
        top_performers = transcripts.filter(percent_score__gte=self.subject.pass_mark).order_by('-percent_score').values_list('student_id', flat=True)[:top_performers_count]
        if top_performers.exists():
            self.top_performers.set(top_performers)

        # Students Who Failed The Assessment
        students_who_failed_the_assessment = transcripts.filter(percent_score__lt=self.subject.pass_mark).values_list('student_id', flat=True)
        if students_who_failed_the_assessment.exists():
            self.students_who_failed_the_assessment.set(students_who_failed_the_assessment)

        self.save()
        
        if self.classroom:
            classroom_performances_tasks.update_classroom_performance_metrics_task.delay(classroom_id=self.classroom.id, term_id=self.term.id)
        else:
            term_performance, created = self.subject.termly_performances.get_or_create(term=self.term, defaults={'school': self.school})
            term_subject_performances_tasks.update_term_performance_metrics_task.delay(term_performance_id=term_performance.id)
        
        print(f'assessment performance metrics calculated successfully')


"""
    BREAKDOWN

    1. Completion Rate
        Context: The completion rate represents the percentage of students who submitted their assessment. 
            This metric is crucial because it provides an overview of student engagement and participation in the assessment process.
        Derivation:
            Completion Rate = (Number of submissions / Total number of students accessed) * 100 
            The method retrieves the total number of students who were assigned the assessment (either within the classroom or grade)
            and the number of students who actually submitted it. The ratio is then multiplied by 100 to get the percentage.
        Significance: 
            A low completion rate may indicate issues such as difficulty in accessing the assessment, lack of preparation,
            or low engagement. A high completion rate suggests that most students took the assessment seriously and participated fully.

    2. Pass Rate
        Context:
            The pass rate is the percentage of students who scored above or equal to the minimum passing mark set for the subject.
            It is a key metric in determining the success of students in an assessment.
        Derivation:
            Pass Rate = (Number of students who passed / Total number of students accessed) * 100
            The number of students who met or exceeded the passing mark is divided by the total number of students who participated in the assessment.
        Significance:
            A high pass rate indicates that most students understood the material and performed well, while a low pass rate may signify a
            challenging assessment or a gap in the students' understanding of the subject matter.

    3. Failure Rate
        Context:
            The failure rate is simply 100% minus the pass rate. It indicates the percentage of students who did not meet the minimum passing score.
        Derivation:
            Failure Rate= 100 - Pass Rate
        Significance:
            A high failure rate is a cause for concern and may indicate that either the assessment was too difficult or
            that students were not adequately prepared. It provides an opportunity for educators to investigate the reasons for poor performance.

    4. Highest Score
        Context:
            The highest score is the maximum score achieved by any student in the assessment.
        Derivation:
            The method finds the maximum value from the list of student scores using NumPy's np.max() function.
        Significance:
            This metric is often used to gauge the ceiling of student performance.
            It helps determine how well the top-performing students did, and it can provide a benchmark for the level of difficulty of the assessment.

    5. Lowest Score
        Context:
            The lowest score is the minimum score obtained by any student in the assessment.
        Derivation:
            The method finds the minimum value from the list of student scores using NumPy's np.min() function.
        Significance:
            The lowest score gives insight into the struggles of the lowest-performing students and whether there are
            significant gaps in understanding or participation issues.

    6. Average Score
        Context:
            The average score represents the mean score of all students who participated in the assessment.
        Derivation:
            Average Score = Sum of all scores / Total number of students
            This is calculated using Django's Avg function.
        Significance:
            The average score provides an overall sense of how well the group performed as a whole. It is a useful metric for
            comparing the difficulty of different assessments over time and for understanding the general level of student achievement.

    7. Median Score
        Context:
            The median score is the middle value when all scores are ordered. If the number of scores is even, it is the average of the two middle values.
        Derivation:
            Median Score= Middle score in ordered list of scores
            The method uses NumPy's np.median() function to calculate this.
        Significance:
            Unlike the average, the median is less affected by outliers (extremely high or low scores). It provides a better
            representation of the "typical" student performance, especially in skewed distributions.

    8. Standard Deviation
        Context:
            The standard deviation measures the amount of variation or dispersion in student scores.
        Derivation:
            can't be shown lmao, look it up
        Significance:
            A high standard deviation indicates a wide range of performance (i.e., some students performed much better or worse than others),
            while a low standard deviation suggests that most students performed similarly. This can help in understanding whether the
            assessment was uniformly understood or had polarizing difficulty.

    9. Mode Score
        Context:
            The mode score is the most frequently occurring score among all students.
        Derivation:
            NumPy's np.unique() function is used to identify the score that appears most often in the dataset.
        Significance:
            The mode score is helpful in identifying common performance levels. For example, if a large group of students received
            the same score, it might indicate that many students were either clustered around a specific level of understanding
            or that the assessment was designed in a way that naturally produced this result.

    10. Interquartile Range (IQR)
        Context:
            The interquartile range measures the spread between the 25th percentile (Q1) and the 75th percentile (Q3) of the scores.
        Derivation:
            IQR = Q3 - Q1 
            where Q1 is the 25th percentile and Q3 is the 75th percentile, calculated using NumPy's np.percentile() function.
        Significance:
            The IQR indicates the range within which the middle 50% of scores fall. It helps to identify how spread out the central
            group of students is and whether there is consistency in their performance. A smaller IQR suggests most students performed similarly,
            while a larger IQR indicates more variability.

    11. Percentile Distribution
        Context:
            The percentile distribution divides students into groups based on their relative rank in the assessment.
            The key percentiles calculated here are the 10th, 25th, 50th, 75th, and 90th.
        Derivation:
            Students are ranked based on their scores, and then split into groups based on these percentiles. For example,
            the top 10% of students are classified as the 90th percentile, and so on.
        Significance:
            This helps educators understand the distribution of student performance across different achievement levels.
            It identifies students who are excelling (top percentiles) and those who may need additional help (lower percentiles).

    12. Top Performers
        Context:
            This metric identifies the top-performing students in the assessment.
        Derivation:
            The method retrieves the top 3 students based on their weighted scores.
        Significance:
            Identifying top performers is important for recognizing excellence and encouraging high-achieving students.
            It may also guide opportunities for advanced learning or rewards.

    13. Students Who Failed the Assessment
        Context:
            This metric identifies students who failed to meet the passing threshold for the assessment.
        Derivation:
            The method filters students who scored below the passing mark.
        Significance:
            Identifying students who failed the assessment is important for intervention strategies, as these students may require
            additional support or remediation to improve their performance in future assessments.

    14. Percentile Rank of Each Student
        Context:
            Each student's performance is ranked in comparison to their peers.
        Derivation:
            The scores are sorted, and each student's score is mapped to its percentile rank. This is then updated in the student's transcript.
        Significance:
            This provides a relative measure of each student's performance, allowing educators and students to see where they stand
            compared to the rest of the group. It helps highlight both high achievers and those who are struggling.

    Conclusion
        The update_performance_metrics method calculates a comprehensive set of metrics that provide both a broad overview and detailed
        insights into student performance in the assessment. By analyzing these metrics, educators can understand overall trends, identify top
        performers and students who are struggling, and adjust their teaching strategies accordingly. Each metric offers a unique perspective
        on the students' performance, contributing to a holistic view of academic success and areas for improvement.

"""
