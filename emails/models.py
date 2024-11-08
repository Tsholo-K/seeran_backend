# django
from django.db import models
from django.utils import timezone


class Email(models.Model):
    """
    Stores individual email messages linked to cases.
    
    Fields:
        message_id (CharField): Unique ID from the email service (e.g., Mailgun) to prevent duplicate entries.
        sender (EmailField): Email address of the sender.
        recipient (EmailField): Email address of the recipient (typically a subdomain address).
        subject (CharField): Subject of the email.
        body (TextField): Full content of the email.
        received_at (DateTimeField): Timestamp when the email was received by the server.
        is_incoming (BooleanField): Flag indicating if the email is incoming (True) or outgoing (False).
        case (ForeignKey): Reference to the associated Case, ensuring each email is part of a case.
    """
    case = models.ForeignKey('email_cases.Case', on_delete=models.CASCADE, related_name='emails')

    sender = models.EmailField()
    recipient = models.EmailField()

    read_reciept = models.BooleanField(default=False)

    subject = models.CharField(max_length=255)
    body = models.TextField()

    is_incoming = models.BooleanField(default=True)
    received_at = models.DateTimeField(default=timezone.now)

    message_id = models.CharField(max_length=255, unique=True)

    def __str__(self):
        return f"Email from {self.sender} to {self.recipient} - {self.subject}"

    class Meta:
        verbose_name = "Email"
        verbose_name_plural = "Emails"
        ordering = ['received_at']  # Orders emails chronologically within a case
