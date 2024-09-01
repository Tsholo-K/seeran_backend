# python 
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
    # The user who set the assessment
    assessor = models.ForeignKey(BaseUser, on_delete=models.SET_NULL, related_name='assessed_assessments', null=True)
    # The date and time when the assessment was created
    date_set = models.DateTimeField(auto_now_add=True, default=timezone.now)  # Allowed format: yyyy-mm-ddThh:mm

    # The date and time when the assessment is due
    due_date = models.DateTimeField()  # Allowed format: yyyy-mm-ddThh:mm

    title = models.CharField(max_length=124)
    topics = models.ManyToManyField(Topic, related_name='assessments')

    # Unique identifier for the assessment
    unique_identifier = models.CharField(max_length=36)
    # Type of the assessment (e.g., practical, exam, test)
    assessment_type = models.CharField(max_length=124, default='EXAMINATION')

    # Total score possible for the assessment
    total = models.IntegerField()

    # Indicates if the assessment is formal
    formal = models.BooleanField(default=False)
    # Percentage weight towards the term mark
    percentage_towards_term_mark = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)

    # Term during which the assessment is given
    term = models.ForeignKey(Term, on_delete=models.CASCADE, related_name='assessments')
    
    # The students who are assessed
    students_assessed = models.ManyToManyField(Student, related_name='assessments_taken')

    # Indicates if the assessment has been collected
    assessed = models.BooleanField(default=False)
    # Date and time when the assessment was collected
    date_assessed = models.DateTimeField(null=True, blank=True)

    # the students who submitted the assessment before the due date elapsed
    ontime_submission = models.ManyToManyField(Student, related_name='ontime_submissions', blank=True)
    # the students who submitted the assessment after the due date elapsed
    late_submission = models.ManyToManyField(Student, related_name='late_submissions', blank=True)

    # the students who did not submit the assessment
    not_submitted = models.ManyToManyField(Student, related_name='not_submitted', blank=True)

    # Indicates if the assessment results have been released
    grades_released = models.BooleanField(default=False)
    # Date and time when results were released
    date_grades_released = models.DateTimeField(null=True, blank=True)

    # The user who moderated the assessment
    moderator = models.ForeignKey(BaseUser, on_delete=models.SET_NULL, related_name='assessments_moderated', null=True)
    # The classroom where the assessment was conducted
    classroom = models.ForeignKey(Classroom, on_delete=models.SET_NULL, related_name='assessments', null=True, blank=True)

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
        if self.assessor:
            # Get the appropriate model for the requesting user's role
            Model = role_specific_maps.account_access_control_mapping[self.assessor.role]

            # Retrieve the user and related school in a single query using select_related
            assessor = Model.objects.select_related('school').only('school', 'role').get(account_id=self.assessor.account_id)

            if assessor not in ['PRINCIPAL', 'ADMIN', 'TEACHER'] or assessor.school != self.school:
                raise ValidationError('only principals, admins, and teachers can set assessments.')
        
        if self.moderator:
             # Get the appropriate model for the requesting user's role
            Model = role_specific_maps.account_access_control_mapping[self.moderator.role]

            # Retrieve the user and related school in a single query using select_related
            moderator = Model.objects.select_related('school').only('school', 'role').get(account_id=self.moderator.account_id)

            if moderator not in ['PRINCIPAL', 'ADMIN', 'TEACHER'] or moderator.school != self.school:
                raise ValidationError('only principals, admins, and teachers can moderate assessments.')

        # Convert due_date to a timezone-aware datetime
        if self.due_date and timezone.is_naive(self.due_date):
            self.due_date = timezone.make_aware(self.due_date, timezone.get_current_timezone())
        
        # Check if due_date is in the future
        if self.due_date and self.due_date < timezone.now():
            raise ValidationError('the due date must be in the future.')
        
        # Convert date_assessed to a timezone-aware datetime
        if self.date_assessed and timezone.is_naive(self.date_assessed):
            self.date_assessed = timezone.make_aware(self.date_assessed, timezone.get_current_timezone())
        
        # Ensure date_assessed is after due_date
        if self.date_assessed and self.date_assessed < self.due_date:
            raise ValidationError('date assessed cannot be before the due date.')

        # Aggregate the total percentage of existing assessments for this term and subject
        total_percentage = self.term.assessments.filter(subject=self.subject).exclude(pk=self.pk).aggregate(total_percentage=models.Sum('percentage_towards_term_mark'))['total_percentage'] or Decimal('0.00')
        
        # Round the total to avoid float precision issues
        total_percentage = total_percentage.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        
        if self.percentage_towards_term_mark is None:
            self.percentage_towards_term_mark = Decimal('0.00')
        
        # Ensure the percentage is within the valid range
        if not (Decimal('0.00') <= self.percentage_towards_term_mark <= Decimal('100.00')):
            raise ValidationError('percentage towards the term mark must be between 0 and 100.')
        
        # Ensure total percentage doesn't exceed 100%
        if (total_percentage + self.percentage_towards_term_mark) > Decimal('100.00'):
            raise ValidationError('total percentage towards the term cannot exceed 100%.')
        
        # Validate that students do not appear in multiple submission status fields
        all_assessed_students = set(self.students_assessed.all())
        
        ontime_students = set(self.ontime_submission.all())
        late_students = set(self.late_submission.all())
        not_submitted_students = set(self.not_submitted.all())
        
        # Check for overlap between ontime and late submissions
        if ontime_students.intersection(late_students):
            raise ValidationError('a student cannot be both an on-time and late submission.')

        # Check for overlap between not submitted and any submissions
        if not_submitted_students.intersection(ontime_students.union(late_students)):
            raise ValidationError('a student marked as not submitted cannot be in on-time or late submissions.')

        # Ensure all submission-related students are part of the assessed students
        if not (ontime_students <= all_assessed_students and late_students <= all_assessed_students and not_submitted_students <= all_assessed_students):
            raise ValidationError('some submission statuses are set for students not part of the assessed students.')
        
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

