# python
import hashlib
import hmac

# decode
from decouple import config


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
    data = f"{timestamp}{token}"

    # Generate HMAC SHA256 signature with Mailgun API key
    hmac_digest = hmac.new(
        key=config('MAILGUN_API_KEY').encode(),
        msg=data.encode(),
        digestmod=hashlib.sha256
    ).hexdigest()

    # Compare generated signature to the signature from Mailgun
    return hmac.compare_digest(hmac_digest, signature)


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