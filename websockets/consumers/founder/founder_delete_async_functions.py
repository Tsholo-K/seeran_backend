# channels
from channels.db import database_sync_to_async

# django
from django.db import transaction

# models 
from accounts.models import Principal, Admin, Teacher, Student
from schools.models import School
from grades.models import Grade
from classrooms.models import Classroom


@database_sync_to_async
def delete_school_account(details):
    try:
        school = School.objects.get(school_id=details.get('school'))

        with transaction.atomic():
            # Perform bulk delete operations without triggering signals
            Principal.objects.filter(school=school).delete()
            Admin.objects.filter(school=school).delete()
            Teacher.objects.filter(school=school).delete()
            Student.objects.filter(school=school).delete()
            Classroom.objects.filter(school=school).delete()
            Grade.objects.filter(school=school).delete()

            # Delete the School instance
            school.delete()

        # Return a success message
        return {"message": "school account deleted successfully"}
                   
    except Principal.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'a principal account with the provided credentials does not exist, please check the account details and try again'}

    except School.DoesNotExist:
        # Handle the case where the School does not exist
        return {"error": "a school with the provided credentials does not exist"}
    
    except Exception as e:
        # Handle any unexpected errors with a general error message
        return {'error': str(e).lower()}


@database_sync_to_async
def delete_principal_account(details):
    """
    Asynchronously deletes a Principal account based on the provided details.

    This function attempts to find and delete a Principal account by its `principal_id`. 
    If the Principal account is found, it is deleted. If the Principal account cannot be 
    found, or if any other error occurs, an appropriate error message is returned.

    Args:
        details (dict): A dictionary containing the `principal_id` of the Principal account to be deleted.

    Returns:
        dict: A dictionary containing either a success message or an error message.
            - If successful, returns {"message": "principal account deleted successfully"}.
            - If the Principal does not exist, returns {"error": "principal with the provided credentials does not exist"}.
            - If an exception occurs, returns {'error': str(e).lower()} with the exception message in lowercase.
    """
    try:
        # Retrieve the Principal instance by principal_id from the provided details
        principal = Principal.objects.get(account_id=details.get('principal'))

        # Delete the Principal instance
        principal.delete()

        # Return a success message
        return {"message": "principal account deleted successfully"}
    
    except Principal.DoesNotExist:
        # Handle the case where the Principal does not exist
        return {"error": "principal with the provided credentials does not exist"}
    
    except Exception as e:
        # Handle any unexpected errors with a general error message
        return {'error': str(e).lower()}

