# python 
import uuid

# django 
from django.db import models, IntegrityError
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError


class Grade(models.Model):
    """
    Represents a grade level within a school, storing information about student count,
    grade ordering, major/non-major subject failure criteria, and more.

    Attributes:
        SCHOOL_GRADES_CHOICES (list): A list of predefined grade levels, ranging from Grade 000 to Grade 12.

        grade (CharField): Represents the grade level (e.g., 'Grade 1', 'Grade R'), chosen from SCHOOL_GRADES_CHOICES. 
            The grade field is not editable once created.
        grade_order (PositiveIntegerField): Numerical representation of the grade order for sorting purposes. Automatically set based on grade.
        
        student_count (IntegerField): The number of students currently enrolled in the grade. Defaults to 0.

        major_subjects (PositiveIntegerField): The number of major subjects a student needs to fail in order to fail a term.
        none_major_subjects (PositiveIntegerField): The number of non-major subjects a student needs to fail in order to fail a term.

        last_updated (DateTimeField): Timestamp automatically set to the current date/time whenever the grade object is modified.

        school (ForeignKey): ForeignKey relation linking the grade to a specific School instance. The grade is associated with a single school.

        grade_id (UUIDField): Unique identifier for the grade, automatically generated upon creation.

    Meta:
        unique_together (tuple): Ensures that each school can only have one unique instance of each grade (prevents duplicate grades).
        ordering (list): The default ordering for querysets is by grade_order.
        indexes (list): Indexing on the combination of grade and school for better query performance.

    Methods:
        clean(): Validates that major_subjects and none_major_subjects are non-negative and logically valid.
            Also checks that grades are valid based on school type (Primary or Secondary).
        save(*args, **kwargs): Overrides the save method to validate incoming data and set the grade_order automatically.
        __str__(): Returns a string representation of the grade in the format "Grade X (Order: Y)".
    """
    # Choice options for the various school grade levels, ranging from early childhood (Grade 000, Grade 00, Grade R) 
    # to Grade 12, which represents the final year of secondary school.
    SCHOOL_GRADES_CHOICES = [
        ('000', 'Grade 000'),  # Early childhood/pre-school level.
        ('00', 'Grade 00'),    # Early childhood/pre-school level.
        ('R', 'Grade R'),      # Pre-primary level.
        ('1', 'Grade 1'),      # Primary school starts from here.
        ('2', 'Grade 2'), 
        ('3', 'Grade 3'),
        ('4', 'Grade 4'), 
        ('5', 'Grade 5'), 
        ('6', 'Grade 6'),
        ('7', 'Grade 7'),      # End of primary school.
        ('8', 'Grade 8'),      # Start of secondary school.
        ('9', 'Grade 9'), 
        ('10', 'Grade 10'), 
        ('11', 'Grade 11'), 
        ('12', 'Grade 12')     # Final year of secondary school.
    ]

    # The grade level is stored as a CharField, with a predefined set of choices from the SCHOOL_GRADES_CHOICES.
    grade = models.CharField(_('school grade'), choices=SCHOOL_GRADES_CHOICES, max_length=4, editable=False)

    # This field is used to define the order of grades numerically, for easy sorting and retrieval.
    # For example, 'Grade 1' will have a lower order number than 'Grade 12'.
    grade_order = models.PositiveIntegerField()

    # The number of students currently assigned to this grade in the school.
    student_count = models.PositiveBigIntegerField(default=0)
    # The number of teachers currently assigned to this grade in the school.
    teacher_count = models.PositiveBigIntegerField(default=0)
    # The number of classrooms currently assigned to this grade in the school.
    classroom_count = models.PositiveBigIntegerField(default=0)
    # The number of terms currently assigned to this grade in the school.
    term_count = models.PositiveBigIntegerField(default=0)
    # The number of subjects currently assigned to this grade in the school.
    subject_count = models.PositiveBigIntegerField(default=0)

    # Number of major subjects a student in this grade needs to fail in order to fail the term.
    major_subjects = models.PositiveIntegerField(default=1)

    # Number of non-major subjects a student in this grade needs to fail in order to fail the term.
    none_major_subjects = models.PositiveIntegerField(default=2)

    # The time the grade record was last updated.
    last_updated = models.DateTimeField(auto_now=True)

    # A foreign key reference to the school the grade is associated with. 
    # The grade is linked to a school, and if the school is deleted, the grade will be deleted as well (CASCADE).
    school = models.ForeignKey('schools.School', on_delete=models.CASCADE, editable=False, related_name='grades')

    timestamp = models.DateTimeField(auto_now_add=True)
    # A unique UUID field to identify each grade instance across the system.
    grade_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)

    class Meta:
        # Ensures that within each school, a grade can only appear once (no duplicates).
        constraints = [
            models.UniqueConstraint(fields=['grade', 'school'], name='unique_school_grade')
        ]
        # Orders grades based on their grade_order field, so that they can be retrieved in the correct order (e.g., Grade 1, Grade 2).
        ordering = ['grade_order']
        # Indexes for improved performance when querying by grade and school fields.
        indexes = [models.Index(fields=['grade', 'school'])]

    def __str__(self):
        # String representation of the grade, useful for debugging and in Django admin.
        return f"Grade {self.grade} (Order: {self.grade_order})"

    def save(self, *args, **kwargs):
        """
        Overrides the default save method to validate incoming data and calculate the grade_order for new instances.
        """
        # Only set the grade_order for new instances (no primary key yet).
        if not self.pk:
            # Ensure the grade is valid and set the grade_order based on the SCHOOL_GRADES_CHOICES.
            if self.grade:
                try:
                    # Extracting the grade keys from the choices and assigning order based on position.
                    self.grade_order = [choice[0] for choice in self.SCHOOL_GRADES_CHOICES].index(self.grade)
                except ValueError:
                    raise ValidationError(_('Could not process your request, the provided grade level is invalid. Please choose a grade from the available options and try again.'))

        # Clean and validate the instance.
        self.clean()
        try:
            # Save the grade record.
            super().save(*args, **kwargs)
        except IntegrityError as e:
            # Handle any database integrity errors (such as unique or foreign key constraints).
            error_message = str(e).lower()
            # Check for unique constraint violations.
            if 'unique constraint' in error_message:
                if 'grade' in error_message:
                    raise ValidationError(_('Could not process your request, the provided grade already exists for your school, duplicate grades are not permitted. Please choose a different grade.'))
            # Re-raise the original exception if it's not specifically handled.
            raise ValidationError(_(error_message))
        except Exception as e:
            raise ValidationError(_(str(e)))  # Catch and raise any exceptions as validation errors
    
    def clean(self):
        """
        Custom validation method for the Grade model. Ensures that fields contain valid data.
        """
        # Ensure a school is linked to the grade.
        if not self.school_id:
            raise ValidationError(_('Could not process your request, a grade needs to be associated with a school. Please provide a school and try again.'))
        
        # Ensure major_subjects and non-major_subjects are non-negative.
        if self.major_subjects < 0 or self.none_major_subjects < 0:
            raise ValidationError(_('Could not process your request, major subjects and non-major subjects must be non-negative integers. Please correct the values and try again.'))

        # Ensure at least one subject is required for the grading criteria.
        if self.major_subjects + self.none_major_subjects <= 0:
            raise ValidationError(_('Could not process your request, you must specify at least one major or non-major subject for the grading criteria. Please correct the values and try again.'))

        # Validate that the grade level is set.
        if not self.grade:
            raise ValidationError(_('Could not process your request, a grade cannot have an empty level. Please ensure you provide a valid grade level and try again.'))

        # Only apply integer checks for numeric grade levels
        try:
            grade_num = int(self.grade)
            if self.school.type == 'PRIMARY' and grade_num > 7:
                raise ValidationError(_('Could not process your request, primary schools cannot assign grades higher than Grade 7. Please choose a valid grade for primary school and try again.'))
            if self.school.type == 'SECONDARY' and grade_num <= 7:
                raise ValidationError(_('Could not process your request, secondary schools must assign grades higher than Grade 7. Please update the grade accordingly.'))
        except ValueError:
            # Handle non-numeric grades like 'R', '00', '000'
            if self.school.type in ['SECONDARY', 'TERTIARY'] and self.grade in ['R', '00', '000']:
                raise ValidationError(_('Could not process your request, secondary and tertiary schools cannot assign non-numeric grades such as "R", "00", or "000". Please select a valid numeric grade.'))

