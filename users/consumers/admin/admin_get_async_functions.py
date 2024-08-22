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

# utility functions 


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

    