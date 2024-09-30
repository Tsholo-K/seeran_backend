# python 
import uuid

# django 
from django.db import models, IntegrityError
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

# models
from grades.models import Grade


class Subject(models.Model):
    """
    Represents a school subject (e.g., Mathematics, English) and its related properties.

    Each subject is tied to a specific grade, and the subject model includes various fields
    for tracking both static information (subject name, whether it's a major subject, etc.)
    and dynamic information such as student and teacher counts.

    Key features:
    - Subjects are uniquely tied to a grade, preventing duplicate subjects within the same grade.
    - Provides fields for tracking the subject pass mark, counts of students/teachers, and related data.
    """

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

    # The name of the subject, limited to 64 characters and chosen from a predefined set of subjects.
    # The choices come from a constant SCHOOL_SUBJECTS_CHOICES (e.g., [("ENGLISH", "English"), ("MATH", "Mathematics")]).
    subject = models.CharField(_('Subject'), max_length=64, choices=SCHOOL_SUBJECTS_CHOICES, default="ENGLISH")

    # A boolean flag to indicate if this is a "major" subject (e.g., core subjects like Math or Science).
    major_subject = models.BooleanField(default=False)

    # The passing mark for this subject, defaulting to 40.00, with a maximum precision of 5 digits and 2 decimal places.
    # For example, a passing mark could be 40.00%, but this can be adjusted per subject.
    pass_mark = models.DecimalField(max_digits=5, decimal_places=2, default=40.00)

    # The number of students enrolled in this subject. This value should be updated as students are enrolled or leave the subject.
    student_count = models.PositiveBigIntegerField(default=0)

    # The number of teachers assigned to teach this subject. Useful for balancing workload and teacher assignment.
    teacher_count = models.PositiveBigIntegerField(default=0)

    # The number of classrooms associated with this subject. For instance, if a subject is taught across multiple rooms.
    classroom_count = models.PositiveBigIntegerField(default=0)

    # Links the subject to a specific grade level, establishing a one-to-many relationship where
    # each grade can have multiple subjects but a subject is associated with only one grade.
    grade = models.ForeignKey(Grade, on_delete=models.CASCADE, editable=False, related_name='subjects')

    # A foreign key reference to the school the grade is associated with. 
    # The subject is linked to a school, and if the school is deleted, the subject will be deleted as well (CASCADE).
    school = models.ForeignKey('schools.School', on_delete=models.CASCADE, editable=False, related_name='subjects')

    # Tracks the last time this subject's record was updated in the database.
    # Automatically updates whenever the record is saved, without needing manual intervention.
    last_updated = models.DateTimeField(auto_now=True)

    timestamp = models.DateTimeField(auto_now_add=True)
    # A UUID field to uniquely identify the subject. Using UUID ensures uniqueness even across distributed systems.
    subject_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)

    class Meta:
        """
        Meta options define constraints, ordering, and indexing for the Subject model.
        """
        # A unique constraint that prevents the same subject from being entered multiple times for the same grade.
        constraints = [
            models.UniqueConstraint(fields=['grade', 'subject'], name='unique_grade_subject')
        ]
        # Default ordering for querying subjects, sorting by subject name alphabetically.
        ordering = ['subject']
        # Adds an index to the combination of subject and grade fields to speed up queries.
        indexes = [models.Index(fields=['subject', 'grade'])]

    def __str__(self):
        """
        The string representation of the Subject model, which returns the subject name.
        This makes it more readable in admin panels and for debugging purposes.
        """
        return self.subject

    def save(self, *args, **kwargs):
        """
        Overrides the default save method to add custom validation and error handling.

        - Ensures that the subject is associated with a grade before saving.
        - Attempts to catch and handle IntegrityError related to unique constraint violations, providing
          more user-friendly error messages if a duplicate subject is detected.
        """
        self.clean()  # Ensure the model's fields are valid before saving.
        try:
            super().save(*args, **kwargs)  # Call the original save method
        except IntegrityError as e:
            error_message = str(e).lower()
            # Handle unique constraint errors gracefully and provide useful feedback.
            if 'unique constraint' in error_message:
                if 'subject' in error_message:
                    raise ValidationError(_('Could not process your request, the subject "{}" already exists for the selected grade. Duplicate subjects are not permitted. Please choose a different subject for this grade or check existing subjects.').format(self.subject))
            # If it's not handled, re-raise the original exception
            raise

    def clean(self):
        """
        Custom validation method for ensuring that the pass mark is within a valid range (0 to 100).
        This method is called before the subject is saved to ensure data integrity.
        """
        if not self.grade_id:
            raise ValidationError(_('Could not process your request, a subject needs to be associated with a school grade. Please provide a grade before saving the subject.'))
        if self.subject not in dict(Subject.SCHOOL_SUBJECTS_CHOICES).keys():
            raise ValidationError(_('Could not process your request, the specified school subject is invalid. Please choose a valid subject from the provided options.'))
        # Ensure the pass mark is between 0 and 100
        if not (0 <= self.pass_mark <= 100):
            raise ValidationError(_('Could not process your request, the subject\'s pass mark must be between 0.00 and 100.00.'))

