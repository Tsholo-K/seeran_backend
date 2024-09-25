# python
import uuid

# django 
from django.db import models, IntegrityError
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from django.utils import timezone

# models
from users.models import Student
from assessments.models import Assessment


class Submission(models.Model):
    """
    Tracks the submission of a student's work for a specific assessment. Each submission
    is associated with a student and an assessment, and records whether the submission 
    was on time, late, or not submitted.
    """

    # Choices for submission status, indicating whether the submission was on time, late, or not submitted.
    SUBMISSION_STATUS_CHOICES = [
        ('ONTIME', 'On Time'),
        ('LATE', 'Late'),
        ('NOT_SUBMITTED', 'Not Submitted'),
        ('EXCUSED', 'Excused')
    ]

    # The student who submitted (or failed to submit) the assessment.
    # CASCADE ensures that when a student is deleted, their submissions are also deleted.
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='submissions')

    # The date and time when the submission was created. Automatically set on creation.
    submission_date = models.DateTimeField(auto_now_add=True)

    # Status of the submission: 'On Time', 'Late', or 'Not Submitted'.
    status = models.CharField(max_length=20, choices=SUBMISSION_STATUS_CHOICES, default='ONTIME')

    # The assessment for which the submission is made.
    # CASCADE ensures that when an assessment is deleted, all related submissions are also deleted.
    assessment = models.ForeignKey(Assessment, on_delete=models.CASCADE, related_name='submissions')

    # Timestamp to track when the submission was last updated.
    last_updated = models.DateTimeField(auto_now=True)

    # A unique identifier for each submission, generated using UUID.
    submission_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)

    class Meta:
        """
        Meta options to ensure that:
        - Each student can only have one submission per assessment.
        - Submissions are ordered by submission date, with the most recent first.
        - Indexing is added on the assessment and student fields for query performance.
        """
        constraints = [
            models.UniqueConstraint(fields=['assessment', 'student'], name='unique_student_assessment_submission')
        ]
        ordering = ['-submission_date']
        indexes = [models.Index(fields=['assessment', 'student'])]

    def save(self, *args, **kwargs):
        """
        Override the save method to:
        - Call the clean() method before saving to ensure all validations are enforced.
        - Handle IntegrityErrors related to unique constraints (such as a duplicate submission).
        """
        self.clean()  # Ensure validation rules are followed

        try:
            super().save(*args, **kwargs)  # Call the base save method to save the instance
        except IntegrityError as e:
            # Handle unique constraint violation for duplicate submissions
            if 'unique constraint' in str(e).lower():
                raise ValidationError('Could not process your request, a submission for this assessment and student already exists. Please add the student to the existing submission list for this assessment instead of creating a new one.')
            else:
                raise  # Re-raise any other exceptions
        except Exception as e:
            raise ValidationError(_(str(e)))

    def clean(self):
        """
        Validation logic for ensuring data consistency and correctness:
        - Automatically sets the submission status to 'ONTIME' or 'LATE' if it's a new submission.
        - Validates that the submission date is after the assessment's set date.
        """
        if not self.pk:  # If this is a new submission
            if not self.status:
                # Check if the current time is before or after the deadline and set status accordingly
                if timezone.now() <= self.assessment.dead_line and not self.assessment.collected:
                    self.status = 'ONTIME'
                else:
                    self.status = 'LATE'

        # Validate that the submission date is not before the assessment was set
        if self.submission_date and self.submission_date < self.assessment.date_set:
            raise ValidationError(_('Could not process your request, cannot collect submissions before the date the assessment was set.'))

