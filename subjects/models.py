# python 
import uuid
# import logging

# django 
from django.db import models, IntegrityError
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError

# models
from grades.models import Grade

# logger = logging.getLogger(__name__)


# subject choices
SCHOOL_SUBJECTS_CHOICES = [
    ('ENGLISH', 'English'),
    ('SEPEDI', 'Sepedi'),
    ('ZULU', 'Zulu'),
    ('AFRIKAANS', 'Afrikaans'),
    ('MATHEMATICS', 'Mathematics'),
    ('MATHEMATICS LITERACY', 'Mathematics Literacy'),
    ('TECHNICAL MATHEMATICS', 'Technical Mathematics'),
    ('PHYSICAL SCIENCE', 'Physical Science'),
    ('LIFE SCIENCE', 'Life Science'),
    ('BIOLOGY', 'Biology'),
    ('GEOGRAPHY', 'Geography'),
    ('ACCOUNTING', 'Accounting'),
    ('BUSINESS STUDIES', 'Business Studies'),
    ('AGRICULTURE', 'Agriculture'),
    ('TOURISM', 'Tourism'),
    ('LIFE ORIENTATION', 'Life Orientation'),
    ('SOCIAL SCIENCE', 'Social Science'),
    ('ARTS AND CULTURE', 'Arts And Culture'),
]

class Subject(models.Model):

    # grade linked to
    grade = models.ForeignKey(Grade, on_delete=models.CASCADE, editable=False, related_name='grade_subjects')
    subject = models.CharField(_('grade subject'), max_length=64, choices=SCHOOL_SUBJECTS_CHOICES, default="ENGLISH")

    student_count = models.IntegerField(default=0)
    teacher_count = models.IntegerField(default=0)
    classes_count = models.IntegerField(default=0)

    # field to indicate if it's a major subject
    major_subject = models.BooleanField(default=False)
    # subject-specific pass mark
    pass_mark = models.DecimalField(max_digits=5, decimal_places=2, default=40.00)

    # subject id
    subject_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)

    class Meta:
        unique_together = ('grade', 'subject')
        ordering = ['subject']
        indexes = [
            models.Index(fields=['subject', 'grade'])
        ]  # Index for performance

    def __str__(self):
        return self.subject

    def clean(self):
        """
        Validate that the pass mark is within a reasonable range.
        """
        if not (0 <= self.pass_mark <= 100):
            raise ValidationError(_('the subjects pass mark must be between 0 and 100'))

    def save(self, *args, **kwargs):
        """
        Override save method to validate incoming data.
        """
        if not self.pk:
            if not self.grade:
                raise ValidationError(_('a subject needs to be associated with a school grade'))
            
        self.clean()
            
        try:
            super().save(*args, **kwargs)
        except IntegrityError as e:
            error_message = str(e).lower()
            # logger.error('Integrity error occurred while saving Subject: %s', str(e))

            # Handle unique constraint errors
            if 'unique constraint' in error_message:

                if 'subject_id' in error_message:
                    raise ValidationError(_('The subject ID must be unique.'))
                
                elif 'grade_subject' in error_message:
                    raise ValidationError(_('The provided subject already exists for this grade. Duplicate subjects are not permitted.'))
                
                else:
                    raise ValidationError(_('A unique constraint error occurred.'))

            # Re-raise the original exception if it's not handled
            raise