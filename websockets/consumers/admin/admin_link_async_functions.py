# channels
from channels.db import database_sync_to_async

# django
from django.db import transaction
from django.core.exceptions import ValidationError

# models 
from accounts.models import Student, Parent

# serilializers
from accounts.serializers.parents.serializers import ParentAccountCreationSerializer

# utility functions 
from accounts import utils as accounts_utilities
from account_permissions import utils as permissions_utilities
from audit_logs import utils as audits_utilities


@database_sync_to_async
def link_parent(account, role, details):
    try:    
        student = None  # Initialize student as None to prevent issues in error handling
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = accounts_utilities.get_account_and_linked_school(account, role)

        # Check if the user has permission to link acounts
        if role != 'PRINCIPAL' and not permissions_utilities.has_permission(requesting_account, 'LINK', 'ACCOUNT'):
            response = f'could not proccess your request, you do not have the necessary permissions to link parents to student accounts'
            audits_utilities.log_audit(actor=requesting_account, action='LINK', target_model='ACCOUNT', outcome='DENIED', server_response=response, school=requesting_account.school)
            return {'error': response}

        student = requesting_account.school.students.prefetch_related('parents').get(account_id=details.get('student'))

        # Check if the child already has two or more parents linked
        student_parent_count = student.parents.count()
        if student_parent_count >= 2:
            response = f"the provided student account has reached the maximum number of linked parents. please unlink one of the existing parents to link a new one"
            audits_utilities.log_audit(actor=requesting_account, action='LINK', target_model='ACCOUNT', outcome='DENIED', server_response=response, school=requesting_account.school)
            return {'error': response}
        
        # Check if an account with the provided email already exists
        existing_parent = Parent.objects.filter(email_address=details.get('email_address')).first()
        if existing_parent:
            with transaction.atomic():
                existing_parent.children.add(student)

                response = f'A parent account with the provided credentials has already been created, the two accounts have been linked. If this is a mistake, unlink the parent from the students account and review the parents information.'
                audits_utilities.log_audit(actor=requesting_account, action='LINK', target_model='ACCOUNT', target_object_id=str(student.account_id) if student else 'N/A', outcome='LINKED', server_response=response, school=requesting_account.school,)
            
            return {'message' : response}

        details['role'] = 'PARENT'
        
        serializer = ParentAccountCreationSerializer(data=details)
        if serializer.is_valid():
            with transaction.atomic():
                parent = Parent.objects.create(**serializer.validated_data)
                parent.children.add(student)

                response = f'parent account successfully created and linked to student. the parent can now sign-in and activate their account'
                audits_utilities.log_audit(actor=requesting_account, action='LINK', target_model='ACCOUNT', target_object_id=str(student.account_id) if student else 'N/A', outcome='LINKED', server_response=response, school=requesting_account.school,)

            return {'user' : parent}
            
        # Return serializer errors if the data is not valid, format it as a string
        error_response = '; '.join([f"{key}: {', '.join(value)}" for key, value in serializer.errors.items()])
        audits_utilities.log_audit(actor=requesting_account, action='LINK', target_model='ACCOUNT', target_object_id=str(student.account_id) if student else 'N/A', outcome='ERROR', server_response=f'Validation failed: {error_response}', school=requesting_account.school)

        return {"error": error_response}
                                      
    except Student.DoesNotExist:
        # Handle the case where the requested student account does not exist.
        return {'error': 'A student account with the provided credentials does not exist, please check the account details and try again'}

    except ValidationError as e:
        error_message = e.messages[0].lower() if isinstance(e.messages, list) and e.messages else str(e).lower()
        audits_utilities.log_audit(actor=requesting_account, action='LINK', target_model='ACCOUNT', target_object_id=str(student.account_id) if student else 'N/A', outcome='ERROR', server_response=error_message, school=requesting_account.school)

        return {"error": error_message}

    except Exception as e:
        error_message = str(e)
        audits_utilities.log_audit(actor=requesting_account, action='LINK', target_model='ACCOUNT', target_object_id=str(student.account_id) if student else 'N/A', outcome='ERROR', server_response=error_message, school=requesting_account.school)

        return {'error': error_message}


