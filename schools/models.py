# python 
import uuid

# django 
from django.db import models, IntegrityError
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from django.core.validators import validate_email


class School(models.Model):
    """
    Represents a school entity, storing information about the school's details, 
    including its name, contact information, type, district, and additional facilities.

    Attributes:
        name (CharField): The name of the school. Limited to 64 characters.
        email (EmailField): The school's email address, which must be unique and valid.
        contact_number (CharField): The school's contact number, which must be unique, contain only digits, and be between 10-15 characters long.
        
        student_count (IntegerField): The total number of students currently enrolled in the school.
        teacher_count (IntegerField): The total number of teachers working in the school.
        admin_count (IntegerField): The total number of administrative staff at the school.

        in_arrears (BooleanField): Boolean flag indicating whether the school has outstanding bills.
        none_compliant (BooleanField): Boolean flag indicating whether the school has been denied access due to non-compliance.

        type (CharField): The type of the school (e.g., Primary, Secondary, Hybrid, Tertiary) with choices predefined in SCHOOL_TYPE_CHOICES.
        province (CharField): The province where the school is located, selected from PROVINCE_CHOICES.
        district (CharField): The district or region where the school operates, selected from SCHOOL_DISTRICT_CHOICES.

        grading_system (TextField): Information on the grading system the school uses (optional).
        library_details (TextField): Information on the school's library resources (optional).
        laboratory_details (TextField): Information on the school's laboratory resources (optional).
        sports_facilities (TextField): Information on the school's sports facilities (optional).

        operating_hours (CharField): The school's general operating hours (optional).
        location (CharField): Physical location or address of the school (optional).

        website (CharField): The school's website URL (optional).
        logo (ImageField): An image file representing the school's logo (optional).

        last_updated (DateTimeField): Automatically updated timestamp whenever the school object is modified.

        school_id (UUIDField): Unique identifier for the school, automatically generated upon creation.

    Meta:
        ordering (list): The default ordering for querysets is by the name field in ascending order.

    Methods:
        clean(): Ensures that the contact number is valid, the email is in the correct format, and other fields meet the constraints.
        save(*args, **kwargs): Overrides the save method to perform validation and save the school object.
        __str__(): Returns a string representation of the school, typically the school's name.
    """
    # Define choices for school districts in Gauteng
    SCHOOL_DISTRICT_CHOICES = [
        # List of school districts in Gauteng
        ('GAUTENG EAST', 'Gauteng East'),
        ('GAUTENG NORTH', 'Gauteng North'),
        ('GAUTENG WEST', 'Gauteng West'),
        ('JHB CENTRAL DISTRICT D14', 'JHB Central District D14'),
        ('JHB NORTH', 'JHB North'),
        ('JHB WEST', 'JHB West'),
        ('JHB SOUTH', 'JHB South'),
        ('JHB EAST', 'JHB EAST'),
        ('EKURHULENI SOUTH', 'Ekurhuleni South'),
        ('EKURHULENI NORTH', 'Ekurhuleni North'),
        ('TSHWANE SOUTH', 'Tshwane South'),
        ('TSHWANE NORTH', 'Tshwane North'),
        ('TSHWANE WEST', 'Tshwane West'),
        ('SEDIBENG EAST', 'Sedibeng East'),
        ('SEDIBENG WEST', 'Sedibeng West'),
        # More districts can be added as needed
    ]

    # Define choices for the type of school
    SCHOOL_TYPE_CHOICES = [
        ('PRIMARY', 'Primary'),       # Primary schools
        ('SECONDARY', 'Secondary'),   # Secondary schools
        ('HYBRID', 'Hybrid'),         # Schools with both primary and secondary education
        ('TERTIARY', 'Tertiary'),     # Colleges or universities
    ]

    # Define choices for provinces (Currently limited to Gauteng)
    PROVINCE_CHOICES = [
        ('GAUTENG', 'Gauteng'),  # Province of Gauteng
    ]

    # Fields for the model

    # Name of the school
    name = models.CharField(_('school name'), max_length=64)

    # Contact email address for the school
    email_address = models.EmailField(_('school email address'), max_length=254)

    # Contact phone number of the school, must be unique and validated later
    contact_number = models.CharField(_('school contact number'), max_length=15)

    # Counts of different types of staff members
    student_count = models.PositiveBigIntegerField(default=0)  # Number of students enrolled
    teacher_count = models.PositiveBigIntegerField(default=0)  # Number of teachers
    admin_count = models.PositiveBigIntegerField(default=0)    # Number of administrative staff

    # Billing and compliance statuses
    in_arrears = models.BooleanField(_('school bill'), default=False)  # Whether the school has unpaid bills
    none_compliant = models.BooleanField(_('school denied access'), default=False)  # Whether the school is non-compliant

    # School classification by type
    type = models.CharField(_('school type'), max_length=50, choices=SCHOOL_TYPE_CHOICES, default="PRIMARY")

    # Province in which the school is located
    province = models.CharField(_('province'), max_length=100, choices=PROVINCE_CHOICES, default="GAUTENG")

    # School district within the province
    district = models.CharField(_('school district'), max_length=100, choices=SCHOOL_DISTRICT_CHOICES, default="GAUTENG NORTH")

    # Additional school-related information
    grading_system = models.JSONField(blank=True, null=True)         # Details about the school's grading system
    library_details = models.TextField(blank=True, null=True)        # Information about the school's library
    laboratory_details = models.TextField(blank=True, null=True)     # Information about the school's laboratories
    sports_facilities = models.TextField(blank=True, null=True)      # Information about the school's sports facilities

    # Operational details
    operating_hours = models.CharField(max_length=12, blank=True, null=True)  # Operating hours (e.g., "08:00 - 15:00")
    location = models.CharField(_('school location'), max_length=100, blank=True, null=True)  # Physical address or location

    # School's website and logo
    website = models.URLField(blank=True, null=True)
    logo = models.ImageField(upload_to='school_logos/', blank=True, null=True)  # Upload for school logo image

    # Timestamp when the record was last updated
    last_updated = models.DateTimeField(auto_now=True)

    # Unique ID for the school, automatically generated
    school_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)

    class Meta:
        # A unique constraint that prevents schools from having the same contact number.
        constraints = [
            models.UniqueConstraint(fields=['email_address'], name='unique_school_email_address'),
            models.UniqueConstraint(fields=['contact_number'], name='unique_school_contact_number')
        ]
        # Default ordering of schools by name
        ordering = ['name']

    def __str__(self):
        # String representation of the model, used in admin and other places
        return self.name

    def save(self, *args, **kwargs):
        """
        Override the save method to ensure custom validation is executed before saving.
        """
        self.clean()  # Call the clean method for validation
        try:
            super().save(*args, **kwargs)  # Proceed with saving the model if no validation errors
        except IntegrityError as e:
            error_message = str(e).lower()
            # Handle unique constraint errors gracefully and provide useful feedback.
            if 'unique constraint' in error_message:
                if 'email_address' in error_message:
                    raise ValidationError(_('The email address provided is already in use by another school. Please use a different email address or contact support if you believe this is an error.'))
                elif 'contact_number' in error_message:
                    raise ValidationError(_('The contact number provided is already in use by another school. Please use a unique contact number or verify if the correct number has been entered.'))
            # If it's not handled, re-raise the original exception
            raise ValidationError(_(error_message))
        except Exception as e:
            raise ValidationError(_(str(e)))  # Catch and raise any exceptions as validation errors

    def clean(self):
        """
        Custom validation method to ensure data integrity for contact number, email, and logo.
        Raises ValidationError if any field contains invalid data.
        """
        # Validate contact number
        if self.contact_number:
            try:
                if not self.contact_number.isdigit():
                    raise ValidationError(_('The contact number provided contains non-numeric characters. Please enter a numeric only contact number (e.g., 0123456789).'))
            except Exception as e:
                raise ValidationError(_(str(e)))
            if len(self.contact_number) < 10 or len(self.contact_number) > 15:
                raise ValidationError(_('The contact number must be between 10 and 15 digits long. Please provide a valid contact number within this range.'))

        # Validate email
        if self.email_address:
            try:
                validate_email(self.email_address)
            except ValidationError:
                raise ValidationError(_('The email address provided is not valid. Please provide a valid email address in the format name@domain.com. If you are unsure, check with your email provider.'))
            if len(self.email_address) > 254:
                raise ValidationError(_('The email address exceeds the maximum allowed length of 254 characters. Please provide a shorter email address or use an alias.'))

        # Validate school logo format
        if self.logo and not self.logo.name.endswith(('.png', '.jpg', '.jpeg')):
            raise ValidationError(_('The school logo must be in PNG, JPG, or JPEG format. Please upload an image file with one of these extensions.'))

        # Validate choice fields
        if self.type not in dict(self.SCHOOL_TYPE_CHOICES).keys():
            raise ValidationError(_('The selected school type is invalid. Please choose a valid option from Primary, Secondary, Hybrid, or Tertiary.'))
        if self.province not in dict(self.PROVINCE_CHOICES).keys():
            raise ValidationError(_('The selected province is invalid. Please choose one from the available options.'))
        if self.district not in dict(self.SCHOOL_DISTRICT_CHOICES).keys():
            raise ValidationError(_('The selected district is invalid. Please choose a valid school district from the provided options.'))

