# python 

# httpx

# channels
from channels.db import database_sync_to_async

# django
from django.db.models import Prefetch

# simple jwt

# models 
from users.models import Principal, Admin
from grades.models import Grade
from terms.models import Term
from subjects.models import Subject
from classes.models import Classroom
from student_group_timetables.models import StudentGroupTimetable

# serilializers
from users.serializers.principals.principals_serializers import PrincipalAccountSerializer
from users.serializers.students.students_serializers import StudentSourceAccountSerializer
from users.serializers.admins.admins_serializers import AdminAccountSerializer
from users.serializers.teachers.teachers_serializers import TeacherAccountSerializer
from audit_logs.serializers import AuditEntriesSerializer, AuditEntrySerializer
from grades.serializers import GradeSerializer, GradesSerializer, GradeDetailsSerializer
from terms.serializers import  TermsSerializer, TermSerializer, ClassesSerializer
from subjects.serializers import SubjectSerializer, SubjectDetailsSerializer

# mappings
from users.maps import role_specific_maps

# queries
from users.complex_queries import queries
    
# utlity functions
from permissions.utils import has_permission
from audit_logs.utils import log_audit


@database_sync_to_async
def search_audit_entries(user, role, details):
    try:
        # Get the appropriate model for the requesting user's role from the mapping.
        Model = role_specific_maps.account_access_control_mapping[role]

        # Build the queryset for the requesting account with the necessary related fields.
        requesting_account = Model.objects.select_related('school').only('school').get(account_id=user)

        # Check if the user has permission to create an assessment
        if role != 'PRINCIPAL' and not has_permission(requesting_account, 'VIEW', 'AUDIT_ENTRIES'):
            response = f'could not proccess your request, you do not have the necessary permissions to view audit entries. please contact your administrator to adjust you permissions for viewing audit entries.'

            log_audit(
                actor=requesting_account,
                action='VIEW',
                target_model='AUDIT_ENTRIES',
                outcome='DENIED',
                response=response,
                school=requesting_account.school
            )

            return {'error': response}
        
        entries = requesting_account.school.audit_logs.only('actor', 'actor__name', 'actor__surname', 'outcome', 'target_model', 'timestamp', 'audit_id').filter(action=details.get('action'))
        serialized_entries = AuditEntriesSerializer(instance=entries, many=True).data

        return {"entries": serialized_entries}
                   
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
def search_audit_entry(user, role, details):
    try:
        # Get the appropriate model for the requesting user's role from the mapping.
        Model = role_specific_maps.account_access_control_mapping[role]

        # Build the queryset for the requesting account with the necessary related fields.
        requesting_account = Model.objects.select_related('school').only('school').get(account_id=user)

        # Check if the user has permission to create an assessment
        if role != 'PRINCIPAL' and not has_permission(requesting_account, 'VIEW', 'AUDIT_ENTRIES'):
            response = f'could not proccess your request, you do not have the necessary permissions to view audit entries. please contact your administrator to adjust you permissions for viewing audit entries.'

            log_audit(
                actor=requesting_account,
                action='VIEW',
                target_model='AUDIT_ENTRIES',
                outcome='DENIED',
                response=response,
                school=requesting_account.school
            )

            return {'error': response}
        
        entries = requesting_account.school.audit_logs.only('actor', 'outcome', 'target_model', 'response', 'timestamp').get(audit_id=details.get('entry'))
        serialized_entry = AuditEntrySerializer(instance=entries).data

        return {"entry": serialized_entry}
                   
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
def search_grades(user, role, details):
    try:
        # Get the appropriate model for the requesting user's role from the mapping.
        Model = role_specific_maps.account_access_control_mapping[role]

        # Build the queryset for the requesting account with the necessary related fields.
        requesting_account = Model.objects.select_related('school').prefetch_related('school__grades').only('school').get(account_id=user)
        
        if details.get('time_stamp'):
            grades = requesting_account.school.grades.filter(created__gt=details['time_stamp'].isoformat())
        else:
            grades = requesting_account.school.grades.all()

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
def search_grade(user, role, details):
    try:
        # Get the appropriate model for the requesting user's role
        Model = role_specific_maps.account_access_control_mapping[role]

        # Retrieve the user and related school in a single query using select_related
        requesting_account = Model.objects.select_related('school').only('school').get(account_id=user)

        grade  = Grade.objects.get(grade_id=details.get('grade'), school=requesting_account.school)

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
        # Get the appropriate model for the requesting user's role
        Model = role_specific_maps.account_access_control_mapping[role]

        # Retrieve the user and related school in a single query using select_related
        requesting_account = Model.objects.select_related('school').only('school').get(account_id=user)

        grade = Grade.objects.get(grade_id=details.get('grade'), school=requesting_account.school)
        
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
def search_grade_terms(user, role, details):
    try:
        # Get the appropriate model for the requesting user's role
        Model = role_specific_maps.account_access_control_mapping[role]

        # Retrieve the user and related school in a single query using select_related
        requesting_account = Model.objects.select_related('school').prefetch_related('school__terms').only('school').get(account_id=user)

        # Prefetch related school terms to minimize database hits
        grade_terms = requesting_account.school.terms.all()
        
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
def search_grade_register_classes(user, role, details):
    try:
        # Get the appropriate model for the requesting user's role
        Model = role_specific_maps.account_access_control_mapping[role]

        # Retrieve the user and related school in a single query using select_related
        requesting_account = Model.objects.select_related('school').only('school').get(account_id=user)

        grade  = Grade.objects.prefetch_related(Prefetch('grade_classes', queryset=Classroom.objects.filter(register_class=True))).get(grade_id=details.get('grade_id'), school=requesting_account.school)

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
def search_term_details(user, role, details):
    try:
        # Get the appropriate model for the requesting user's role
        Model = role_specific_maps.account_access_control_mapping[role]

        # Retrieve the user and related school in a single query using select_related
        requesting_account = Model.objects.select_related('school').only('school').get(account_id=user)

        term = Term.objects.get(term_id=details.get('term'), school=requesting_account.school)
        
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
    try:
        # Get the appropriate model for the requesting user's role
        Model = role_specific_maps.account_access_control_mapping[role]

        # Retrieve the user and related school in a single query using select_related
        requesting_account = Model.objects.select_related('school').only('school').get(account_id=user)

        # Retrieve the subject and its related grade
        subject = Subject.objects.get(subject_id=details.get('subject'), grade__school=requesting_account.school)

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
        # Get the appropriate model for the requesting user's role
        Model = role_specific_maps.account_access_control_mapping[role]

        # Retrieve the user and related school in a single query using select_related
        requesting_account = Model.objects.select_related('school').only('school').get(account_id=user)

        subject = Subject.objects.get(subject_id=details.get('subject'), grade__school=requesting_account.school)
        
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
    try:
        # Get the appropriate model for the requesting user's role
        Model = role_specific_maps.account_access_control_mapping[role]

        if details.get('role') == 'admins':
            # Retrieve the user and related school in a single query using select_related
            requesting_account = Model.objects.select_related('school').prefetch_related('school__admins', 'school__principal').get(account_id=user)

            # Fetch all admin accounts in the school
            admins = requesting_account.school.admins.all().exclude(account_id=user)
            serialized_accounts = AdminAccountSerializer(admins, many=True).data

            # If the user is not a principal, exclude them from the results
            if role != 'PRINCIPAL':
                principal = requesting_account.school.principal
                if principal:
                    serialized_principal = PrincipalAccountSerializer(principal).data
                    serialized_accounts.append(serialized_principal)

        elif details.get('role') == 'teachers':
            # Retrieve the user and related school in a single query using select_related
            requesting_account = Model.objects.select_related('school').prefetch_related('school__teachers').get(account_id=user)

            # Fetch all teacher accounts in the school, excluding the current user
            teachers = requesting_account.school.teachers.all()
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
        # Get the appropriate model for the requesting user's role from the mapping.
        Model = role_specific_maps.account_access_control_mapping[role]

        # Build the queryset for the requesting account with the necessary related fields.
        requesting_account = Model.objects.select_related('school').only('school').get(account_id=user)

        grade = Grade.objects.prefetch_related('students').get(grade_id=details.get('grade'), school=requesting_account.school.pk)

        serialized_students = StudentSourceAccountSerializer(grade.students.all(), many=True).data

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
    try:
        # Get the appropriate model for the requesting user's role from the mapping.
        Model = role_specific_maps.account_access_control_mapping[role]

        # Build the queryset for the requesting account with the necessary related fields.
        requesting_account = Model.objects.select_related('school').only('school').get(account_id=user)

        # Retrieve the group schedule
        group_schedule = StudentGroupTimetable.objects.prefetch_related('students').get(group_schedule_id=details.get('group_schedule_id'), grade__school=requesting_account.school)

        # Get all students subscribed to this group schedule
        students = group_schedule.students.all()

        # Serialize the students
        serialized_students = StudentSourceAccountSerializer(students, many=True).data

        return {"students": serialized_students}
               
    except Principal.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'a principal account with the provided credentials does not exist, please check the account details and try again'}
                   
    except Admin.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'an admin account with the provided credentials does not exist, please check the account details and try again'}
                
    except StudentGroupTimetable.DoesNotExist:
        return {'error': 'a group schedule in your school with the provided credentials does not exist. Please check the group schedule details and try again.'}

    except Exception as e:
        # Handle any unexpected errors with a general error message
        return {'error': str(e)}
