# channels
from channels.db import database_sync_to_async

# django
from django.db import transaction
from django.core.exceptions import ValidationError

# models 
from users.models import Principal
from schools.models import School
from bug_reports.models import BugReport

# serializers
from users.serializers.principals.principals_serializers import UpdatePrincipalAccountSerializer, PrincipalAccountDetailsSerializer
from schools.serializers import UpdateSchoolAccountSerializer, SchoolDetailsSerializer
from bug_reports.serializers import UpdateBugReportStatusSerializer



@database_sync_to_async
def update_school_account(details):
    try:
        school = School.objects.get(school_id=details.get('school'))

        # Initialize the serializer with the existing school instance and incoming data
        serializer = UpdateSchoolAccountSerializer(instance=school, data=details)

        # Validate the incoming data
        if serializer.is_valid():
            # Use an atomic transaction to ensure the database is updated safely
            with transaction.atomic():
                serializer.save()
                        
            # Serialize the grade
            serialized_school = SchoolDetailsSerializer(school).data

            return {'school': serialized_school, "message": "school account details have been successfully updated" }
        
        # Return serializer errors if the data is not valid, format it as a string
        return {"error": '; '.join([f"{key}: {', '.join(value)}" for key, value in serializer.errors.items()])}

    except ValidationError as e:
        # Handle validation errors separately with meaningful messages
        return {"error": e.messages[0].lower() if isinstance(e.messages, list) and e.messages else str(e).lower()}

    except Exception as e:
        # Handle any unexpected errors with a general error message
        return {'error': str(e)}


@database_sync_to_async
def update_principal_account(details):
    """
    Asynchronously updates a Principal account with the provided details.

    This function retrieves a Principal account using the `account_id` provided in the `details` dictionary.
    It then updates the account with the new information provided in the `updates` field of the `details`.
    If the update is successful, the updated Principal account is serialized and returned. 
    If any validation errors or exceptions occur, appropriate error messages are returned.

    Args:
        details (dict): A dictionary containing:
            - 'account_id' (str): The ID of the Principal account to be updated.
            - 'updates' (dict): A dictionary of the new data to update the account with.

    Returns:
        dict: A dictionary containing either the updated Principal account data or an error message.
            - If successful, returns {"user": serializer.data} with the updated Principal data.
            - If validation fails, returns {"error": serializer.errors} with the validation errors.
            - If the Principal account does not exist, returns {'error': 'account with the provided credentials does not exist'}.
            - If an exception occurs, returns {'error': str(e)} with the exception message.
    """
    try:
        # Retrieve the Principal instance by account_id from the provided details
        account = Principal.objects.get(account_id=details.get('account_id'))
        
        # Initialize the serializer with the existing instance and the updates to apply
        serializer = UpdatePrincipalAccountSerializer(instance=account, data=details.get('updates'))
        
        if serializer.is_valid():
            # Save the updates in an atomic transaction to ensure data integrity
            with transaction.atomic():
                serializer.save()
            
            # Serialize the updated account data using PrincipalIDSerializer
            serializer = PrincipalAccountDetailsSerializer(instance=account)
            return {"principal": serializer.data}
            
        # If the data is not valid, return the validation errors formatted as a string
        return {"error": '; '.join([f"{key}: {', '.join(value)}" for key, value in serializer.errors.items()])}
    
    except Principal.DoesNotExist:
        # Handle the case where the Principal account does not exist
        return {'error': 'a principal account with the provided credentials does not exist'}
    
    except Exception as e:
        # Handle any unexpected errors with a general error message
        return {'error': str(e)}
  

@database_sync_to_async
def update_bug_report(details):
    """
    Asynchronously updates the status of a BugReport with the provided details.

    This function retrieves a BugReport instance using the `bugreport_id` provided in the `details` dictionary.
    It then updates the status of the bug report with the new information provided in the `details`.
    If the update is successful, a success message is returned. 
    If any validation errors or exceptions occur, appropriate error messages are returned.

    Args:
        details (dict): A dictionary containing:
            - 'bug_report' (str): The ID of the BugReport to be updated.
            - Other relevant fields for updating the status.

    Returns:
        dict: A dictionary containing either a success message or an error message.
            - If successful, returns {"message": "bug report status successfully changed"}.
            - If validation fails, returns {"error": serializer.errors} with the validation errors.
            - If the BugReport does not exist, returns {'error': 'bug report with the provided ID does not exist'}.
            - If an exception occurs, returns {'error': str(e)} with the exception message.
    """
    try:
        # Retrieve the BugReport instance by bugreport_id from the provided details
        bug_report = BugReport.objects.get(bugreport_id=details.get('bug_report'))

        # Initialize the serializer with the existing instance and the update data
        serializer = UpdateBugReportStatusSerializer(instance=bug_report, data=details)
    
        if serializer.is_valid():
            # Save the updates
            serializer.save()

            # Return a success message
            return {"message": "bug report status successfully changed"}
    
        # If the data is not valid, return the validation errors formatted as a string
        return {"error": '; '.join([f"{key}: {', '.join(value)}" for key, value in serializer.errors.items()])}
    
    except BugReport.DoesNotExist:
        # Handle the case where the BugReport does not exist
        return {'error': 'bug report with the provided ID does not exist'}
    
    except Exception as e:
        # Handle any unexpected errors with a general error message
        return {'error': str(e)}


