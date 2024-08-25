# python 

# httpx

# channels
from channels.db import database_sync_to_async

# django

# simple jwt

# models 
from users.models import Principal, Admin

# serilializers
from grades.serializers import GradesSerializer, StudentGradesSerializer
from schools.serializers import SchoolDetailsSerializer

# utility functions


@database_sync_to_async
def fetch_grades(user, role):

    try:
        # Retrieve the user and related school in a single query using select_related
        if role == 'PRINCIPAL':
            admin = Principal.objects.select_related('school').only('school').get(account_id=user)
        else:
            admin = Admin.objects.select_related('school').only('school').get(account_id=user)
            
        grades = admin.school.grades.all()

        # Serialize the grade objects into a dictionary
        serialized_grades = GradesSerializer(grades, many=True).data

        return {'grades': serialized_grades}
               
    except Principal.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'a principal account with the provided credentials does not exist, please check the account details and try again'}
                   
    except Admin.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'an admin account with the provided credentials does not exist, please check the account details and try again'}

    except Exception as e:
        # Handle any unexpected errors with a general error message
        return {'error': str(e)}


@database_sync_to_async
def fetch_student_grades(user, role):

    try:
        # Retrieve the user and related school in a single query using select_related
        if role == 'PRINCIPAL':
            admin = Principal.objects.select_related('school').only('school').get(account_id=user)
        else:
            admin = Admin.objects.select_related('school').only('school').get(account_id=user)

        grades = admin.school.grades.all()

        serialized_grades = StudentGradesSerializer(grades, many=True).data

        return {'grades': serialized_grades}
               
    except Principal.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'a principal account with the provided credentials does not exist, please check the account details and try again'}
                   
    except Admin.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'an admin account with the provided credentials does not exist, please check the account details and try again'}

    except Exception as e:
        # Handle any unexpected errors with a general error message
        return {'error': str(e)}

    