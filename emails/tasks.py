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
        emails_logger.info(f"Starting email fetch task (Task ID: {self.request.id})")
        emails_fetched = 0

        # Initialize the Google Cloud Storage client and get the bucket
        storage_client = storage.Client()
        bucket = storage_client.get_bucket(config('GS_EMAIL_BUCKET_NAME'))
        batch_size = config('EMAIL_PROCESSING_BATCH_SIZE', default=5, cast=int)

        # List blobs (emails) from the bucket with a specific prefix
        blobs = bucket.list_blobs(max_results=batch_size)
        emails_fetched += emails_utilities.process_blobs(blobs)  # Counter to track how many emails have been processed

        # Check if there are more emails using the pagination token
        while blobs.next_page_token:
            blobs = bucket.list_blobs(max_results=batch_size, page_token=blobs.next_page_token)
            emails_fetched += emails_utilities.process_blobs(blobs)

        emails_logger.info(f"{emails_fetched} emails fetched and processed successfully.")
        return {
            "status": "success",
            "emails_fetched": emails_fetched,
            "task_id": self.request.id,
        }

    except Exception as e:
        current_retries = self.request.retries
        emails_logger.error(f"Error in fetch_emails_from_gcs task (retry {current_retries}): {str(e)}")

        raise self.retry(exc=e)

