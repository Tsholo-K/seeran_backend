# python 

# httpx

# channels
from channels.db import database_sync_to_async

# django
from django.db.models import Q

# simple jwt

# models 
from users.models import CustomUser
from timetables.models import GroupSchedule
from grades.models import Grade, Subject
from schools.models import Term

# serilializers
from users.serializers import AccountSerializer
from grades.serializers import GradeSerializer, SubjectDetailSerializer, ClassesSerializer
from schools.serializers import TermSerializer

# utility functions 


@database_sync_to_async
def search_term(user, details):
    try:
        # Fetch the school directly using the account_id for efficiency
        account = CustomUser.objects.select_related('school').only('school').get(account_id=user)
        term = CustomUser.objects.select_related('school').only('school').get(term_id=details.get('term'))

        # Check if the user has permission to view the term
        if account.school != term.school:
            return {"error": 'permission denied. you can only access details about terms from your own school'}
        
        # Serialize the school terms
        serialized_term = TermSerializer(term).data
        
        # Return the serialized terms in a dictionary
        return {'term': serialized_term}
    
    except CustomUser.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'An account with the provided credentials does not exist. Please check the account details and try again.'}
    
    except Exception as e:
        # Handle any unexpected errors with a general error message
        return {'error': f'An unexpected error occurred: {str(e)}'}
    

@database_sync_to_async
def search_accounts(user, details):

    try:
        if details.get('role') not in ['ADMIN', 'TEACHER']:
            return { "error" : 'invalid role request' }
        
        account = CustomUser.objects.get(account_id=user)

        if details.get('role') == 'ADMIN':
            accounts = CustomUser.objects.filter( Q(role='ADMIN') | Q(role='PRINCIPAL'), school=account.school).exclude(account_id=user)
    
        if details.get('role') == 'TEACHER':
            accounts = CustomUser.objects.filter(role=details.get('role'), school=account.school)

        serializer = AccountSerializer(accounts, many=True)
        return { "users" : serializer.data }
    
    except CustomUser.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'An account with the provided credentials does not exist, please check the account details and try again'}

    except Exception as e:
        # Handle any unexpected errors with a general error message
        return {'error': str(e)}


@database_sync_to_async
def search_subscribed_students(user, details):
    """
    Searches and retrieves students subscribed to a specific group schedule.

    Args:
        user (str): The account ID of the user making the request.
        details (dict): A dictionary containing the group_schedule_id to identify the group schedule.

    Returns:
        dict: A dictionary containing the list of subscribed students or an error message.

    Raises:
        CustomUser.DoesNotExist: If the user with the provided account ID does not exist.
        GroupSchedule.DoesNotExist: If the group schedule with the provided ID does not exist.
        Exception: For any other unexpected errors.
    """
    try:
        # Retrieve the account making the request
        account = CustomUser.objects.get(account_id=user)
        
        # Retrieve the group schedule
        group_schedule = GroupSchedule.objects.get(group_schedule_id=details.get('group_schedule_id'))

        # Check if the user has permission to view the group schedule
        if account.school != group_schedule.grade.school:
            return {"error": 'permission denied. you can only view details about group schedules from your own school.'}

        # Get all students subscribed to this group schedule
        students = group_schedule.students.all()

        # Serialize the students
        serializer = AccountSerializer(students, many=True)

        return {"students": serializer.data}
    
    except CustomUser.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'An account with the provided credentials does not exist, please check the account details and try again'}
                
    except GroupSchedule.DoesNotExist:
        return {'error': 'a group schedule with the provided credentials does not exist. Please check the group schedule details and try again.'}

    except Exception as e:
        # Handle any unexpected errors with a general error message
        return {'error': str(e)}


@database_sync_to_async
def search_grade(user, details):

    try:
        account = CustomUser.objects.get(account_id=user)
        
        grade  = Grade.objects.get(school=account.school, grade_id=details.get('grade_id'))
        serializer = GradeSerializer(instance=grade)

        return { 'grade' : serializer.data}
    
    except Grade.DoesNotExist:
        return { 'error': 'grade with the provided credentials does not exist' }
    
    except CustomUser.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'An account with the provided credentials does not exist, please check the account details and try again'}

    except Exception as e:
        # Handle any unexpected errors with a general error message
        return {'error': str(e)}


@database_sync_to_async
def search_subject(user, details):
    """
    Asynchronous function to search for and retrieve subject details.

    This function checks if the requesting user is authorized to access or update 
    the subject information. If the subject is found and the user has the correct 
    permissions, the function returns the serialized subject data.

    Args:
        user (str): The account_id of the user making the request.
        details (dict): A dictionary containing the details of the subject being searched, specifically the 'subject_id'.

    Returns:
        dict: A dictionary containing the serialized subject data if found and accessible, 
            or an error message if the subject or user account is not found, or if there is 
            a permission issue.
    """
    try:
        # Retrieve user account
        account = CustomUser.objects.get(account_id=user)

        # Retrieve the subject and its related grade
        subject = Subject.objects.select_related('grade').get(subject_id=details.get('subject_id'))

        # Verify that the subject belongs to the same school as the user
        if account.school != subject.grade.school:
            return {"error": "permission denied. you can only access or update details about subjects from your own school."}

        # Serialize the subject data
        serializer = SubjectDetailSerializer(subject)
        return {"subject": serializer.data}
    
    except CustomUser.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'An account with the provided credentials does not exist, please check the account details and try again'}
    
    except Subject.DoesNotExist:
        # Handle case where the subject does not exist
        return {'error': 'a subject with the provided credentials does not exist.'}

    except Exception as e:
        # Handle any unexpected errors with a general error message
        return {'error': str(e)}


@database_sync_to_async
def search_grade_register_classes(user, details):

    try:
        account = CustomUser.objects.get(account_id=user)
        grade  = Grade.objects.get(grade_id=details.get('grade_id'), school=account.school)

        classes = grade.grade_classes.filter(register_class=True)

        serializer = ClassesSerializer(classes, many=True)

        return {"classes": serializer.data}
    
    except CustomUser.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'An account with the provided credentials does not exist, please check the account details and try again'}
           
    except Grade.DoesNotExist:
        return { 'error': 'grade with the provided credentials does not exist' }

    except Exception as e:
        # Handle any unexpected errors with a general error message
        return {'error': str(e)}
    

@database_sync_to_async
def search_students(user, details):

    try:
        account = CustomUser.objects.get(account_id=user)
        students = Grade.objects.get(grade_id=details.get('grade_id'), school=account.school.pk).students.all()

        serializer = AccountSerializer(students, many=True)

        return {"students": serializer.data}
    
    except CustomUser.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'An account with the provided credentials does not exist, please check the account details and try again'}
           
    except Grade.DoesNotExist:
        return { 'error': 'grade with the provided credentials does not exist' }

    except Exception as e:
        # Handle any unexpected errors with a general error message
        return {'error': str(e)}
