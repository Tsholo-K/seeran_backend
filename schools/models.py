# python 
import uuid
from datetime import timedelta

# django 
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError

class School(models.Model):
    """
    Model to represent a school entity.

    Attributes:
        name (CharField): The name of the school.
        email (EmailField): The contact email address for the school.
        contact_number (CharField): The contact phone number for the school.
        in_arrears (BooleanField): Indicates if the school is in arrears with payments.
        none_compliant (BooleanField): Indicates if the school is non-compliant and denied access.
        school_type (CharField): The type of school (e.g., Primary, Secondary).
        province (CharField): The province where the school is located.
        school_district (CharField): The school district within the province.
        school_id (UUIDField): A unique identifier for the school.
        grading_system (TextField): Information about the school's grading system.
        library_details (TextField): Details about the school's library.
        laboratory_details (TextField): Details about the school's laboratories.
        sports_facilities (TextField): Details about the school's sports facilities.
        operating_hours (CharField): The school's operating hours.
        location (CharField): The physical location of the school.
        website (URLField): The school's website URL.
        logo (ImageField): The school's logo.
        established_date (DateField): The date the school was established.
        accreditation (CharField): Accreditation information for the school.
        curriculum_details (TextField): Details about the school's curriculum.
        school_motto (CharField): The school's motto or mission statement.
    """
    
    # Basic school information
    name = models.CharField(_('school name'), max_length=100)
    email = models.EmailField(_('school email address'), max_length=255)
    contact_number = models.CharField(_('school contact number'), max_length=15)
    
    # Compliance and financial status
    in_arrears = models.BooleanField(_('school bill'), default=False)
    none_compliant = models.BooleanField(_('school denied access'), default=False)

    # School type choices
    class SchoolType(models.TextChoices):
        PRIMARY = 'PRIMARY', _('Primary')
        SECONDARY = 'SECONDARY', _('Secondary')
        HYBRID = 'HYBRID', _('Hybrid')
        TERTIARY = 'TERTIARY', _('Tertiary')
        
    school_type = models.CharField(_('school type'), max_length=50, choices=SchoolType.choices, default=SchoolType.PRIMARY)
    
    # Province and district choices
    class Province(models.TextChoices):
        GAUTENG = 'GAUTENG', _('Gauteng')
        # Add more provinces as needed
    
    province = models.CharField(_('province'), max_length=100, choices=Province.choices, default=Province.GAUTENG)
    
    class SchoolDistrict(models.TextChoices):
        GAUTENG_EAST = 'GAUTENG EAST', _('Gauteng East')
        GAUTENG_NORTH = 'GAUTENG NORTH', _('Gauteng North')
        # Add more districts as needed
    
    school_district = models.CharField(_('school district'), max_length=100, choices=SchoolDistrict.choices, default="")

    # Unique school ID
    school_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)   
    
    # Additional school details
    grading_system = models.TextField(blank=True, null=True)  
    library_details = models.TextField(blank=True, null=True)  
    laboratory_details = models.TextField(blank=True, null=True)  
    sports_facilities = models.TextField(blank=True, null=True)  
    operating_hours = models.CharField(max_length=100, blank=True, null=True)
    location = models.CharField(_('school location'), max_length=100, blank=True, null=True)
    
    # Additional attributes
    website = models.URLField(max_length=200, blank=True, null=True)
    logo = models.ImageField(upload_to='school_logos/', blank=True, null=True)
    established_date = models.DateField(blank=True, null=True)
    accreditation = models.CharField(max_length=100, blank=True, null=True)
    curriculum_details = models.TextField(blank=True, null=True)  
    school_motto = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        verbose_name = _('school')
        verbose_name_plural = _('schools')

    def __str__(self):
        return self.name


