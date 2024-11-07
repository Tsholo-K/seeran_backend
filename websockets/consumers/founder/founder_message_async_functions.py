# decode
from decouple import config

# channels
from channels.db import database_sync_to_async

# django
from django.db import transaction
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
def thread_reply(account, email_data):
    """
    Create a new case and send the initial email to the recipient.

    Args:
        recipient: The email address of the recipient.
        subject: The subject of the initial email.
        body: The body content of the initial email.
        case_type: The type of the case being created.
    """
    try:
        with transaction.atomic():
            # Fetch the case and initial email
            case = Case.objects.get(
                case_id=email_data.case_id, 
                type=email_data.email_type
            )
            print("retrieved case")

            # Save the outgoing email in the database
            Email.objects.create(
                message_id=email_data.message_id,
                sender=f"{email_data.email_type}@{config('MAILGUN_DOMAIN')}",
                recipient=email_data.recipient,
                subject=email_data.subject,
                body=email_data.message,
                received_at=timezone.now(),
                case=case,
                is_incoming=False
            )
            print("created email object")

            # Assign to the user if the case has no assigned user
            if not case.assigned_to:
                # Fetch the Account object based on account_id
                account = Founder.objects.get(account_id=account)
                case.assigned_to = account  # Set the actual account object
                case.save(update_fields=['assigned_to'])
            print("checked thread assigned_to")

        return {"message": "Thread reply has been successfully sent."}

    except Exception as e:
        emails_logger.error(f"Error creating case and sending email: {str(e)}")
        return {"error": str(e)}   


@database_sync_to_async
def marketing_thread_initialization(account, email_data):
    """
    Create a new case and send the initial email to the recipient.

    Args:
        recipient: The email address of the recipient.
        subject: The subject of the initial email.
        body: The body content of the initial email.
        case_type: The type of the case being created.
    """
    try:
        with transaction.atomic():
            case = Case.objects.create(
                title=email_data.subject,
                type=email_data.email_type.upper(),
                initial_email=None,
                description=f"Marketing email sent from our system."
            )
            emails_logger.info(f"Created new case: {case.case_id} for email from {email_data.email_type.lower()}@{config('MAILGUN_DOMAIN')}.")

            # Save the outgoing email in the database
            email_entry = Email.objects.create(
                message_id=email_data.message_id,
                sender=f"{email_data.email_type.lower()}@{config('MAILGUN_DOMAIN')}",
                recipient=email_data.recipient,
                subject=email_data.subject,
                body="We have sent a marketing email to your email address inbox we hope you can go through it and get back to us.",
                received_at=timezone.now(),
                case=case,
                is_incoming=False
            )
            print("created marketing email object")

            # Assign to the user if the case has no assigned user
            requesting_account = Founder.objects.get(account_id=account)
            case.assigned_to = requesting_account  # Set the actual account object
            print("assigned marketing case assigned_to")

            # If this is the first email in the case, set it as the initial_email
            case.initial_email = email_entry
            emails_logger.info(f"Set initial email for marketing case: {case.case_id}.")

            case.save(update_fields=['assigned_to', 'initial_email'])

        return {"message": "A marketing email has been sent to the provided email address, we hope they can go through it and get back to us."}

    except Exception as e:
        emails_logger.error(f"Error creating case and sending email: {str(e)}")
        return {"error": str(e)}   