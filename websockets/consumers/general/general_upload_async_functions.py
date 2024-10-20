# channels
from channels.db import database_sync_to_async

# django
from django.utils.translation import gettext as _
from django.db import transaction

# models 
from accounts.models import BaseAccount

# utility functions 
from accounts import utils as accounts_utilities

    
@database_sync_to_async
def remove_profile_picture(account):
    try:
        requesting_account = BaseAccount.objects.get(account_id=account)

        if requesting_account.profile_picture:
            with transaction.atomic():
                # Delete the old profile picture from GCS if it exists
                if requesting_account.profile_picture:
                    accounts_utilities.delete_profile_picture_from_gcs(requesting_account.profile_picture.name)
        else:
            return {"error": "Could not process your request, your account does not have a custom profile picture."}

    except BaseAccount.DoesNotExist:
        return {"error": "Could not process your request, no account with the provided credentials exists."}
    except Exception as e:
        return {"message": str(e)}
