# python
from datetime import datetime
import uuid
from decimal import Decimal, ROUND_HALF_UP

# django 
from django.db import models, IntegrityError
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from django.utils import timezone

# models
from users.models import BaseUser, Student
from schools.models import School
from grades.models import Grade
from terms.models import Term
from subjects.models import Subject
from classes.models import Classroom
from topics.models import Topic

# mappings
from users.maps import role_specific_maps

    
class Assessment(models.Model):
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

    # The user who set the assessment
    assessor = models.ForeignKey(BaseUser, on_delete=models.SET_NULL, related_name='assessed_assessments', null=True)
    # The user who moderated the assessment
    moderator = models.ForeignKey(BaseUser, on_delete=models.SET_NULL, related_name='assessments_moderated', null=True)

    # The date and time when the assessment was created
    date_set = models.DateTimeField(auto_now_add=True, editable=False)  # Allowed format: yyyy-mm-ddThh:mm
    # The date the assessment is due
    due_date = models.DateField()  # Allowed format: yyyy-mm-dd

    # The time assessment is starts
    start_time = models.TimeField(null=True, blank=True)  # Allowed format: Thh:mm
    # The date and time when the assessment is due
    dead_line = models.TimeField()  # Allowed format: hh:mm

    title = models.CharField(max_length=124)
    topics = models.ManyToManyField(Topic, related_name='assessments')

    # Unique identifier for the assessment
    unique_identifier = models.CharField(max_length=36)
    # Type of the assessment (e.g., practical, exam, test)
    assessment_type = models.CharField(max_length=124, choices=ASSESSMENT_TYPE_CHOICES, default='TEST')

    # Total score possible for the assessment
    total = models.DecimalField(max_digits=5, decimal_places=2)

    # Indicates if the assessment is formal
    formal = models.BooleanField(default=False)
    # Percentage weight towards the term mark
    percentage_towards_term_mark = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)

    # Term during which the assessment is given
    term = models.ForeignKey(Term, on_delete=models.CASCADE, related_name='assessments')

    # Indicates if the assessment has been collected
    collected = models.BooleanField(default=False)
    # Date and time when the assessment was collected
    date_collected = models.DateTimeField(null=True, blank=True)

    # Indicates if the assessment results have been released
    grades_released = models.BooleanField(default=False)
    # Date and time when results were released
    date_grades_released = models.DateTimeField(null=True, blank=True)
    
    # The classroom where the assessment was conducted
    classroom = models.ForeignKey(Classroom, on_delete=models.CASCADE, related_name='assessments', null=True, blank=True)

    # the subject the assessment is for
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='assessments')
    # the grade the assessment is for
    grade = models.ForeignKey(Grade, on_delete=models.CASCADE, related_name='assessments')
    # The school where the assessment was conducted
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='assessments')

    # assessment id 
    assessment_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)

    class Meta:
        unique_together = ('unique_identifier', 'grade', 'classroom')
        ordering = ['-due_date']
        indexes = [models.Index(fields=['subject', 'grade', 'school'])]  # Index for performance

    def __str__(self):
        return self.unique_identifier

    def clean(self):
        if not self.grade:
            raise ValidationError(_('could not proccess your request, assessments need to be assigned to a grade.'))
        
        if not self.term:
            raise ValidationError(_('could not proccess your request, assessments need to be assigned to a term.'))
        
        if not self.subject:
            raise ValidationError(_('could not proccess your request, assessments need to be assigned to a subject.'))

        if self.assessor:
            # Get the appropriate model for the requesting user's role
            Model = role_specific_maps.account_access_control_mapping[self.assessor.role]

            # Retrieve the user and related school in a single query using select_related
            assessor = Model.objects.select_related('school').only('school', 'role').get(account_id=self.assessor.account_id)

            if assessor.role not in ['PRINCIPAL', 'ADMIN', 'TEACHER']:
                raise ValidationError(_('could not proccess your request, only principals, admins, and teachers can set assessments.'))

            if self.school and assessor.school != self.school:
                raise ValidationError(_('could not proccess your request, you can only create assessments for your own school'))
        
        if self.moderator:
             # Get the appropriate model for the requesting user's role
            Model = role_specific_maps.account_access_control_mapping[self.moderator.role]

            # Retrieve the user and related school in a single query using select_related
            moderator = Model.objects.select_related('school').only('school', 'role').get(account_id=self.moderator.account_id)

            if moderator.role not in ['PRINCIPAL', 'ADMIN', 'TEACHER']:
                raise ValidationError(_('could not proccess your request, only principals, admins, and teachers can moderate assessments.'))

            if self.school and assessor.school != self.school:
                raise ValidationError(_('could not proccess your request, accounts can only moderate assessments from their own school.'))

        # Convert date_collected to a timezone-aware datetime
        if self.date_collected and timezone.is_naive(self.date_collected):
            self.date_collected = timezone.make_aware(self.date_collected, timezone.get_current_timezone())

        # Ensure date_collected is after the start_time if available
        if self.date_collected and self.start_time:
            # Combine due_date and start_time into a single datetime
            start_datetime = datetime.combine(self.due_date, self.start_time)
            
            # Check if the date_collected is before the start_datetime
            if self.date_collected < start_datetime:
                raise ValidationError(_('you cannot collect an assessment before its start time. please update the assessment information or wait until the assessment has started.'))

        # Aggregate the total percentage of existing assessments for this term and subject
        total_percentage = self.term.assessments.filter(subject=self.subject).exclude(pk=self.pk).aggregate(total_percentage=models.Sum('percentage_towards_term_mark'))['total_percentage'] or Decimal('0.00')
        
        # Round the total to avoid float precision issues
        total_percentage = total_percentage.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        
        if self.percentage_towards_term_mark is None:
            self.percentage_towards_term_mark = Decimal('0.00')
        
        # Ensure the percentage is within the valid range
        if not (Decimal('0.00') <= self.percentage_towards_term_mark <= Decimal('100.00')):
            raise ValidationError(_('percentage towards the term mark must be between 0 and 100.'))
        
        # Ensure total percentage doesn't exceed 100%
        if (total_percentage + self.percentage_towards_term_mark) > Decimal('100.00'):
            raise ValidationError(_('total percentage towards the term cannot exceed 100%.'))
        
        if self.percentage_towards_term_mark > Decimal('0.00'):
            self.formal = True
        
    def save(self, *args, **kwargs):
        """
        Override save method to validate incoming data
        """
        self.clean()

        try:
            super().save(*args, **kwargs)

        except IntegrityError as e:
            # Check if the error is related to unique constraints
            if 'unique constraint' in str(e).lower():
                raise ValidationError(_('an assessment with the provided unique identifier in the specified classroom already exists. duplicate assessment unique identifiers within the same classroom is not permitted.'))
            else:
                # Re-raise the original exception if it's not related to unique constraints
                raise

        except Exception as e:
            raise ValidationError(_(str(e).lower()))


