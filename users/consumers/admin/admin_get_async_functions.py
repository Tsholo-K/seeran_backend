# python 

# httpx

# channels
from channels.db import database_sync_to_async

# django

# simple jwt

# models 
from users.models import CustomUser
from grades.models import Grade

# serilializers
from grades.serializers import GradesSerializer
from schools.serializers import SchoolIDSerializer

# utility functions 



@database_sync_to_async
def fetch_school_id(user):
    """
    Asynchronously fetches the school ID associated with the provided user.

    This function retrieves the school associated with a user based on their account ID.
    It handles potential errors such as non-existent users and unexpected exceptions.

    Args:
        user (str): The account ID of the user.

    Returns:
        dict: A dictionary containing either the school ID or an error message.
    """
    try:
        # Use select_related to fetch the related school in the same query for efficiency
        account = CustomUser.objects.select_related('school').get(account_id=user)
        
        # Serialize the school object into a dictionary
        return {'school': SchoolIDSerializer(account.school).data}
        
    except CustomUser.DoesNotExist:
        # Return a clear and user-friendly error message if the user is not found
        return {'error': 'No account found with the provided account ID.'}
    
    except Exception as e:
        # Catch all other exceptions and return a descriptive error message
        return {'error': f'An unexpected error occurred: {str(e)}'}


@database_sync_to_async
def fetch_grades(user):

    try:
        account = CustomUser.objects.get(account_id=user)
        grades = Grade.objects.filter(school=account.school.pk)
        
        serializer = GradesSerializer(grades, many=True)

        return { 'grades': serializer.data }
        
    except CustomUser.DoesNotExist:
        return { 'error': 'account with the provided credentials does not exist' }
    
    except Exception as e:
        return { 'error': str(e) }


@database_sync_to_async
def fetch_grades_with_student_count(user):

    try:
        account = CustomUser.objects.get(account_id=user)
        grades = Grade.objects.filter(school=account.school)

        serializer = GradesSerializer(grades, many=True)
        student_count = CustomUser.objects.filter(role='STUDENT', school=account.school).count()

        return { 'grades': serializer.data, 'student_count' : student_count }
        
    except CustomUser.DoesNotExist:
        return { 'error': 'account with the provided credentials does not exist' }
    
    except Exception as e:
        return { 'error': str(e) }

    