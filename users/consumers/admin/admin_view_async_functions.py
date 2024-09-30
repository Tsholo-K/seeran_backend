# channels
from channels.db import database_sync_to_async

# serilializers
from schools.serializers import SchoolDetailsSerializer
from announcements.serializers import AnnouncementsSerializer

# utility functions 
from users import utils as users_utilities
    
    
# Asynchronous database call to retrieve and return school details based on the requesting user's account and role
@database_sync_to_async
def view_school_details(user, role):
    """
    Retrieves the school details for a user based on their account and role within the system.

    Args:
        user (UUID or str): The account ID of the requesting user.
        role (str): The role of the user (e.g., 'ADMIN', 'TEACHER', 'STUDENT').

    Returns:
        dict: A dictionary containing serialized school details, or an error message in case of failure.
    """
    try:
        # Step 1: Retrieve the requesting user's account and the associated school in a single database query
        # This uses a utility function (get_account_and_linked_school) to fetch the user's account and linked school.
        requesting_account = users_utilities.get_account_and_linked_school(user, role)

        # Step 2: Serialize the school object into a structured dictionary format for easy consumption by the API or frontend
        serialized_school = SchoolDetailsSerializer(requesting_account.school).data
        
        # Step 3: Return the serialized school details as part of the response
        return {"school": serialized_school}

    except Exception as e:
        # Catch-all exception handler for any unexpected errors during the process
        return {'error': str(e)}  # Return the error message as a response


# Asynchronous database call to retrieve and return announcements for a user's school
@database_sync_to_async
def view_school_announcements(user, role):
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
        requesting_account = users_utilities.get_account_and_linked_school(user, role)

        # Step 2: Fetch announcements related to the school of the requesting user.
        # Assume that 'announcements' is a related manager, e.g., through a ForeignKey or ManyToManyField on the School model.
        announcements = requesting_account.school.announcements

        # Step 3: Serialize the fetched announcements into a structured format using a serializer.
        serialized_announcements = AnnouncementsSerializer(announcements, many=True, context={'user': user}).data

        # Step 4: Return the serialized announcements as part of the response
        return {'announcements': serialized_announcements}

    except Exception as e:
        # Catch-all exception handler for any unexpected errors during the process
        return {'error': str(e)}  # Return the error message as a response