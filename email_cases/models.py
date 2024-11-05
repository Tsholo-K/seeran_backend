# python
import uuid

# djnago
from django.db import models


class Case(models.Model):
    """
    Represents a conversation thread for any email sent to the application's subdomains.
    Every email, whether a support case or general inquiry, is assigned to a case.
    
    Fields:
        case_id (UUIDField): Unique identifier for the case, ensuring non-collision across cases.
        title (CharField): Brief title summarizing the case, often derived from the initial email's subject.
        created_at (DateTimeField): Timestamp when the case was first created.
        updated_at (DateTimeField): Timestamp of the last update to the case, useful for tracking recent activity.
        type (CharField): Categorizes the case based on type (e.g., support, enquiry, communication).
        status (CharField): Indicates the current state of the case (open, closed, pending).
        assigned_to (ForeignKey): Optional user assignment to the case, allowing team members to manage specific cases.
        initial_email (ForeignKey): Tracks the very first email that initiated this case, providing reference context.
        description (TextField): Optional field for any additional notes or context related to the case.
    """
    CASE_TYPES = [
        ('SUPPORT', 'Support'),       # Cases related to technical or account support
        ('ENQUIRY', 'Enquiry'),       # General inquiries or questions
        ('BILLING', 'Billing'),  # Announcements or non-interactive communication
        ('MARKETING', 'Marketing'),  # Announcements or non-interactive communication
        # Add more case types as needed
    ]
    
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)

    type = models.CharField(
        max_length=50,
        choices=CASE_TYPES,
        default='SUPPORT'
    )

    status = models.CharField(
        max_length=50,
        choices=[('OPEN', 'Open'), ('CLOSED', 'Closed'), ('PENDING', 'Pending')],
        default='OPEN'
    )

    assigned_to = models.ForeignKey(
        'accounts.Founder', 
        null=True, 
        blank=True, 
        on_delete=models.SET_NULL, 
        related_name='assigned_cases'
    )

    initial_email = models.ForeignKey(
        'emails.Email', 
        null=True, 
        blank=True, 
        on_delete=models.SET_NULL, 
        related_name='initial_case'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    case_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)

    def __str__(self):
        return f"Case {self.case_id} - {self.title} ({self.get_type_display()})"

    class Meta:
        verbose_name = "Case"
        verbose_name_plural = "Cases"
