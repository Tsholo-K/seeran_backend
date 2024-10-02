# channels
from channels.db import database_sync_to_async

# django
from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _

# models 
from accounts.models import Teacher
from assessments.models import Assessment

# utility functions 
from account_permissions import utils as permissions_utilities
from audit_logs import utils as audits_utilities


@database_sync_to_async
def delete_assessment(user, details):
    try:
        assessment = None  # Initialize assessment as None to prevent issues in error handling

        # Retrieve the user and related school in a single query using select_related
        requesting_account = Teacher.objects.select_related('school').get(account_id=user)

        # Check if the user has permission to create an assessment
        if not permissions_utilities.has_permission(requesting_account, 'DELETE', 'ASSESSMENT'):
            response = f'could not proccess your request, you do not have the necessary permissions to delete assessments.'
            audits_utilities.log_audit(actor=requesting_account, action='DELETE', target_model='ASSESSMENT', outcome='DENIED', response=response, school=requesting_account.school)

            return {'error': response}

        assessment = Assessment.objects.select_related('assessor').get(assessment_id=details.get('assessment'), school=requesting_account.school)

        # Ensure only authorized users can delete
        if assessment.assessor != requesting_account:
            response = f'could not proccess your request, you do not have the necessary permissions to delete assessments that are not assessed by you.'
            audits_utilities.log_audit(actor=requesting_account, action='DELETE', target_model='ASSESSMENT', outcome='DENIED', response=response, school=requesting_account.school)

            return {'error': response}

        with transaction.atomic():
            response = f"assessment with assessment ID {assessment.assessment_id} has been successfully deleted, along with it's associated data"
            audits_utilities.log_audit(actor=requesting_account, action='DELETE', target_model='ASSESSMENT', target_object_id=str(assessment.assessment_id), outcome='DELETED', response=response, school=requesting_account.school,)

        return {"message": response}
                   
    except Teacher.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'a teacher account with the provided credentials does not exist, please check your account details and try again'}

    except ValidationError as e:
        error_message = e.messages[0].lower() if isinstance(e.messages, list) and e.messages else str(e).lower()
        audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='ACCOUNT', target_object_id=str(assessment.assessment_id) if assessment else 'N/A', outcome='ERROR', response=error_message, school=requesting_account.school)

        return {"error": error_message}

    except Exception as e:
        error_message = str(e)
        audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='ACCOUNT', target_object_id=str(assessment.assessment_id) if assessment else 'N/A', outcome='ERROR', response=error_message, school=requesting_account.school)

        return {'error': error_message}
