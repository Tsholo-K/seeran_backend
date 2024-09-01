# python 
import uuid

# django 
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError

# models
from users.models import Student
from assessments.models import Assessment


class Transcript(models.Model):
    """
    Model to represent a student's transcript for a specific assessment.
    """
    # The student who received the score
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='my_transcripts')

    # The score the student received in the assessment
    score = models.DecimalField(max_digits=5, decimal_places=2)

    # The score recieved by the student after moderation
    moderated_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    # the date the score was updated from the intital score
    moderated_date = models.DateTimeField(null=True, blank=True)

    # The assessment for which the score is recorded
    assessment = models.ForeignKey(Assessment, on_delete=models.CASCADE, related_name='student_scores')

    # transcript id
    transcript_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)

    class Meta:
        ordering = ['-assessment__due_date']
        indexes = [models.Index(fields=['student', 'assessment'])]  # Index for performance

    def __str__(self):
        return f"{self.assessment.unique_identifier} - {self.student.name}"

    def clean(self):
        if self.moderated_score is not None and (self.moderated_score < 0 or self.moderated_score > self.assessment.total):
            raise ValidationError(f'the students moderated score must be within the range of 0 to {self.assessment.total}')

        if self.score < 0 or self.score > self.assessment.total:
            raise ValidationError(f'the students score must be within the range of 0 to {self.assessment.total}')
        
    def save(self, *args, **kwargs):
        """
        Override save method to validate incoming data
        """
        self.clean()

        try:
            super().save(*args, **kwargs)
        except Exception as e:
            raise ValidationError(_(str(e).lower()))