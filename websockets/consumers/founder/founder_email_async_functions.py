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


@database_sync_to_async
@transaction.atomic
async def email_thread_reply(account, details):
    try:
        # Verify user account
        requesting_account = Founder.objects.get(account_id=account)

        # Ensure required details are present
        if not {'thread', 'type', 'message'}.issubset(details):
            return {'error': 'Invalid request. Provide a valid thread ID, email type, and response message.'}

        # Fetch case and initial email
        case = Case.objects.get(
            case_id=details.get('thread'), 
            type=details.get('type').upper()
        )
        initial_email = case.initial_email

        # Check initial email and assignment
        if not initial_email:
            return {"error": "This thread lacks an initial email, so it cannot be replied to."}

        if case.assigned_to and str(case.assigned_to.account_id) != account:
            return {"error": "This thread is assigned to another user."}

        # Determine recipient based on initial email
        recipient = initial_email.sender if initial_email.is_incoming else initial_email.recipient

        # Prepare email data for Mailgun
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

        # Send email via Mailgun
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"https://api.eu.mailgun.net/v3/{config('MAILGUN_DOMAIN')}/messages",
                auth=("api", config('MAILGUN_API_KEY')),
                data=email_data
            )

        if response.status_code == 200:
            response_data = response.json()
            message_id = response_data.get("id")

            # Log the outgoing email in the database
            Email.objects.create(
                message_id=message_id,
                sender=f"{case.type.lower()}@{config('MAILGUN_DOMAIN')}",
                recipient=recipient,
                subject=initial_email.subject,
                body=message,
                received_at=timezone.now(),
                case=case,
                is_incoming=False
            )

            # Assign case if no user is assigned
            if not case.assigned_to:
                case.assigned_to = requesting_account
                case.save(update_fields=['assigned_to'])

            return {"message": "Thread reply successfully sent."}

        elif response.status_code in [400, 401, 402, 403, 404]:
            error = f"Account successfully created, but there was an error sending thread reply email to the email address. Please open a new bug ticket with the issue, error code {response.status_code}."
            emails_logger.error(error)
            return {"error": error}
        elif response.status_code == 429:
            error = f"Account successfully created, but there was an error sending thread reply email to the email address. The status code received could indicate a rate limit issue, so please wait a few minutes before creating a new account."
            emails_logger.error(error)
            return {"error": error}
        else:
            error = f"Account successfully created, but there was an error sending thread reply email to the email address."
            emails_logger.error(error)
            return {"error": error}

    except Founder.DoesNotExist:
        return {'error': 'Could not process your request, invalid account credentials.'}
    except ValidationError:
        error = f"There was a validation error while trying to sending thread reply email: {str(e)}"
        emails_logger.error(error)
        return {"error": str(e)}
    except Exception as e:
        error = f"There was an exception error while trying to sending thread reply email: {str(e)}"
        emails_logger.error(error)
        return {"error": str(e)}


async def send_thread_response(case_data):
    """
    Send a reply to a case through Mailgun, ensuring data integrity with atomic transaction.
    Args:
        case_id: ID of the case to which the email belongs.
        recipient: Recipient email address.
        body: Email body content.
        type: Type of email (e.g., response, update).
    """
    try:
        validate_email(case_data.recipient)

        # Prepare Mailgun API data
        data = {
            "from": f"seeran grades <{case_data.case.type.lower()}@{config('MAILGUN_DOMAIN')}>",
            "to": case_data.recipient,
            "template": f"{case_data.case.type.lower()} response email",
            "subject": case_data.initial_email.subject,
            "v:response": case_data.message,
            "v:caseid": str(case_data.case.case_id),
            "v:status": case_data.case.status.title(),
            "v:agent": case_data.agent,
            "h:In-Reply-To": case_data.initial_email.message_id,
            "h:References": case_data.initial_email.message_id,
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
                "email_data" : {
                    "message_id": message_id, 
                    "case_id": case_data.case.case_id, 
                    "subject": case_data.initial_email.subject, 
                    "email_type": case_data.case.type, 
                    "recipient": case_data.recipient,
                    "message": case_data.message
                }
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


async def send_marketing_email(details):
    """
    Create a new case and send the initial email to the recipient.

    Args:
        recipient: The email address of the recipient.
        subject: The subject of the initial email.
        body: The body content of the initial email.
        case_type: The type of the case being created.
    """
    if not (details.get("type") or details.get("recipient")):
        return {"error": "Could not process your request, invlaid data provided."}
               
    try:
        validate_email(details["recipient"])

        # Prepare Mailgun API data
        data = {
            "from": f"seeran grades <{details["type"].lower()}@{config('MAILGUN_DOMAIN')}>",
            "to": details["recipient"],
            "template": "marketing email",
            "subject": "The All-In-One School Management Solution for Real-Time Engagement",
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

            return {"email_data" : {
                "message_id": message_id, 
                "subject": "The All-In-One School Management Solution for Real-Time Engagement", 
                "email_type": details["type"], 
                "recipient": details["recipient"], 
            }}
        
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
