# decode
from decouple import config

# channels
from channels.db import database_sync_to_async

# django
from django.utils import timezone

# models
from accounts.models import Founder
from emails.models import Email
from email_cases.models import Case

# logging
import logging

# Get loggers
emails_logger = logging.getLogger('emails_logger')
email_cases_logger = logging.getLogger('email_cases_logger')


@database_sync_to_async
def thread_reply(case_id, message_id, subject, email_type, recipient, sender, message):
    """
    Create a new case and send the initial email to the recipient.

    Args:
        recipient: The email address of the recipient.
        subject: The subject of the initial email.
        body: The body content of the initial email.
        case_type: The type of the case being created.
    """
    try:
        # Fetch the case and initial email
        case = Case.objects.get(case_id=case_id, type=email_type)
        print("retrieved case")

        # Save the outgoing email in the database
        Email.objects.create(
            message_id=message_id,
            sender=f"{email_type}@{config('MAILGUN_DOMAIN')}",
            recipient=recipient,
            subject=subject,
            body=message,
            received_at=timezone.now(),
            case=case,
            is_incoming=False
        )
        print("created email object")

        # Assign to the user if the case has no assigned user
        if not case.assigned_to:
            # Fetch the Account object based on account_id
            account = Founder.objects.get(account_id=sender)
            case.assigned_to = account  # Set the actual account object
            case.save(update_fields=['assigned_to'])
        print("checked thread assigned_to")

        return {"case_id": case_id, "message": message}

    except Exception as e:
        emails_logger.error(f"Error creating case and sending email: {str(e)}")
        return {"error": str(e)}   
