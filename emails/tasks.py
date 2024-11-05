# python
import requests

# celery
from celery import shared_task

# decode
from decouple import config

# utllity function
from emails import utils as emails_utilities

# logging
import logging

# Get loggers
emails_logger = logging.getLogger('emails_logger')
email_cases_logger = logging.getLogger('email_cases_logger')


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def fetch_and_process_emails(*args, **kwargs): # accept any arguments Celery might send, even if you’re not expecting any
    # Fetch emails from Mailgun
    response = requests.get(
        f"https://api.mailgun.net/v3/{config('MAILGUN_DOMAIN')}/messages",  
        auth=('api', config('MAILGUN_API_KEY')),
        params={"limit": 5}  # Limit to 5 emails at a time
    )

    if response.status_code == 200:
        emails = response.json().get('items', [])
        for email in emails:
            # Process each email (you can use your existing parsing logic here)
            emails_utilities.process_email(email)

        # If there are more emails, call this task again
        if len(emails) == 5:
            fetch_and_process_emails.apply_async(countdown=5)  # Delay next call by 5 seconds

        return emails_logger.info(f"Emails fetched and processed successfully.")

    else:
        # Handle error (log it, raise an exception, etc.)
        return emails_logger.info(f'Error fetching emails: {response.status_code} - {response.text}')

