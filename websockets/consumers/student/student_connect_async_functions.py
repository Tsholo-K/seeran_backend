# channels
from channels.db import database_sync_to_async

# models
from private_chat_room_messages.models import PrivateMessage

# utility functions 
from accounts import utils as accounts_utilities

# mappings
from accounts.mappings import serializer_mappings


@database_sync_to_async
def account_details(account, role):
    try:
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = accounts_utilities.get_account_and_linked_school(account, role)

        if requesting_account.school.none_compliant:
            return {"denied": "access denied"}
        
        # Fetch announcements relevant to the user's school
        unread_announcements_count = requesting_account.school.announcements.exclude(accounts_reached=requesting_account).count()

        # Fetch unread messages for the user
        unread_messages_count = PrivateMessage.objects.filter(read_receipt=False).exclude(author=requesting_account).count()
        
        Serializer = serializer_mappings.account_details[role]
        # Serialize the user
        serialized_account = Serializer(instance=requesting_account).data

        # Return the serialized account details along with unread counts
        return {'websocket_authenticated' : {'account': serialized_account, 'messages': unread_messages_count, 'announcements': unread_announcements_count}}
    
    except Exception as e:
        return {'error': str(e)}

