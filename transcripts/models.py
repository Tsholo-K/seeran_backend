# python 
import uuid

# django 
from django.db import models, IntegrityError
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError

# models
from users.models import Student
from assessments.models import Assessment


class Transcript(models.Model):
    # The student who received the score
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='transcripts')

    # The score the student received in the assessment
    score = models.DecimalField(max_digits=5, decimal_places=2)
    # The normalized percentage score (weighted)
    weighted_score = models.DecimalField(max_digits=5, decimal_places=2)

    # The score recieved by the student after moderation
    moderated_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    # the date the score was updated from the intital score
    moderated_date = models.DateTimeField(null=True, blank=True)

    # The assessment for which the score is recorded
    assessment = models.ForeignKey(Assessment, on_delete=models.CASCADE, related_name='scores')

    # transcript id
    transcript_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)

    class Meta:
        unique_together = ('student', 'assessment')
        ordering = ['student__surname', 'student__name', 'student__account_id']
        indexes = [models.Index(fields=['student', 'assessment'])]  # Index for performance

    def __str__(self):
        return f"{self.assessment.unique_identifier} - {self.student.name}"

    def clean(self):
        if self.score < 0 or self.score > self.assessment.total:
            raise ValidationError(f'the students score must be within the range of 0 to {self.assessment.total}')
        
        # Calculate the weighted score (normalized to a percentage)
        if self.assessment.total > 0 and not self.moderated_score:
            self.weighted_score = (self.score / self.assessment.total) * 100
        
        if self.moderated_score:
            if (self.moderated_score < 0 or self.moderated_score > self.assessment.total):
                raise ValidationError(f'the students moderated score must be within the range of 0 to {self.assessment.total}')
            # If a moderated score exists, calculate its weighted value too
            self.weighted_score = (self.moderated_score / self.assessment.total) * 100

    def save(self, *args, **kwargs):
        self.clean()

        try:
            super().save(*args, **kwargs)

        except IntegrityError as e:
            # Check if the error is related to unique constraints
            if 'unique constraint' in str(e).lower():
                raise ValidationError(_('the provided student already has a transcript for this assessment. duplicate assessment transcripts for the same student and assessment is not permitted.'))
            else:
                # Re-raise the original exception if it's not related to unique constraints
                raise

        except Exception as e:
            raise ValidationError(_(str(e).lower()))