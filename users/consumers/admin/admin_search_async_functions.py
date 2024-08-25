# python 

# httpx

# channels
from channels.db import database_sync_to_async

# django
from django.db.models import Prefetch

# simple jwt

# models 
from users.models import Principal, Admin
from grades.models import Grade, Subject, Term
from classes.models import Classroom
from schedules.models import GroupSchedule

# serilializers
from users.serializers.principals.principals_serializers import PrincipalAccountSerializer
from users.serializers.students.students_serializers import StudentAccountSerializer
from users.serializers.admins.admins_serializers import AdminAccountSerializer
from users.serializers.teachers.teachers_serializers import TeacherAccountSerializer
from grades.serializers import GradeSerializer, GradeDetailsSerializer, TermsSerializer, TermSerializer, SubjectSerializer, SubjectDetailsSerializer, ClassesSerializer

# utility functions 


@database_sync_to_async
def search_grade(user, role, details):

    try:
        # Retrieve the user and related school in a single query using select_related
        if role == 'PRINCIPAL':
            admin = Principal.objects.select_related('school').only('school').get(account_id=user)
        else:
            admin = Admin.objects.select_related('school').only('school').get(account_id=user)

        grade  = Grade.objects.get(grade_id=details.get('grade'), school=admin.school)

        serialized_grade = GradeSerializer(instance=grade).data

        return {'grade' : serialized_grade}
               
    except Principal.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'a principal account with the provided credentials does not exist, please check the account details and try again'}
                   
    except Admin.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'an admin account with the provided credentials does not exist, please check the account details and try again'}
    
    except Grade.DoesNotExist:
        # Handle the case where the provided grade ID does not exist
        return {'error': 'a grade in your school with the provided credentials does not exist, please check the grade details and try again'}

    except Exception as e:
        # Handle any unexpected errors with a general error message
        return {'error': str(e)}


@database_sync_to_async
def search_grade_details(user, role, details):
    try:
        # Retrieve the user and related school in a single query using select_related
        if role == 'PRINCIPAL':
            admin = Principal.objects.select_related('school').only('school').get(account_id=user)
        else:
            admin = Admin.objects.select_related('school').only('school').get(account_id=user)

        grade = Grade.objects.get(grade_id=details.get('grade'), school=admin.school)
        
        # Serialize the grade
        serialized_grade = GradeDetailsSerializer(grade).data
        
        # Return the serialized grade in a dictionary
        return {'grade': serialized_grade}
               
    except Principal.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'a principal account with the provided credentials does not exist, please check the account details and try again'}
                   
    except Admin.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'an admin account with the provided credentials does not exist, please check the account details and try again'}
    
    except Grade.DoesNotExist:
        # Handle the case where the provided grade ID does not exist
        return {'error': 'a grade in your school with the provided credentials does not exist, please check the grade details and try again'}

    except Exception as e:
        # Handle any unexpected errors with a general error message
        return {'error': f'An unexpected error occurred: {str(e)}'}


@database_sync_to_async
def search_grade_register_classes(user, role, details):

    try:
        # Retrieve the user and related school in a single query using select_related
        if role == 'PRINCIPAL':
            admin = Principal.objects.select_related('school').only('school').get(account_id=user)
        else:
            admin = Admin.objects.select_related('school').only('school').get(account_id=user)

        grade  = Grade.objects.prefetch_related(Prefetch('grade_classes', queryset=Classroom.objects.filter(register_class=True))).get(grade_id=details.get('grade_id'), school=admin.school)

        classes = grade.grade_classes.all()

        serialized_classes = ClassesSerializer(classes, many=True).data

        return {"classes": serialized_classes}
               
    except Principal.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'a principal account with the provided credentials does not exist, please check the account details and try again'}
                   
    except Admin.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'an admin account with the provided credentials does not exist, please check the account details and try again'}
    
    except Grade.DoesNotExist:
        # Handle the case where the provided grade ID does not exist
        return {'error': 'a grade in your school with the provided credentials does not exist, please check the grade details and try again'}

    except Exception as e:
        # Handle any unexpected errors with a general error message
        return {'error': str(e)}
    

