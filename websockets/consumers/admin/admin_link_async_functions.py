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
def link_parent(user, role, details):
    try:    
        student = None  # Initialize student as None to prevent issues in error handling
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = accounts_utilities.get_account_and_linked_school(user, role)

        # Check if the user has permission to link acounts
        if role != 'PRINCIPAL' and not permissions_utilities.has_permission(requesting_account, 'LINK', 'ACCOUNT'):
            response = f'could not proccess your request, you do not have the necessary permissions to link parents to student accounts'
            audits_utilities.log_audit(actor=requesting_account, action='LINK', target_model='ACCOUNT', outcome='DENIED', response=response, school=requesting_account.school)

            return {'error': response}

        student = Student.objects.prefetch_related('parents').get(account_id=details.get('student'), school=requesting_account.school)

        # Check if the child already has two or more parents linked
        student_parent_count = student.parents.count()
        if student_parent_count >= 2:
            response = f"the provided student account has reached the maximum number of linked parents. please unlink one of the existing parents to link a new one"
            audits_utilities.log_audit(actor=requesting_account, action='LINK', target_model='ACCOUNT', outcome='DENIED', response=response, school=requesting_account.school)

            return {'error': response}
        
        # Check if an account with the provided email already exists
        existing_parent = Parent.objects.filter(email=details.get('email')).first()
        if existing_parent:
            return {'user' : existing_parent, 'notice' : 'there is already a parent account with the provide email address'}

        details['role'] = 'PARENT'
        
        serializer = ParentAccountCreationSerializer(data=details)
        if serializer.is_valid():
            with transaction.atomic():
                parent = Parent.objects.create(**serializer.validated_data)
                parent.children.add(student)

                response = f'parent account successfully created and linked to student. the parent can now sign-in and activate their account'
                audits_utilities.log_audit(actor=requesting_account, action='LINK', target_model='ACCOUNT', target_object_id=str(student.account_id) if student else 'N/A', outcome='LINKED', response=response, school=requesting_account.school,)

            return {'user' : parent}
            
        # Return serializer errors if the data is not valid, format it as a string
        error_response = '; '.join([f"{key}: {', '.join(value)}" for key, value in serializer.errors.items()])
        audits_utilities.log_audit(actor=requesting_account, action='LINK', target_model='ACCOUNT', target_object_id=str(student.account_id) if student else 'N/A', outcome='ERROR', response=f'Validation failed: {error_response}', school=requesting_account.school)

        return {"error": error_response}
                                      
    except Student.DoesNotExist:
        # Handle the case where the requested student account does not exist.
        return {'error': 'A student account with the provided credentials does not exist, please check the account details and try again'}

    except ValidationError as e:
        error_message = e.messages[0].lower() if isinstance(e.messages, list) and e.messages else str(e).lower()
        audits_utilities.log_audit(actor=requesting_account, action='LINK', target_model='ACCOUNT', target_object_id=str(student.account_id) if student else 'N/A', outcome='ERROR', response=error_message, school=requesting_account.school)

        return {"error": error_message}

    except Exception as e:
        error_message = str(e)
        audits_utilities.log_audit(actor=requesting_account, action='LINK', target_model='ACCOUNT', target_object_id=str(student.account_id) if student else 'N/A', outcome='ERROR', response=error_message, school=requesting_account.school)

        return {'error': error_message}

