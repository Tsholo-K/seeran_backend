# channels
from channels.db import database_sync_to_async

# django
from django.db import transaction
from django.core.exceptions import ValidationError

# serilializers
from schools.serializers import UpdateSchoolAccountSerializer, SchoolDetailsSerializer

# utility functions 
from accounts import utils as accounts_utilities
from account_permissions import utils as permissions_utilities
from audit_logs import utils as audits_utilities


@database_sync_to_async
def assign_permission_group_subscribers(user, role, details):
    try:
        school = None  # Initialize requested_account as None to prevent issues in error handling
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = accounts_utilities.get_account_and_linked_school(user, role)
        
        school = requesting_account.school

        # Check if the user has permission to update classrooms
        if role != 'PRINCIPAL' and not permissions_utilities.has_permission(requesting_account, 'UPDATE', 'ACCOUNT'):
            response = f'could not proccess your request, you do not have the necessary permissions to update account details.'
            audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='ACCOUNT', outcome='DENIED', response=response, school=school)

            return {'error': response}

        # Initialize the serializer with the existing school instance and incoming data
        serializer = UpdateSchoolAccountSerializer(instance=school, data=details)
        # Validate the incoming data
        if serializer.is_valid():
            # Use an atomic transaction to ensure the database is updated safely
            with transaction.atomic():
                serializer.save()
                    
                response = f"school account details have been successfully updated"
                audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='ACCOUNT', target_object_id=str(school.school_id) if school else 'N/A', outcome='UPDATED', response=response, school=requesting_account.school,)

            # Serialize the grade
            serialized_school = SchoolDetailsSerializer(school).data

            return {'school': serialized_school, "message": response}
            
        # Return serializer errors if the data is not valid, format it as a string
        error_response = '; '.join([f"{key}: {', '.join(value)}" for key, value in serializer.errors.items()])
        audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='ACCOUNT', target_object_id=str(school.school_id) if school else 'N/A', outcome='ERROR', response=f'Validation failed: {error_response}', school=school)

        return {"error": error_response}

    except ValidationError as e:
        error_message = e.messages[0].lower() if isinstance(e.messages, list) and e.messages else str(e).lower()
        audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='ACCOUNT', target_object_id=str(school.school_id) if school else 'N/A', outcome='ERROR', response=error_message, school=school)

        return {"error": error_message}

    except Exception as e:
        error_message = str(e)
        audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='ACCOUNT', target_object_id=str(school.school_id) if school else 'N/A', outcome='ERROR', response=error_message, school=school)

        return {'error': error_message}



