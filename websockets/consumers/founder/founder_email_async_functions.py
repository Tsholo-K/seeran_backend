# python
import httpx

# decode
from decouple import config

# django
from django.db import transaction
from django.utils import timezone

# models
from emails.models import Email
from email_cases.models import Case

# logging
import logging

# Get loggers
emails_logger = logging.getLogger('emails_logger')
email_cases_logger = logging.getLogger('email_cases_logger')


async def send_case_response(details):
    """
    Send a reply to a case through Mailgun, ensuring data integrity with atomic transaction.
    Args:
        case_id: ID of the case to which the email belongs.
        recipient: Recipient email address.
        body: Email body content.
        type: Type of email (e.g., response, update).
    """
    try:
        async with transaction.atomic():
            # Fetch the case and initial email
            case = await Case.objects.select_for_update().aget(case_id=details.get('case'))
            initial_email = case.initial_email

            # Determine the correct recipient based on whether the initial email is incoming
            if initial_email and initial_email.is_incoming:
                recipient = initial_email.sender
            else:
                recipient = case.recipient_email

            # Prepare headers for reply tracking
            headers = {
                "In-Reply-To": initial_email.message_id if initial_email else "",
                "References": initial_email.message_id if initial_email else "",
                "X-Case-ID": case.case_id,
            }

            # Prepare Mailgun API data
            data = {
                "from": f"seeran grades <{case.type.lower()}@{config('MAILGUN_DOMAIN')}>",
                "to": recipient,
                "subject": initial_email.subject,
                "text": details.get('body'),
                "h:In-Reply-To": headers["In-Reply-To"],
                "h:References": headers["References"],
                "h:X-Case-ID": headers["X-Case-ID"],
            }

            # Send the email
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"https://api.eu.mailgun.net/v3/{config('MAILGUN_DOMAIN')}/messages",
                    auth=("api", config('MAILGUN_API_KEY')),
                    data=data
                )

            response.raise_for_status()
            message_id = response.headers.get("Message-ID")

            # Save the outgoing email in the database
            email = await Email.objects.acreate(
                message_id=message_id,
                sender=f"{case.type.lower()}@{config('MAILGUN_DOMAIN')}",
                recipient=recipient,
                subject=initial_email.subject,
                body=details.get('body'),
                received_at=timezone.now(),
                case=case,
                is_incoming=False
            )

            emails_logger.info(f"Reply email sent and saved for case: {case.case_id}.")
            return {"status": "Reply sent successfully", "email_id": email.id}

    except Case.DoesNotExist:
        emails_logger.error(f"Case not found for ID: {case.case_id}.")
        return {"error": "Case not found"}

    except httpx.RequestError as e:
        emails_logger.error(f"Error sending email via Mailgun for case {case.case_id}: {str(e)}")
        return {"error": f"Mailgun request failed: {str(e)}"}

    except Exception as e:
        emails_logger.error(f"Unexpected error for case {case.case_id}: {str(e)}")
        return {"error": str(e)}


async def send_marketing_case_and_send_initial_email(details):
    """
    Create a new case and send the initial email to the recipient.

    Args:
        recipient: The email address of the recipient.
        subject: The subject of the initial email.
        body: The body content of the initial email.
        case_type: The type of the case being created.
    """
    try:
        # Start an atomic transaction block for data integrity
        async with transaction.atomic():
            # Create the case first
            case = await Case.objects.acreate(
                title='The Future of School Management',
                type='MARKETING',
                initial_email=None,  # Will be set after sending the email
                description="marketing case initialized with the first email"
            )

            # Prepare headers for the initial email
            headers = {
                "X-Case-ID": case.case_id,  # Custom header for tracking
            }

            # Prepare Mailgun API data for sending the email
            data = {
                "from": f"seeran grades <marketing@{config('MAILGUN_DOMAIN')}>",
                "to": details.get('recipient'),
                "subject": 'The All-In-One School Management Solution for Real-Time Engagement',
                "template": "marketing email",
                "h:X-Case-ID": headers["X-Case-ID"],
            }

            # Send the initial email using Mailgun's API
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"https://api.eu.mailgun.net/v3/{config('MAILGUN_DOMAIN')}/messages",
                    auth=("api", config('MAILGUN_API_KEY')),
                    data=data
                )

            # Raise an error if the email sending fails
            response.raise_for_status()
            message_id = response.headers.get("Message-ID")

            # Create the Email record in the database
            email = await Email.objects.acreate(
                message_id=message_id,
                sender=f"marketing@{config('MAILGUN_DOMAIN')}",
                recipient=details.get('recipient'),
                subject='The All-In-One School Management Solution for Real-Time Engagement',
                body='Marketing email sent',
                received_at=timezone.now(),
                case=case,
                is_incoming=False  # This is an outgoing email
            )

            # Update the case with the initial email reference
            case.initial_email = email
            await case.asave(update_fields=['initial_email'])

            # Log success
            emails_logger.info(f"Case created and initial email sent for case: {case.case_id}.")
            return {"status": "Case created and initial email sent successfully", "case_id": case.case_id}

    except Exception as e:
        emails_logger.error(f"Error creating case and sending email: {str(e)}")
        return {"error": str(e)}