class SchoolCalendar(models.Model):
    """
    Model to represent the school calendar for a specific academic year and term.

    Attributes:
        school (ForeignKey): The school to which this calendar belongs.
        academic_year (CharField): The academic year (e.g., '2024-2025').
        term (IntegerField): The term number within the academic year.
        start_date (DateField): The start date of the term.
        end_date (DateField): The end date of the term.
        total_school_days (IntegerField): The total number of school days in this term.
        school_calendar_id (UUIDField): A unique identifier for the school calendar.
    """

    # Academic year and term
    academic_year = models.CharField(max_length=9)  # Format: '2024-2025'
    term = models.IntegerField()

    # Term start and end dates
    start_date = models.DateField()
    end_date = models.DateField()

    # Calculated or provided total school days
    total_school_days = models.IntegerField(blank=True, null=True)

    # Link to the school
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='calendars')
    
    # Unique calendar ID
    school_calendar_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)

    class Meta:
        verbose_name = _('School Calendar')
        verbose_name_plural = _('School Calendars')
        unique_together = ['school', 'academic_year', 'term']

    def __str__(self):
        return f"{self.school.name} - {self.academic_year} Term {self.term}"

    def calculate_total_school_days(self):
        """
        Calculate the total number of school days for the term.

        This method calculates the total school days between the start_date and end_date,
        excluding weekends and any holidays that are recorded in SchoolEvent.

        Returns:
            int: The total number of school days.
        """
        total_days = (self.end_date - self.start_date).days + 1

        # Filter out weekends (assuming Saturday and Sunday are weekends)
        school_days = sum(1 for day in range(total_days) if (self.start_date + timedelta(days=day)).weekday() < 5)

        # Subtract any holidays or non-school days recorded in SchoolEvent
        holidays = SchoolEvent.objects.filter(
            school=self.school,
            calendar=self,
            event_type=SchoolEvent.EventType.HOLIDAY,
            event_date__range=[self.start_date, self.end_date]
        ).count()

        return school_days - holidays

    def clean(self):
        """
        Custom validation logic for the SchoolCalendar model.
        
        This method ensures that:
        - The start date is before the end date.
        """
        if self.start_date > self.end_date:
            raise ValidationError(_('Start date cannot be after the end date.'))

    def save(self, *args, **kwargs):
        """
        Override the save method to calculate total school days if not provided.
        """
        self.clean()  # Validate the dates
        if not self.total_school_days:
            self.total_school_days = self.calculate_total_school_days()

        super().save(*args, **kwargs)


class SchoolEvent(models.Model):
    """
    Model to represent important events in the school calendar.

    Attributes:
        school (ForeignKey): The school to which this event belongs.
        calendar (ForeignKey): The school calendar to which this event is linked.
        event_name (CharField): The name of the event (e.g., 'Exams Start', 'School Holiday').
        event_date (DateField): The date on which the event occurs.
        event_type (CharField): The type of event (e.g., 'EXAM', 'HOLIDAY', 'OPENING', 'CLOSING').
        description (TextField): A description of the event.
        school_event_id (UUIDField): A unique identifier for the school event.
    """

    # Event details
    event_name = models.CharField(max_length=100)
    event_date = models.DateField()

    # Event type choices
    class EventType(models.TextChoices):
        EXAM = 'EXAM', _('Examination')
        HOLIDAY = 'HOLIDAY', _('Holiday')
        OPENING = 'OPENING', _('Opening Day')
        CLOSING = 'CLOSING', _('Closing Day')
        OTHER = 'OTHER', _('Other')
    
    event_type = models.CharField(max_length=20, choices=EventType.choices)
    description = models.TextField(null=True, blank=True)

    # Relationships
    calendar = models.ForeignKey(SchoolCalendar, on_delete=models.CASCADE, related_name='events')
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='events')

    # Unique event ID
    school_event_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)

    class Meta:
        verbose_name = _('School Event')
        verbose_name_plural = _('School Events')

    def __str__(self):
        return f"{self.event_name} - {self.event_date}"

    def clean(self):
        """
        Custom validation logic for the SchoolEvent model.

        This method ensures that:
        - The event date is within the term dates of the linked SchoolCalendar.
        """
        if not (self.calendar.start_date <= self.event_date <= self.calendar.end_date):
            raise ValidationError(_('Event date must be within the calendar term dates.'))

    def save(self, *args, **kwargs):
        """
        Override the save method to ensure the event is valid.
        """
        self.clean()  # Validate event dates
        super().save(*args, **kwargs)
