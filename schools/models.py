# python 
import uuid

# django 
from django.db import models
from django.utils.translation import gettext_lazy as _


class School(models.Model):
    
    
    ########################################### required fields #############################################
    
    
    name = models.CharField(_('school name'), max_length=100)
    email = models.EmailField(_('school email address'), max_length=255)
    contact_number = models.CharField(_('school contact number'), max_length=15)
    
    in_arrears = models.BooleanField(_('school bill'), default=False)
    none_compliant = models.BooleanField(_('school denied access'), default=False)

    # school type choices
    SCHOOL_TYPE_CHOICES = [
        ('PRIMARY', 'Primary'),
        ('SECONDARY', 'Secondary'),
        ('HYBRID', 'Hybrid'),
        ('TERTIARY', 'Tertiary'),
        # Add more types as needed
    ]
    school_type = models.CharField(_('school type'), max_length=50, choices=SCHOOL_TYPE_CHOICES, default="PRIMARY")  # e.g., Primary, Secondary, High School, etc.
    
    # province choices
    PROVINCE_CHOICES = [
        ('GAUTENG', 'Gauteng'),
    ]
    province = models.CharField(_('province'), max_length=100, choices=PROVINCE_CHOICES, default="GAUTENG")  # School District or Region

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
    school_district = models.CharField(_('school district'), max_length=100, choices=SCHOOL_DISTRICT_CHOICES, default="")  # School District or Region

    # school account id 
    school_id = models.CharField(max_length=15, unique=True)   


    ##################################### fields set by school( not important ) ################################
    
    
    grading_system = models.TextField(blank=True, null=True)  # Grading System Details
    library_details = models.TextField(blank=True, null=True)  # Library Details
    laboratory_details = models.TextField(blank=True, null=True)  # Laboratory Details
    sports_facilities = models.TextField(blank=True, null=True)  # Sports Facilities Details
    operating_hours = models.CharField(max_length=100, blank=True, null=True)
    location = models.CharField(_('school location'), max_length=100, blank=True, null=True)

    # others
    website = models.URLField(max_length=200, blank=True, null=True)
    logo = models.ImageField(upload_to='school_logos/', blank=True, null=True)
    established_date = models.DateField(blank=True, null=True)
    accreditation = models.CharField(max_length=100, blank=True, null=True)
    academic_calendar = models.TextField(blank=True, null=True)
    curriculum_details = models.TextField(blank=True, null=True)  # Curriculum Details
    school_motto = models.CharField(max_length=255, blank=True, null=True)  # School Motto or Mission Statement
    

    ############################################### model extra details ###########################################


    class Meta:
        verbose_name = _('school')
        verbose_name_plural = _('schools')

    def __str__(self):
        return self.name

    # school account id creation handler
    def save(self, *args, **kwargs):
        if not self.school_id:
            self.school_id = self.generate_unique_id('SA')

        super(School, self).save(*args, **kwargs)

    @staticmethod
    def generate_unique_id(prefix=''):
      
        max_attempts = 10
       
        for _ in range(max_attempts):
            unique_part = uuid.uuid4().hex[:13]  # Take only the first 13 characters
            id = f"{prefix}{unique_part}"
            if not School.objects.filter(school_id=id).exists():
                return id
        raise ValueError('failed to generate a unique account ID after 10 attempts, please try again later.')
