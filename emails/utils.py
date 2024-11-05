# python
import hmac
import hashlib
import httpx

# decode
from decouple import config

# asgiref
from asgiref.sync import sync_to_async

# django
from django.db import transaction
from django.http import JsonResponse
from django.utils import timezone

# models
from .models import Email
from email_cases.models import Case

# utllity function
from emails import utils as emails_utilities

# logging
import logging

# Get loggers
emails_logger = logging.getLogger('emails_logger')
email_cases_logger = logging.getLogger('email_cases_logger')


def process_email(email):
    try:
        with transaction.atomic():  # Start a transaction block for data integrity
            
            # Extract email data from request
            message_id = email.get('Message-Id')
            sender = email.get('sender')
            recipient = email.get('recipient')
            subject = email.get('subject', 'No Subject')
            body = email.get('body-plain', '')
            received_at = timezone.now()
            case_id = email.get('X-Case-ID')  # Custom header from Mailgun, if exists

            # Determine case type based on recipient subdomain
            case_type = emails_utilities.determine_case_type(recipient)

            # Check if the email message ID is unique (to prevent duplicates)
            if Email.objects.filter(message_id=message_id).exists():
                emails_logger.info(f"Duplicate email ignored: {message_id} from {sender}.")
                return JsonResponse({"status": "Duplicate message ignored"}, status=200)

            # Identify or create a Case
            if case_id:
                try:
                    # Attempt to retrieve the existing case using the case_id from the custom header
                    case = Case.objects.get(case_id=case_id)
                    emails_logger.info(f"Case found: {case_id} for email from {sender}.")
                except Case.DoesNotExist:
                    # If no case is found with the provided case_id, create a new case
                    case = Case.objects.create(
                        title=subject,
                        type=case_type,
                        initial_email=None,
                        description="Auto-generated case for email without matching Case ID"
                    )
                    emails_logger.info(f"Created new case: {case.case_id} for email from {sender}.")
            else:
                # If no case_id in the header, create a new case
                case = Case.objects.create(
                    title=subject,
                    type=case_type,
                    initial_email=None,
                    description="Auto-generated case for email without Case ID"
                )
                emails_logger.info(f"Created new case: {case.case_id} for email from {sender}.")

            # Create a new Email entry in the database, linking to the identified or created case
            email = Email.objects.create(
                message_id=message_id,
                sender=sender,
                recipient=recipient,
                subject=subject,
                body=body,
                received_at=received_at,
                case=case,
                is_incoming=True
            )
            emails_logger.info(f"Email saved: {message_id} linked to case: {case.case_id}.")

            # If this is the first email in the case, set it as the initial_email
            if not case.initial_email:
                case.initial_email = email
                case.save(update_fields=['initial_email'])
                emails_logger.info(f"Set initial email for case: {case.case_id}.")

        # Commit transaction and respond with success
        emails_logger.info(f"Email processed successfully: {message_id}.")
        return JsonResponse({"status": "Email processed and saved successfully", "case_id": case.case_id}, status=201)

    except Exception as e:
        # Rollback the transaction in case of any error and log the exception
        emails_logger.error(f"Error processing email from {sender}: {str(e)}")
        return JsonResponse({"error": str(e)}, status=500)


def verify_mailgun_signature(timestamp, token, signature):
    """
    Verifies the request signature to ensure the request is from Mailgun.
    
    Args:
        timestamp (str): Unix timestamp provided by Mailgun.
        token (str): Unique token provided by Mailgun.
        signature (str): HMAC-SHA256 signature from Mailgun.

    Returns:
        bool: True if the signature is valid, False otherwise.
    """
    # Prepare the string to sign
    signed_string = f"{timestamp}{token}"

    # Compute the HMAC SHA256 hash
    computed_signature = hmac.new(
        config('MAILGUN_SIGNING_KEY').encode(),
        signed_string.encode(),
        hashlib.sha256
    ).hexdigest()
    
    # Compare the computed signature with the provided signature
    return computed_signature == signature


def determine_case_type(recipient):
    """
    Helper function to determine the case type based on the recipient email address.
    This function uses the subdomain part of the recipient email to categorize the case.

    Args:
        recipient (str): The recipient email address.

    Returns:
        str: The case type (e.g., 'support', 'enquiry', 'billing').
    """
    # Extract subdomain (everything before the '@') and use it to assign case type
    subdomain = recipient.split('@')[0].split('.')[0].upper()  # Example: 'support', 'billing', etc.

    # Define mappings for common case types
    case_type_mappings = {
        'SUPPORT': 'Support',       # Support cases
        'ENQUIRY': 'Enquiry',       # General inquiries
        'BILLING': 'Billing',       # Billing or account inquiries
        # Add additional mappings as needed
    }

    # Return the case type based on the subdomain, defaulting to 'Enquiry' if unknown
    return case_type_mappings.get(subdomain, 'SUPPORT')

