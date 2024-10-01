# channels
from channels.db import database_sync_to_async

# models
from accounts.models import Founder

# serilializers
from accounts.serializers.founders.serializers import FounderAccountDetailsSerializer


@database_sync_to_async
def account_details(user):
    try:
        founder = Founder.objects.get(account_id=user)
        serialized_founder = FounderAccountDetailsSerializer(instance=founder).data
        
        return {'websocket_authenticated': {'account': serialized_founder}}
    
    except Exception as e:
        return {'error': str(e)}