@database_sync_to_async
def search_school_terms(user, role, details):
    """
    Fetch all the terms associated with the school linked to a given user.

    This function retrieves the school associated with the provided user account,
    and then fetches all the terms related to that school. It handles cases where
    the user does not exist and returns a descriptive error message in such scenarios.

    Args:
        user (str): The account ID of the user whose school terms are to be fetched.

    Returns:
        dict: A dictionary containing either the serialized terms data or an error message.
    """
    try:
        # Retrieve the user and related school in a single query using select_related
        if role == 'PRINCIPAL':
            admin = Principal.objects.select_related('school').only('school').get(account_id=user)
        else:
            admin = Admin.objects.select_related('school').only('school').get(account_id=user)

        grade = Grade.objects.prefetch_related('grade_terms').get(grade_id=details.get('grade'), school=admin.school)

        # Prefetch related school terms to minimize database hits
        grade_terms = grade.grade_terms.all()
        
        # Serialize the school terms
        serialized_terms = TermsSerializer(grade_terms, many=True).data
        
        # Return the serialized terms in a dictionary
        return {'terms': serialized_terms}
               
    except Principal.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'a principal account with the provided credentials does not exist, please check the account details and try again'}
                   
    except Admin.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'an admin account with the provided credentials does not exist, please check the account details and try again'}
    
    except Grade.DoesNotExist:
        # Handle the case where the provided grade ID does not exist
        return {'error': 'a grade in your school with the provided credentials does not exist, please check the grade details and try again'}

    except Exception as e:
        # Handle any unexpected errors with a general error message
        return {'error': f'An unexpected error occurred: {str(e)}'}
    

@database_sync_to_async
def search_term_details(user, role, details):
    try:
        # Retrieve the user and related school in a single query using select_related
        if role == 'PRINCIPAL':
            admin = Principal.objects.select_related('school').only('school').get(account_id=user)
        else:
            admin = Admin.objects.select_related('school').only('school').get(account_id=user)

        term = Term.objects.get(term_id=details.get('term'), school=admin.school)
        
        # Serialize the school terms
        serialized_term = TermSerializer(term).data
        
        # Return the serialized terms in a dictionary
        return {'term': serialized_term}
               
    except Principal.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'a principal account with the provided credentials does not exist, please check the account details and try again'}
                   
    except Admin.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'an admin account with the provided credentials does not exist, please check the account details and try again'}
    
    except Term.DoesNotExist:
        # Handle the case where the provided term ID does not exist
        return {'error': 'a term in your school with the provided credentials does not exist, please check the term details and try again'}

    except Exception as e:
        # Handle any unexpected errors with a general error message
        return {'error': f'An unexpected error occurred: {str(e)}'}


@database_sync_to_async
def search_subject(user, role, details):
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
        # Retrieve the user and related school in a single query using select_related
        if role == 'PRINCIPAL':
            admin = Principal.objects.select_related('school').only('school').get(account_id=user)
        else:
            admin = Admin.objects.select_related('school').only('school').get(account_id=user)

        # Retrieve the subject and its related grade
        subject = Subject.objects.get(subject_id=details.get('subject_id'), grade__school=admin.school)

        # Serialize the subject data
        serialized_subject = SubjectSerializer(subject).data

        return {"subject": serialized_subject}
               
    except Principal.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'a principal account with the provided credentials does not exist, please check the account details and try again'}
                   
    except Admin.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'an admin account with the provided credentials does not exist, please check the account details and try again'}
    
    except Subject.DoesNotExist:
        # Handle case where the subject does not exist
        return {'error': 'a subject in your school with the provided credentials does not exist, please check the subject details and try again'}

    except Exception as e:
        # Handle any unexpected errors with a general error message
        return {'error': str(e)}


@database_sync_to_async
def search_subject_details(user, role, details):
    try:
        # Retrieve the user and related school in a single query using select_related
        if role == 'PRINCIPAL':
            admin = Principal.objects.select_related('school').only('school').get(account_id=user)
        else:
            admin = Admin.objects.select_related('school').only('school').get(account_id=user)

        subject = Subject.objects.get(subject_id=details.get('subject'), grade__school=admin.school)
        
        # Serialize the subject
        serialized_subject = SubjectDetailsSerializer(subject).data
        
        # Return the serialized grade in a dictionary
        return {'subject': serialized_subject}
               
    except Principal.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'a principal account with the provided credentials does not exist, please check the account details and try again'}
                   
    except Admin.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'an admin account with the provided credentials does not exist, please check the account details and try again'}
    
    except Subject.DoesNotExist:
        # Handle case where the subject does not exist
        return {'error': 'a subject in your school with the provided credentials does not exist, please check the subject details and try again'}

    except Exception as e:
        # Handle any unexpected errors with a general error message
        return {'error': f'An unexpected error occurred: {str(e)}'}
    

