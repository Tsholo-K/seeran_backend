# python
from decouple import config
from datetime import timedelta

# google
from google.cloud import storage  # Import for Google Cloud Storage usage
from google.oauth2 import service_account

# models
from accounts.models import Principal, Admin, Teacher, Student, Parent

# queries
from seeran_backend.complex_queries import queries

# mappings
from accounts.mappings import model_mapping, serializer_mappings, attr_mappings


def upload_profile_picture_to_gcs(filename, file_data):
    """Uploads the file to Google Cloud Storage."""
    storage_client = storage.Client()
    bucket = storage_client.bucket('seeran-grades-bucket')
    blob = bucket.blob(filename)
    
    # Upload the file to GCS
    blob.upload_from_file(file_data, content_type=file_data.content_type)


def delete_profile_picture_from_gcs(filename):
    """Deletes the file from Google Cloud Storage."""
    storage_client = storage.Client()
    bucket = storage_client.bucket('seeran-grades-bucket')
    blob = bucket.blob(filename)
    
    # Delete the file from GCS
    blob.delete()


def generate_signed_url(filename, expiration=timedelta(hours=1)):
    """
    Generate a signed URL for accessing a specific object in Google Cloud Storage.

    :param filename: The name of the file in the GCS bucket.
    :param expiration: The time duration for which the URL will be valid.
    :return: A signed URL string.
    """

    # Load service account credentials from a JSON key file
    credentials = service_account.Credentials.from_service_account_file(config('GS_CREDENTIALS'))

    storage_client = storage.Client(credentials=credentials)
    bucket = storage_client.bucket('seeran-grades-bucket')
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
