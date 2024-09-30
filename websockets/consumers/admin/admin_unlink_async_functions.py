# channels
from channels.db import database_sync_to_async

# django
from django.db import transaction
from django.core.exceptions import ValidationError

# models 
from accounts.models import Student

# utility functions 
from accounts import utils as users_utilities
from account_permissions import utils as permissions_utilities
from audit_logs import utils as audits_utilities


@database_sync_to_async
def unlink_parent(user, role, details):
    try:
        student = None  # Initialize student as None to prevent issues in error handling
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = users_utilities.get_account_and_linked_school(user, role)

        # Check if the user has permission to create a grade
        if role != 'PRINCIPAL' and not permissions_utilities.has_permission(requesting_account, 'UNLINK', 'ACCOUNT'):
            response = f'could not proccess your request, you do not have the necessary permissions to unlink parents from student accounts'
            audits_utilities.log_audit(actor=requesting_account, action='UNLINK', target_model='ACCOUNT', outcome='DENIED', response=response, school=requesting_account.school)

            return {'error': response}

        # Fetch the student account using the provided child ID
        student = Student.objects.prefetch_related('parents').get(account_id=details.get('student'), school=requesting_account.school)

        # Fetch the parent account using the provided parent ID
        parent = student.parents.filter(account_id=details.get('parent')).first()

        if not parent:
            response = "could not process your request, the specified student account is not a child of the provided parent account. please ensure the provided information is complete and true"
            audits_utilities.log_audit(actor=requesting_account, action='UNLINK', target_model='ACCOUNT', target_object_id=str(student.account_id), outcome='DENIED', response=response, school=requesting_account.school)

            return {'error': response}

        # Remove the child from the parent's list of children
        with transaction.atomic():
            parent.children.remove(student)
            if parent.children.len <= 0:
                parent.is_active = False
                parent.save()

            response = "the parent account has been successfully unlinked from the student. the account will no longer be associated with the student or have access to the student's data"
            audits_utilities.log_audit(actor=requesting_account, action='UNLINK', target_model='ACCOUNT', target_object_id=str(student.account_id) if student else 'N/A', outcome='UNLINKED', response=response, school=requesting_account.school,)

        return {"message": response}
                   
    except Student.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'a student account in your school with the provided credentials does not exist, please check the account details and try again'}

    except ValidationError as e:
        error_message = e.messages[0].lower() if isinstance(e.messages, list) and e.messages else str(e).lower()
        audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='GRADE', target_object_id=str(student.account_id) if student else 'N/A', outcome='ERROR', response=error_message, school=requesting_account.school)

        return {"error": error_message}

    except Exception as e:
        error_message = str(e)
        audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='GRADE', target_object_id=str(student.account_id) if student else 'N/A', outcome='ERROR', response=error_message, school=requesting_account.school)

        return {'error': error_message}