class Submission(models.Model):
    SUBMISSION_STATUS_CHOICES = [
        ('ONTIME', 'On Time'),
        ('LATE', 'Late'),
        ('NOT_SUBMITTED', 'Not Submitted'),
    ]

    assessment = models.ForeignKey(Assessment, on_delete=models.CASCADE, related_name='submissions')

    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='submissions')
    submission_date = models.DateTimeField(auto_now_add=True)

    status = models.CharField(max_length=20, choices=SUBMISSION_STATUS_CHOICES, default='ONTIME')

    # submission id 
    submission_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)

    class Meta:
        unique_together = ('assessment', 'student')
        ordering = ['-submission_date']
        indexes = [models.Index(fields=['assessment', 'student'])]

    def clean(self):
        # Ensure submission_date is within a valid range
        if self.submission_date and (self.submission_date < self.assessment.date_set):
            raise ValidationError(_('submission date must be after the date the assessment was set.'))
        
    def save(self, *args, **kwargs):
        """
        Override save method to validate incoming data
        """
        self.clean()

        try:
            super().save(*args, **kwargs)

        except IntegrityError as e:
            # Check if the error is related to unique constraints
            if 'unique constraint' in str(e).lower():
                raise ValidationError(_(f'there is no need to create a new {self.status} submission list for the provided assessment as it already exists. instead just add the students into the existing {self.status} submission list.'))
            else:
                # Re-raise the original exception if it's not related to unique constraints
                raise

        except Exception as e:
            raise ValidationError(_(str(e).lower()))