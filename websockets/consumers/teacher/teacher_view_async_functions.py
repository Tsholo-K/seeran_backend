# channels
from channels.db import database_sync_to_async

# serilializers
from school_announcements.serializers import AnnouncementsSerializer
from classrooms.serializers import TeacherClassroomsSerializer

# utility functions 
from accounts import utils as accounts_utilities
from account_permissions import utils as permissions_utilities
from audit_logs import utils as audits_utilities


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
        requesting_account = accounts_utilities.get_account_and_linked_school(account, role)

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


@database_sync_to_async
def view_my_classrooms(account, role):
    try:
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = accounts_utilities.get_account(account, role)

        if not permissions_utilities.has_permission(requesting_account, 'VIEW', 'CLASSROOM'):
            response = f'could not proccess your request, you do not have the necessary permissions to view classrooms. please contact your administrator to adjust you permissions for viewing classrooms.'
            audits_utilities.log_audit(actor=requesting_account, action='VIEW', target_model='CLASSROOM', outcome='DENIED', server_response=response, school=requesting_account.school)
            return {'error': response}

        my_classrooms = requesting_account.taught_classrooms
        serialized_classrooms = TeacherClassroomsSerializer(my_classrooms, many=True).data

        return {"classrooms": serialized_classrooms}
    
    except Exception as e:
        return { 'error': str(e) }