@database_sync_to_async
def search_accounts(user, role, details):
    """
    Search for accounts within a school based on the provided role and details.

    Args:
        user (str): The account ID of the user making the request.
        role (str): The role of the user making the request ('PRINCIPAL' or 'ADMIN').
        details (dict): The search details containing the target role to filter accounts.

    Returns:
        dict: A dictionary containing the serialized account data or an error message.
    """
    try:
        # Retrieve the user and related school in a single query using select_related
        if role == 'PRINCIPAL':
            admin = Principal.objects.select_related('school').only('school').get(account_id=user)
        else:
            admin = Admin.objects.select_related('school').only('school').get(account_id=user)

        if details.get('role') == 'admins':
            # Fetch all admin accounts in the school
            admins = admin.school.admins.exclude(account_id=user)
            serialized_accounts = AdminAccountSerializer(admins, many=True).data

            # If the user is not a principal, exclude them from the results
            if role != 'PRINCIPAL':
                principal = admin.school.principal
                if principal:
                    serialized_accounts.append(PrincipalAccountSerializer(principal).data)

        elif details.get('role') == 'teachers':
            # Fetch all teacher accounts in the school, excluding the current user
            teachers = admin.school.teachers
            serialized_accounts = TeacherAccountSerializer(teachers, many=True).data

        else:
            return {"error": "could not proccess your request, the role specified is invalid"}

        return {"users": serialized_accounts}

    except Principal.DoesNotExist:
        # Handle the case where the principal account does not exist
        return {'error': 'a principal account with the provided credentials does not exist, please check the account details and try again'}

    except Admin.DoesNotExist:
        # Handle the case where the admin account does not exist
        return {'error': 'an admin account with the provided credentials does not exist, please check the account details and try again'}

    except Exception as e:
        # Handle any unexpected errors with a general error message
        return {'error': str(e)} 
    

@database_sync_to_async
def search_students(user, role, details):

    try:
        # Retrieve the user and related school in a single query using select_related
        if role == 'PRINCIPAL':
            admin = Principal.objects.select_related('school').only('school').get(account_id=user)
        else:
            admin = Admin.objects.select_related('school').only('school').get(account_id=user)

        grade = Grade.objects.prefetch_related('students').get(grade_id=details.get('grade'), school=admin.school.pk)

        serialized_students = StudentAccountSerializer(grade.students.all(), many=True).data

        return {"students": serialized_students}
               
    except Principal.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'a principal account with the provided credentials does not exist, please check the account details and try again'}
                   
    except Admin.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'an admin account with the provided credentials does not exist, please check the account details and try again'}
    
    except Grade.DoesNotExist:
        # Handle the case where the provided grade ID does not exist
        return { 'error': 'a grade in your school with the provided credentials does not exist, please check the grade details and try again'}

    except Exception as e:
        # Handle any unexpected errors with a general error message
        return {'error': str(e)}


@database_sync_to_async
def search_subscribed_students(user, role, details):
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
        # Retrieve the user and related school in a single query using select_related
        if role == 'PRINCIPAL':
            admin = Principal.objects.select_related('school').only('school').get(account_id=user)
        else:
            admin = Admin.objects.select_related('school').only('school').get(account_id=user)

        # Retrieve the group schedule
        group_schedule = GroupSchedule.objects.prefetch_related('students').get(group_schedule_id=details.get('group_schedule_id'), grade__school=admin.school)

        # Get all students subscribed to this group schedule
        students = group_schedule.students.all()

        # Serialize the students
        serialized_students = StudentAccountSerializer(students, many=True).data

        return {"students": serialized_students}
               
    except Principal.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'a principal account with the provided credentials does not exist, please check the account details and try again'}
                   
    except Admin.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'an admin account with the provided credentials does not exist, please check the account details and try again'}
                
    except GroupSchedule.DoesNotExist:
        return {'error': 'a group schedule in your school with the provided credentials does not exist. Please check the group schedule details and try again.'}

    except Exception as e:
        # Handle any unexpected errors with a general error message
        return {'error': str(e)}
