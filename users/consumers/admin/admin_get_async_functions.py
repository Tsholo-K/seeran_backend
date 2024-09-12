# channels
from channels.db import database_sync_to_async

# django
from django.db.models import Q

# models
from users.models import BaseUser

# serilializers
from users.serializers.general_serializers import SourceAccountSerializer

# utility functions 
from users import utils as users_utilities


@database_sync_to_async
def fetch_accounts(user, role, details):
    try:
        # Retrieve the requesting user's account and related school
        requesting_account = users_utilities.get_account_and_linked_school(user, role)

        # Base query to filter moderators by role
        search_filters = Q(role='PRINCIPAL') | Q(role='ADMIN') | Q(role='TEACHER')

        # Apply search filters if provided
        if 'search_query' in details:
            search_query = details.get('search_query')
            search_filters &= (Q(name__icontains=search_query) | Q(surname__icontains=search_query) | Q(account_id__icontains=search_query))

        # Apply cursor for pagination using the primary key (id)
        if 'cursor' in details:
            cursor = details.get('cursor')
            search_filters &= Q(id__lt=cursor)  # Filter by primary key (id)

        # Fetch the moderators with pagination
        moderators = BaseUser.objects.filter(search_filters).order_by('-id')[:20]
        serialized_moderators = SourceAccountSerializer(moderators, many=True).data

        # Determine the next cursor (based on the primary key)
        next_cursor = moderators[-1].id if len(moderators) == 20 else None

        return {'moderators': serialized_moderators, 'next_cursor': next_cursor}

    except Exception as e:
        return {'error': str(e)}

