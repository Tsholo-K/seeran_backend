# python
from decouple import config
from datetime import timedelta

# google
from google.cloud import storage  # Import for Google Cloud Storage usage
from google.oauth2 import service_account
from google.cloud.exceptions import GoogleCloudError

# django
from django.core.exceptions import ValidationError


def upload_profile_picture_to_gcs(filename, file_data):
    """
    Uploads the file to Google Cloud Storage with Cache-Control headers for client-side caching.
    
    :param filename: The name of the file in the GCS bucket.
    :param file_data: The file data (typically from a form or request).
    :return: URL of the uploaded file or None in case of failure.
    """
    try:
        # Initialize the GCS client and bucket
        storage_client = storage.Client()
        bucket = storage_client.bucket(config('GS_BUCKET_NAME'))
        blob = bucket.blob(filename)

        # Set Cache-Control header (cache for 1 day = 86400 seconds)
        blob.cache_control = 'private, max-age=86400'
        
        # Upload the file to GCS
        blob.upload_from_file(file_data, content_type=file_data.content_type)

        # Generate a signed URL for the uploaded file
        signed_url = generate_signed_url(filename)

        return signed_url

    except GoogleCloudError as e:
        raise ValidationError(f"Could not process your request, failed to upload file to GCS: {e}")


def delete_profile_picture_from_gcs(filename):
    """Deletes the file from Google Cloud Storage."""
    storage_client = storage.Client()
    bucket = storage_client.bucket(config('GS_BUCKET_NAME'))
    blob = bucket.blob(filename)
    
    # Delete the file from GCS
    blob.delete()


def generate_signed_url(filename, expiration=timedelta(hours=24)):
    """
    Generate a signed URL for accessing a specific object in Google Cloud Storage.

    :param filename: The name of the file in the GCS bucket.
    :param expiration: The time duration for which the URL will be valid.
    :return: A signed URL string.
    """

    # Load service account credentials from a JSON key file
    credentials = service_account.Credentials.from_service_account_file(config('GS_CREDENTIALS'))

    storage_client = storage.Client(credentials=credentials)
    bucket = storage_client.bucket(config('GS_BUCKET_NAME'))
    blob = bucket.blob(filename)

    # Generate a signed URL for the blob
    signed_url = blob.generate_signed_url(expiration=expiration)

    return signed_url

