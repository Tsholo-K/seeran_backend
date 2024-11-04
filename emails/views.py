# django
from django.db import transaction
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
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


@csrf_exempt
def parse_email(request):
    """
    Endpoint to receive and parse incoming emails from Mailgun.
    Verifies request authenticity using Mailgun signature, and 
    categorizes emails based on recipient subdomain.

    All database operations are wrapped in a transaction to ensure data integrity.

    Expected POST data:
        'recipient': 'support@yourdomain.com',
        'sender': 'user@example.com',
        'subject': 'Help with my account',
        'body-plain': 'Email content',
        'Message-Id': '<unique_message_id@yourdomain.com>',
        'X-Case-ID': 'case_id_from_custom_header' (optional)
    
    Returns:
        JsonResponse indicating success or error with appropriate status.
    """
    emails_logger.info("Received email parsing request.")

    if request.method != 'POST':
        emails_logger.warning("Invalid request method: only POST requests are allowed.")
        return JsonResponse({"error": "Could not process your request, only POST requests are allowed at this endpoint"}, status=405)
    
    print(request.POST)

    # Verify Mailgun signature
    timestamp = request.POST.get('timestamp')
    token = request.POST.get('token')
    signature = request.POST.get('signature')

    if not emails_utilities.verify_mailgun_signature(timestamp, token, signature):
        emails_logger.error("Invalid Mailgun signature.")
        return JsonResponse({"error": "Could not process your request, invalid signature"}, status=403)
    
    try:
        with transaction.atomic():  # Start a transaction block for data integrity
            
            # Extract email data from request
            message_id = request.POST.get('Message-Id')
            sender = request.POST.get('sender')
            recipient = request.POST.get('recipient')
            subject = request.POST.get('subject', 'No Subject')
            body = request.POST.get('body-plain', '')
            received_at = timezone.now()
            case_id = request.POST.get('X-Case-ID')  # Custom header from Mailgun, if exists

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
