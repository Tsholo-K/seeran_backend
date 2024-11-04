# django
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

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

    # Verify Mailgun signature
    timestamp = request.POST.get('timestamp')
    token = request.POST.get('token')
    signature = request.POST.get('signature')

    if not emails_utilities.verify_mailgun_signature(timestamp, token, signature):
        emails_logger.error("Invalid Mailgun signature.")
        return JsonResponse({"error": "Could not process your request, invalid signature"}, status=403)
    
    # Process each email (you can use your existing parsing logic here)
    return emails_utilities.process_email(request.POST)
