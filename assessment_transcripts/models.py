# python 
import uuid

# django 
from django.db import models, IntegrityError
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError


class AssessmentTranscript(models.Model):
    """
    Represents a transcript for a student in a particular assessment.
    
    Stores the student's score in the assessment, along with any moderation applied
    to the score, and calculates a weighted score as a normalized percentage. It also
    handles validation of whether the student has submitted the assessment and whether
    the assessment is collected (ready for grading). Each transcript is unique per 
    student-assessment pair.
    """

    # The student who is associated with this transcript. 
    # This is a ForeignKey relationship with the 'Student' model.
    # If the student is deleted, all associated transcripts are also deleted (CASCADE).
    student = models.ForeignKey('accounts.Student', on_delete=models.CASCADE, related_name='transcripts')

    # The student's raw score in the assessment. Stored as a DecimalField for precision.
    # The score can range from 0 to the total points of the assessment.
    score = models.DecimalField(max_digits=5, decimal_places=2)

    # Optional field allowing teachers to leave comments on the student's performance.
    # The field can be blank or null if no comments are provided.
    comment = models.TextField(max_length=1024, null=True, blank=True)
    
    # The student's score in the assessment as a percentage relative to the weight of the assessment
    # This is calculated based on either the raw or moderated score.
    percent_score = models.DecimalField(max_digits=5, decimal_places=2)

    # The student's normalized score in the form of a percentage (weighted score).
    # The weighted score can range from 0 to 100.
    weighted_score = models.DecimalField(max_digits=5, decimal_places=2)

    # The student's score after moderation (if applicable). Moderation can happen
    # for various reasons like grading consistency. This field is optional.
    moderated_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)

    # Optional field allowing teachers to leave comments on the student's performance.
    # The field can be blank or null if no comments are provided.
    moderator_comment = models.TextField(max_length=1024, null=True, blank=True)

    # The date and time when the score was updated after moderation.
    # This field is optional and is only set if the score is moderated.
    moderated_date = models.DateTimeField(null=True, blank=True)

    # The student's percentile in the assessment. This field is optional and could be used
    # for analytics or comparative purposes.
    percentile = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)

    # ForeignKey to the 'Assessment' model, linking the transcript to a specific assessment.
    # If the assessment is deleted, all associated transcripts are also deleted (CASCADE).
    assessment = models.ForeignKey('assessments.Assessment', on_delete=models.CASCADE, related_name='transcripts')

    # A foreign key reference to the school the grade is associated with. 
    # The grade is linked to a school, and if the school is deleted, the grade will be deleted as well (CASCADE).
    school = models.ForeignKey('schools.School', on_delete=models.CASCADE, editable=False, related_name='transcripts')

    # This field is automatically updated to the current date and time whenever the
    # transcript is modified.
    last_updated = models.DateTimeField(auto_now=True)

    timestamp = models.DateTimeField(auto_now_add=True)
    # A unique identifier for each transcript, generated using UUID to ensure uniqueness.
    # This field is non-editable and is assigned when the transcript is created.
    transcript_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)

    class Meta:
        """
        Meta options to enforce uniqueness, ordering, and indexing:
        
        - UniqueConstraint ensures that each student can only have one transcript
          per assessment.
        - Default ordering is by the student's surname, then first name, and finally
          by their account ID (to handle cases where names might be the same).
        - An index is created on the student and assessment fields to optimize queries.
        """
        constraints = [
            models.UniqueConstraint(fields=['student', 'assessment'], name='unique_student_assessment_transcript')
        ]
        ordering = ['student__surname', 'student__name', 'student__account_id']
        indexes = [models.Index(fields=['student', 'assessment'])]

    def __str__(self):
        """
        String representation of the transcript, returning the assessment's unique 
        identifier and the student's name for easy identification.
        """
        return f"{self.assessment.unique_identifier} - {self.student.name}"

    def save(self, *args, **kwargs):
        """
        Override the save method to ensure that the clean() method is called before
        saving the transcript. This ensures that all custom validation is enforced.
        
        Also handles unique constraint errors gracefully, providing user-friendly
        error messages if an attempt is made to create a duplicate transcript for a 
        student in the same assessment.
        """
        # Perform validation before saving
        self.clean()
        try:
            # Call the parent class's save method to actually save the instance
            super().save(*args, **kwargs)
        except IntegrityError as e:
            # Handle unique constraint violations (e.g., if a duplicate transcript exists)
            if 'unique constraint' in str(e).lower():
                raise ValidationError('Could not process your request, the provided student already has a transcript for this assessment. Try updating the student\'s score instead. Duplicate assessment transcripts for the same student in the same assessment are not permitted.')
            raise
        except Exception as e:
            # Catch all other exceptions and raise them as validation errors
            raise ValidationError(_(str(e).lower()))

    def clean(self):
        """
        Custom validation logic for ensuring data integrity:
        
        - Ensures the assessment has been collected before grading (required before adding a score).
        - Ensures the student has actually submitted the assessment before grading them.
        - Ensures the score and moderated score (if present) are within valid ranges (0 to assessment total).
        - Calculates the weighted score based on the score or moderated score.
        
        This method is called automatically before saving the model (via save method) or 
        can be manually invoked.
        """
        # Ensure that the assessment is flagged as collected before grading
        if not self.assessment.collected:
            raise ValidationError('Could not process your request, The provided assessment has not been collected. Please make sure to flag the assessment as collected before grading any students.')

        # Ensure that the student has submitted the assessment
        if not self.assessment.submissions.filter(student=self.student).exists():
            raise ValidationError('Could not process your request, the provided student did not submit the assessment. Cannot grade an unsubmitted assessment. Please make sure to collect the student\'s assessment before grading.')

        # Validate moderated score if present and calculate the weighted score
        if self.moderated_score:
            if self.moderated_score < 0 or self.moderated_score > self.assessment.total:
                raise ValidationError(f'Could not process your request, the student\'s moderated score must be within the range of 0 to {self.assessment.total}.')
            self.percent_score = (self.moderated_score / self.assessment.total) * 100
        else:
            # Validate the raw score and calculate the weighted score based on it
            if self.score < 0 or self.score > self.assessment.total:
                raise ValidationError(f'Could not process your request, the student\'s score must be within the range of 0 to {self.assessment.total}.')
            self.percent_score = (self.score / self.assessment.total) * 100

        self.weighted_score = self.percent_score * (self.assessment.percentage_towards_term_mark / 100) if self.assessment.formal > 0 else 0

