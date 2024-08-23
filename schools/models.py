# python 
import uuid

# django 
from django.db import models, IntegrityError
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.core.validators import validate_email

# school district choices
SCHOOL_DISTRICT_CHOICES = [
    # gauteng districts
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
    # Add more districts as needed
]

# school type choices
SCHOOL_TYPE_CHOICES = [
    ('PRIMARY', 'Primary'),
    ('SECONDARY', 'Secondary'),
    ('HYBRID', 'Hybrid'),
    ('TERTIARY', 'Tertiary'),
    # Add more types as needed
]

# province choices
PROVINCE_CHOICES = [
    ('GAUTENG', 'Gauteng'),
]

class School(models.Model):
    
    name = models.CharField(_('school name'), max_length=64)
    email = models.EmailField(_('school email address'), max_length=64, unique=True)
    contact_number = models.CharField(_('school contact number'), max_length=15, unique=True)

    student_count = models.IntegerField(default=0)
    teacher_count = models.IntegerField(default=0)
    admin_count = models.IntegerField(default=0)
    
    in_arrears = models.BooleanField(_('school bill'), default=False)
    none_compliant = models.BooleanField(_('school denied access'), default=False)
    
    # e.g., Primary, Secondary, High School, etc.
    type = models.CharField(_('school type'), max_length=50, choices=SCHOOL_TYPE_CHOICES, default="PRIMARY")
    # School District or Region
    province = models.CharField(_('province'), max_length=100, choices=PROVINCE_CHOICES, default="GAUTENG")
    # School District or Region
    district = models.CharField(_('school district'), max_length=100, choices=SCHOOL_DISTRICT_CHOICES, default="GAUTENG NORTH")
    
    # Grading System Details
    grading_system = models.TextField(blank=True, null=True)

    # Library Details
    library_details = models.TextField(blank=True, null=True)
    # Laboratory Details
    laboratory_details = models.TextField(blank=True, null=True)
    # Sports Facilities Details
    sports_facilities = models.TextField(blank=True, null=True)

    operating_hours = models.CharField(max_length=12, blank=True, null=True)
    location = models.CharField(_('school location'), max_length=100, blank=True, null=True)

    # others
    website = models.CharField(max_length=256, blank=True, null=True)
    logo = models.ImageField(upload_to='school_logos/', blank=True, null=True)

    # school account id 
    school_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    
    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name
    
    def clean(self):
        """
        Perform custom validation for the School model.
        """
        if self.contact_number:
            if not self.contact_number.isdigit():
                raise ValidationError(_('contact number should contain only digits'))
            if len(self.contact_number) < 10 or len(self.contact_number) > 15:
                raise ValidationError(_('contact number should be between 10 and 15 digits'))
        
        if self.email:
            try:
                validate_email(self.email)
            except ValidationError:
                raise ValidationError(_('the provided email address is not in a valid format. please correct the email address and try again'))
            
            if School.objects.filter(email=self.email).exclude(pk=self.pk).exists():
                raise ValidationError(_('a school account with the provided email address already exists'))
            
            if len(self.email) > 254:
                raise ValidationError(_("email address cannot exceed 254 characters"))
        
        if self.logo and not self.logo.name.endswith(('.png', '.jpg', '.jpeg')):
            raise ValidationError(_('school logo must be a PNG or JPG/JPEG image'))

        # Validate choice fields
        if self.type not in dict(SCHOOL_TYPE_CHOICES).keys():
            raise ValidationError(_('provided school type is invalid'))
        if self.province not in dict(PROVINCE_CHOICES).keys():
            raise ValidationError(_('provided school province is invalid'))
        if self.district not in dict(SCHOOL_DISTRICT_CHOICES).keys():
            raise ValidationError(_('provided school district is invalid'))


    def save(self, *args, **kwargs):
        """
        Override save method to handle custom validation and additional processing.
        """
        self.clean()

        try:
            super().save(*args, **kwargs)

        except Exception as e:
            raise ValidationError(_(str(e).lower()))

