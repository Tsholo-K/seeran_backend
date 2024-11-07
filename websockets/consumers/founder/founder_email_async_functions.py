# python
import httpx

# decode
from decouple import config
from asgiref.sync import sync_to_async

# channels
from channels.db import database_sync_to_async

# django
from django.db import transaction
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
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


async def email_thread_reply(account, details):
    """
    Asynchronously handles sending a reply to an email thread.

    This function performs the following:
    1. Verifies the requesting user's account.
    2. Checks the provided details for required fields (thread ID, email type, message).
    3. Fetches the associated case and initial email.
    4. Verifies the case assignment, ensuring the user is authorized to respond.
    5. Sends the reply email using Mailgun.
    6. Logs the email in the database and assigns the case to the user if unassigned.

    Args:
        account (str): The account ID of the requesting user.
        details (dict): Dictionary containing 'thread', 'type', and 'message'.

    Returns:
        dict: Success message or error details.
    """
    try:
        emails_logger.info("Starting email_thread_reply execution.")

        # Step 1: Fetch the requesting user account and verify permissions.
        emails_logger.debug("Fetching requesting account.")
        requesting_account = await sync_to_async(Founder.objects.get)(account_id=account)
        emails_logger.info(f"Found requesting account: {requesting_account}")

        # Step 2: Ensure required details are provided.
        if not {'thread', 'type', 'message'}.issubset(details):
            error_message = "Invalid request. Missing required details: 'thread', 'type', or 'message'."
            emails_logger.error(error_message)
            return {'error': error_message}
        emails_logger.info("Validated incoming data.")

        # Step 3: Fetch the case and related initial email.
        emails_logger.debug("Fetching case and initial email.")
        case = await sync_to_async(Case.objects.select_related('initial_email', 'assigned_to').get)(
            case_id=details.get('thread'), 
            type=details.get('type').upper()
        )
        initial_email = case.initial_email  # The initial email is preloaded with select_related
        emails_logger.info(f"Fetched case with ID: {case.case_id}.")

        # Step 4: Validate the initial email and case assignment.
        if not initial_email:
            error_message = "This thread lacks an initial email, so it cannot be replied to."
            emails_logger.error(error_message)
            return {"error": error_message}

        if case.assigned_to and str(case.assigned_to.account_id) != account:
            error_message = "Unauthorized action. This thread is assigned to another user."
            emails_logger.error(error_message)
            return {"error": error_message}
        emails_logger.info("Validated initial email and case assignment.")

        # Step 5: Determine recipient and prepare the email data for sending.
        recipient = initial_email.sender if initial_email.is_incoming else initial_email.recipient
        message = details.get('message')
        agent_name = f"{requesting_account.surname} {requesting_account.name}".title()
        email_data = {
            "from": f"seeran grades <{case.type.lower()}@{config('MAILGUN_DOMAIN')}>",
            "to": recipient,
            "template": f"{case.type.lower()} response email",
            "subject": initial_email.subject,
            "v:response": message,
            "v:caseid": str(case.case_id),
            "v:status": case.status.title(),
            "v:agent": agent_name,
            "h:In-Reply-To": initial_email.message_id,
            "h:References": initial_email.message_id,
        }
        emails_logger.info(f"Prepared email data for recipient: {recipient}")

        # Step 6: Send the email via Mailgun.
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"https://api.eu.mailgun.net/v3/{config('MAILGUN_DOMAIN')}/messages",
                auth=("api", config('MAILGUN_API_KEY')),
                data=email_data
            )

        # Step 7: Handle Mailgun response and log the email if successful.
        if response.status_code == 200:
            response_data = response.json()
            message_id = response_data.get("id")
            emails_logger.info(f"Email successfully sent. Mailgun message ID: {message_id}")

            # Step 8: Log the outgoing email in the database.
            await sync_to_async(Email.objects.create)(
                message_id=message_id,
                sender=f"{case.type.lower()}@{config('MAILGUN_DOMAIN')}",
                recipient=recipient,
                subject=initial_email.subject,
                body=message,
                received_at=timezone.now(),
                case=case,
                is_incoming=False
            )
            emails_logger.info("Outgoing email logged in the database.")

            # Step 9: Assign the case to the requesting user if no user is assigned.
            if not case.assigned_to:
                case.assigned_to = requesting_account
                await sync_to_async(case.save)(update_fields=['assigned_to'])
                emails_logger.info(f"Case assigned to user: {requesting_account}")

            return {"message": message}

        # Handle common error statuses from Mailgun.
        elif response.status_code in [400, 401, 402, 403, 404]:
            error_message = f"Error sending email, status code {response.status_code}. Check Mailgun API keys and permissions."
            emails_logger.error(error_message)
            return {"error": error_message}
        elif response.status_code == 429:
            error_message = "Rate limit exceeded. Please try again later."
            emails_logger.error(error_message)
            return {"error": error_message}
        else:
            error_message = "An unexpected error occurred while sending the email."
            emails_logger.error(error_message)
            return {"error": error_message}

    # Catch validation errors
    except ValidationError as e:
        error_message = f"Validation error: {str(e)}"
        emails_logger.error(error_message)
        return {"error": error_message}

    # Catch any other unexpected exceptions.
    except Exception as e:
        error_message = f"Exception while trying to send thread reply email: {str(e)}"
        emails_logger.error(error_message)
        return {"error": error_message}


