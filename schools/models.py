# django imports
from django.apps import apps
from django.db import models
from django.utils.translation import gettext_lazy as _

# models

# utility functions
from authentication.utils import generate_account_id


class School(models.Model):
    
    
    #### required fields ####
    
    
    name = models.CharField(_('school name'), max_length=100)
    email = models.EmailField(_('school email address'), max_length=255)
    contact_number = models.CharField(_('school contact number'), max_length=15)

    # school type choices
    SCHOOL_TYPE_CHOICES = [
        ('PRIMARY', 'Primary'),
        ('SECONDARY', 'Secondary'),
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
    school_id = models.CharField(max_length=15, unique=True, default=generate_account_id('SC')) # school account
        
    # all required fields
    REQUIRED_FIELDS = ['name', 'email', 'location', 'contact_number', 'school_type', 'school_district']


    #### fields set by school ####
    
    
    # important particulars
    grading_system = models.TextField(blank=True, null=True)  # Grading System Details
    number_of_classrooms = models.IntegerField(blank=True, null=True)  # Number of Classrooms
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
    # courses_offered = models.ManyToManyField(Course, related_name='school_courses')  # List of Courses/Subjects Offered
    school_motto = models.CharField(max_length=255, blank=True, null=True)  # School Motto or Mission Statement
    
    class Meta:
        verbose_name = _('school')
        verbose_name_plural = _('schools')

    def __str__(self):
        return self.name

