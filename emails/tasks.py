# google
from google.cloud import storage

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


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def fetch_and_process_incoming_emails(self, *args, **kwargs):
    try:
        # Initialize the Google Cloud Storage client and get the bucket
        storage_client = storage.Client()
        bucket = storage_client.get_bucket(config('GS_EMAIL_BUCKET_NAME'))

        # List blobs (emails) from the bucket with a specific prefix
        blobs = bucket.list_blobs(max_results=5)
        emails_fetched = 0  # Counter to track how many emails have been processed

        # Process the blobs (emails)
        for blob in blobs:
            try:
                # Download the email data as text
                email_data = blob.download_as_text()

                # Process the email data (implement your email parsing logic)
                emails_utilities.process_email(email_data)
                emails_fetched += 1

                emails_logger.info(f"Successfully processed email: {blob.name}")

            except Exception as e:
                # Log any errors that occur while processing individual emails
                emails_logger.error(f"Error processing email {blob.name}: {str(e)}")
                continue  # Skip to the next email

        # Check if there are more emails using the pagination token
        while blobs.next_page_token:
            blobs = bucket.list_blobs(max_results=5, page_token=blobs.next_page_token)
            for blob in blobs:
                try:
                    email_data = blob.download_as_text()
                    emails_utilities.process_email(email_data)
                    emails_fetched += 1
                    emails_logger.info(f"Successfully processed email: {blob.name}")
                except Exception as e:
                    emails_logger.error(f"Error processing email {blob.name}: {str(e)}")
                    continue

        emails_logger.info(f"{emails_fetched} emails fetched and processed successfully.")
        return {"status": "success", "emails_fetched": emails_fetched}

    except Exception as e:
        # Log any errors that occur during the overall execution of the task
        emails_logger.error(f"Error in fetch_emails_from_gcs task: {str(e)}")

        # Retry the task if an exception occurs (Celery will handle the retry mechanism)
        raise self.retry(exc=e)
