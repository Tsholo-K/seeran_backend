# channels
from channels.db import database_sync_to_async

# serilializers
from school_announcements.serializers import AnnouncementsSerializer

# utility functions 
from accounts import utils as users_utilities


# Asynchronous database call to retrieve and return announcements for a user's school
@database_sync_to_async
def view_school_announcements(account, role):
    """
    Retrieves school announcements related to the user's account and role.

    Args:
        user (UUID or str): The account ID of the requesting user.
        role (str): The role of the user (e.g., 'ADMIN', 'TEACHER', 'STUDENT').

    Returns:
        dict: A dictionary containing serialized school announcements, or an error message in case of failure.
    """
    try:
        # Step 1: Retrieve the requesting user's account and the associated school in a single database query
        requesting_account = users_utilities.get_account_and_linked_school(account, role)

        # Step 2: Fetch announcements related to the school of the requesting user.
        # Assume that 'announcements' is a related manager, e.g., through a ForeignKey or ManyToManyField on the School model.
        announcements = requesting_account.school.announcements

        # Step 3: Serialize the fetched announcements into a structured format using a serializer.
        serialized_announcements = AnnouncementsSerializer(announcements, many=True, context={'user': account}).data

        # Step 4: Return the serialized announcements as part of the response
        return {'announcements': serialized_announcements}

    except Exception as e:
        # Catch-all exception handler for any unexpected errors during the process
        return {'error': str(e)}  # Return the error message as a response