# python
from decouple import config
from datetime import timedelta

# google
from google.cloud import storage  # Import for Google Cloud Storage usage
from google.oauth2 import service_account
from google.cloud.exceptions import GoogleCloudError

# django
from django.core.exceptions import ValidationError

# models
from accounts.models import Principal, Admin, Teacher, Student, Parent

# queries
from seeran_backend.complex_queries import queries

# mappings
from accounts.mappings import model_mapping, serializer_mappings, attr_mappings



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


def get_account(account, role):
    try:
        Model = model_mapping.account[role]

        return Model.objects.get(account_id=account)

    except Principal.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'Could not process your request, a principal account with the provided credentials does not exist. Please review your account details and try again.'}
                   
    except Admin.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'Could not process your request, an admin account with the provided credentials does not exist. Please review your account details and try again.'}
                   
    except Teacher.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'Could not process your request, a teacher account with the provided credentials does not exist. Please review your account details and try again.'}
                   
    except Student.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'Could not process your request, a student account with the provided credentials does not exist. Please review your account details and try again.'}
               
    except Parent.DoesNotExist:
        # Handle the case where the requested parent account does not exist.
        return {'error': 'Could not process your request, a parent account with the provided credentials does not exist. Please review your account details and try again.'}

    except Exception as e:
        # Handle any unexpected errors with a general error message
        return {'error': str(e)}


def get_account_and_security_information(account, role):
    try:
        Model = model_mapping.account[role]
        Serializer = serializer_mappings.account_security_information[role]

        requesting_account = Model.objects.get(account_id=account)

        return Serializer(requesting_account).data

    except Principal.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'Could not process your request, a principal account with the provided credentials does not exist. Please review your account details and try again.'}
                   
    except Admin.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'Could not process your request, an admin account with the provided credentials does not exist. Please review your account details and try again.'}
                   
    except Teacher.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'Could not process your request, a teacher account with the provided credentials does not exist. Please review your account details and try again.'}
                   
    except Student.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'Could not process your request, a student account with the provided credentials does not exist. Please review your account details and try again.'}
               
    except Parent.DoesNotExist:
        # Handle the case where the requested parent account does not exist.
        return {'error': 'Could not process your request, a parent account with the provided credentials does not exist. Please review your account details and try again.'}

    except Exception as e:
        # Handle any unexpected errors with a general error message
        return {'error': str(e)}


def get_account_and_permission_check_attr(account, role):
    try:
        Model = model_mapping.account[role]
        select_related, prefetch_related = attr_mappings.permission_check[role]

        return queries.join_queries(Model, select_related, prefetch_related).get(account_id=account)

    except Principal.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'Could not process your request, a principal account with the provided credentials does not exist. Please review your account details and try again.'}
                   
    except Admin.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'Could not process your request, an admin account with the provided credentials does not exist. Please review your account details and try again.'}
                   
    except Teacher.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'Could not process your request, a teacher account with the provided credentials does not exist. Please review your account details and try again.'}
                   
    except Student.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'Could not process your request, a student account with the provided credentials does not exist. Please review your account details and try again.'}
               
    except Parent.DoesNotExist:
        # Handle the case where the requested parent account does not exist.
        return {'error': 'Could not process your request, a parent account with the provided credentials does not exist. Please review your account details and try again.'}

    except Exception as e:
        # Handle any unexpected errors with a general error message
        return {'error': str(e)}


def get_account_and_linked_school(account, role):
    try:
        Model = model_mapping.account[role]

        return Model.objects.select_related('school').get(account_id=account)

    except Principal.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'Could not process your request, a principal account with the provided credentials does not exist. Please review your account details and try again.'}
                   
    except Admin.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'Could not process your request, an admin account with the provided credentials does not exist. Please review your account details and try again.'}
                   
    except Teacher.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'Could not process your request, a teacher account with the provided credentials does not exist. Please review your account details and try again.'}
                   
    except Student.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'Could not process your request, a student account with the provided credentials does not exist. Please review your account details and try again.'}

    except Exception as e:
        # Handle any unexpected errors with a general error message
        return {'error': str(e)}


def get_account_and_creation_serializer(role):
    try:
        return (model_mapping.account[role], serializer_mappings.account_creation[role])

    except Principal.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'Could not process your request, a principal account with the provided credentials does not exist. Please review your account details and try again.'}
                   
    except Admin.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'Could not process your request, an admin account with the provided credentials does not exist. Please review your account details and try again.'}
                   
    except Teacher.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'Could not process your request, a teacher account with the provided credentials does not exist. Please review your account details and try again.'}
                   
    except Student.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'Could not process your request, a student account with the provided credentials does not exist. Please review your account details and try again.'}

    except Exception as e:
        # Handle any unexpected errors with a general error message
        return {'error': str(e)}
