# python
import httpx

# decode
from decouple import config

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


async def send_thread_response(case, initial_email, recipient, message, agent):
    """
    Send a reply to a case through Mailgun, ensuring data integrity with atomic transaction.
    Args:
        case_id: ID of the case to which the email belongs.
        recipient: Recipient email address.
        body: Email body content.
        type: Type of email (e.g., response, update).
    """
    try:
        # Prepare Mailgun API data
        data = {
            "from": f"seeran grades <{case.type.lower()}@{config('MAILGUN_DOMAIN')}>",
            "to": recipient,
            "template": f"{case.type.lower()} response email",
            "subject": initial_email.subject,
            "v:response": message,
            "v:caseid": str(case.case_id),
            "v:status": case.status.title(),
            "v:agent": agent,
            "h:In-Reply-To": initial_email.message_id,
            "h:References": initial_email.message_id,
        }
        print("Prepared Mailgun API data")

        # Send the email
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"https://api.eu.mailgun.net/v3/{config('MAILGUN_DOMAIN')}/messages",
                auth=("api", config('MAILGUN_API_KEY')),
                data=data
            )

        if response.status_code == 200:
            print("Email sent")
            # Extract Message-ID from the response body
            response_data = response.json()
            message_id = response_data.get("id")  # This is the Message-ID
            return {
                "case_id": case.case_id, 
                "message_id": message_id, 
                "subject": initial_email.subject, 
                "email_type": case.type, 
                "recipient": recipient,
                "message": message
            }
        
        elif response.status_code in [400, 401, 402, 403, 404]:
            return {"error": f"Account successfully created, but there was an error sending an account confirmation email to the account's email address. Please open a new bug ticket with the issue, error code {response.status_code}."}
        elif response.status_code == 429:
            return {"error": "Account successfully created, but there was an error sending an account confirmation email to the account's email address. The status code received could indicate a rate limit issue, so please wait a few minutes before creating a new account."}
        else:
            return {"error": "Account successfully created, but there was an error sending an account confirmation email to the account's email address."}

    except httpx.RequestError as e:
        print(f"Error sending thread response email via Mailgun: {str(e)}")
        return {"error": f"Mailgun request failed: {str(e)}"}

    except Exception as e:
        print(f"Unexpected error sending thread response email: {str(e)}")
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
                description="Marketing case initialized with the first email"
            )

            # Prepare headers for the initial email
            headers = {
                # Note: No need for X-Case-ID, we rely on the email thread via In-Reply-To
            }

            # Prepare Mailgun API data for sending the email
            data = {
                "from": f"seeran grades <marketing@{config('MAILGUN_DOMAIN')}>",
                "to": details.get('recipient'),
                "subject": 'The All-In-One School Management Solution for Real-Time Engagement',
                "template": "marketing email",
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

            # Assign to the user if the case has no assigned user
            if not case.assigned_to:
                # Fetch the Account object based on account_id
                account = await Founder.objects.aget(account_id=details.get('sender'))
                case.assigned_to = account  # Set the actual account object

            await case.asave(update_fields=['initial_email', 'assigned_to'])

            # Log success
            emails_logger.info(f"Case created and initial email sent for case: {case.case_id}.")
            return {"status": "Case created and initial email sent successfully", "case_id": case.case_id}

    except Exception as e:
        emails_logger.error(f"Error creating case and sending email: {str(e)}")
        return {"error": str(e)}
