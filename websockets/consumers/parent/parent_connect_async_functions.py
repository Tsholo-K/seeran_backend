# channels
from channels.db import database_sync_to_async

# models
from chat_room_messages.models import PrivateMessage

# utility functions 
from accounts import utils as accounts_utilities

# mappings
from accounts.mappings import serializer_mappings


@database_sync_to_async
def account_details(account, role):
    try:
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = accounts_utilities.get_account(account, role)

        if not requesting_account.children:
            return {"denied": "Could not process your request, your account doesnt have any children linked to it. For more information about this you can read our Parent Dashboard Documentation for why you're seeing this."}

        if not requesting_account.children.filter(school__none_compliant=False).exists():
            return {"denied": "Could not process your request, all of the children linked to your account have their accounts deactivated. For more information about this you can read our Termination Policy for why you're seeing this."}
        
        # Fetch announcements relevant to the user's school
        unread_announcements_count = requesting_account.children.filter(school__announcements__accounts_reached=requesting_account).count()

        # Fetch unread messages for the user
        unread_messages_count = PrivateMessage.objects.filter(read_receipt=False).exclude(author=requesting_account).count()
        
        Serializer = serializer_mappings.account_details[role]
        # Serialize the user
        serialized_account = Serializer(instance=requesting_account).data

        # Return the serialized account details along with unread counts
        return {'websocket_authenticated' : {'account': serialized_account, 'messages': unread_messages_count, 'announcements': unread_announcements_count}}
    
    except Exception as e:
        return {'error': str(e)}
