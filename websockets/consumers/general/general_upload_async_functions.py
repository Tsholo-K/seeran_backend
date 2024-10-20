# python
import uuid
import urllib

# channels
from channels.db import database_sync_to_async

# django
from django.utils.translation import gettext as _
from django.db import transaction
from django.core.cache import cache

# models 
from accounts.models import BaseAccount

# serializers
from accounts.serializers.general_serializers import ProfilePictureSerializer

# utility functions 
from accounts import utils as accounts_utilities

    
@database_sync_to_async
def upload_profile_picture(account, details):
    try:
        requesting_account = BaseAccount.objects.get(account_id=account)

        # Create a ProfilePictureSerializer instance
        serializer = ProfilePictureSerializer(data={'profile_picture': details})
        if serializer.is_valid():
            with transaction.atomic():
                serializer.save()

                # Delete the old profile picture
                requesting_account.profile_picture.delete()

                # Generate a new filename with UUID
                ext = "jpg"  # Assuming the file extension is jpg for simplicity; adjust as needed
                filename = f'{uuid.uuid4()}.{ext}'
                filename = urllib.parse.quote(filename)

                # Save the new profile picture to the Google Cloud Storage
                accounts_utilities.save_profile_picture_to_gcs(requesting_account, filename, details)

                # Clear the cache if it exists
                if cache.get(requesting_account.account_id + 'profile_picture'):
                    cache.delete(requesting_account.account_id + 'profile_picture')
            
            # Send a success response to the client
            return {"message": "Profile picture updated successfully."}

        error_response = '; '.join([f"{key}: {', '.join(value)}" for key, value in serializer.errors.items()])
        return {"error": error_response}
    
    except BaseAccount.DoesNotExist:
        return {"error": "Could not process your request, no account with the provided credentials exists."}
    except Exception as e:
        return {"message": str(e)}