async def send_marketing_email(account, details):
    """
    Sends a marketing email and initializes a new case associated with it.

    This function:
    1. Validates email and details.
    2. Sends a marketing email to the specified recipient via Mailgun.
    3. Creates a new case in the database associated with the sent email.
    4. Logs the email in the system and assigns it to the requesting account.

    Args:
        account (str): The account ID of the requesting user.
        details (dict): Dictionary containing 'type' and 'recipient'.

    Returns:
        dict: Success message or error details.
    """
    # Step 1: Validate required details
    if not {'type', 'recipient'}.issubset(details):
        error_message = "Invalid request. Missing required 'type' or 'recipient'."
        emails_logger.error(error_message)
        return {"error": error_message}

    try:
        # Step 2: Validate recipient email format
        validate_email(details["recipient"])

        # Prepare Mailgun data
        email_data = {
            "from": f"seeran grades <{details['type'].lower()}@{config('MAILGUN_DOMAIN')}>",
            "to": details["recipient"],
            "template": "marketing email",
            "subject": "The All-In-One School Management Solution for Real-Time Engagement",
        }
        emails_logger.info("Prepared email data for marketing email.")

        # Step 3: Send marketing email through Mailgun
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"https://api.eu.mailgun.net/v3/{config('MAILGUN_DOMAIN')}/messages",
                auth=("api", config('MAILGUN_API_KEY')),
                data=email_data
            )

        # Step 4: Handle Mailgun response and initialize a case
        if response.status_code == 200:
            response_data = response.json()
            message_id = response_data.get("id")
            emails_logger.info(f"Marketing email successfully sent. Mailgun message ID: {message_id}")

            # Step 5: Initialize a marketing case and log the email
            return await initialize_case(account, {
                "message_id": message_id,
                "subject": email_data["subject"],
                "email_type": details["type"],
                "recipient": details["recipient"]
            })

        elif response.status_code in [400, 401, 402, 403, 404]:
            error_message = f"Error sending marketing email, status code {response.status_code}."
            emails_logger.error(error_message)
            return {"error": error_message}
        elif response.status_code == 429:
            error_message = "Rate limit exceeded. Please wait and try again later."
            emails_logger.error(error_message)
            return {"error": error_message}
        else:
            error_message = "An unexpected error occurred while sending the email."
            emails_logger.error(error_message)
            return {"error": error_message}

    except ValidationError as e:
        error_message = f"Validation error: {str(e)}"
        emails_logger.error(error_message)
        return {"error": error_message}
    except Exception as e:
        error_message = f"Exception while sending marketing email: {str(e)}"
        emails_logger.error(error_message)
        return {"error": error_message}


@database_sync_to_async
def initialize_case(account, email_data):
    """
    Initializes a new case and logs the email in the database.

    Args:
        account (str): The account ID of the requesting user.
        email_data (dict): Data related to the email, including message_id, subject, email_type, and recipient.

    Returns:
        dict: Success message or error details.
    """
    try:
        with transaction.atomic():
            # Step 1: Create a new case for the marketing email
            case = Case.objects.create(
                title=email_data["subject"],
                type=email_data["email_type"].upper(),
                initial_email=None,
                description="Marketing email sent from our system."
            )
            emails_logger.info(f"Created new case: {case.case_id} for email from {email_data['email_type'].lower()}@{config('MAILGUN_DOMAIN')}.")

            # Step 2: Log the outgoing email in the database
            email_entry = Email.objects.create(
                message_id=email_data["message_id"],
                sender=f"{email_data['email_type'].lower()}@{config('MAILGUN_DOMAIN')}",
                recipient=email_data["recipient"],
                subject=email_data["subject"],
                body="We have sent a marketing email to your email address. Please review it and get back to us.",
                received_at=timezone.now(),
                case=case,
                is_incoming=False
            )
            emails_logger.info("Logged outgoing marketing email in the database.")

            # Step 3: Assign the case to the requesting account
            requesting_account = Founder.objects.get(account_id=account)
            case.assigned_to = requesting_account
            case.initial_email = email_entry  # Set the email entry as the initial email of the case
            case.save(update_fields=['assigned_to', 'initial_email'])
            emails_logger.info(f"Case assigned to user: {requesting_account}, and initial email set for case: {case.case_id}.")

        return {"message": "A marketing email has been sent and the case has been successfully initialized."}

    except Exception as e:
        error_message = f"Error initializing marketing case: {str(e)}"
        emails_logger.error(error_message)
        return {"error": error_message}

