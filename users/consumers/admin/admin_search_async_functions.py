# python 
from datetime import datetime

# channels
from channels.db import database_sync_to_async

# django
from django.db.models import Prefetch
from django.utils.translation import gettext as _
from django.db.models import Q

# models 
from users.models import Teacher
from audit_logs.models import AuditLog
from grades.models import Grade
from terms.models import Term
from subjects.models import Subject
from classes.models import Classroom
from assessments.models import Assessment
from student_group_timetables.models import StudentGroupTimetable

# serilializers
from users.serializers.principals.principals_serializers import PrincipalAccountSerializer
from users.serializers.students.students_serializers import StudentSourceAccountSerializer, LeastAccountDetailsSerializer
from users.serializers.admins.admins_serializers import AdminAccountSerializer
from users.serializers.teachers.teachers_serializers import TeacherAccountSerializer
from schools.serializers import SchoolDetailsSerializer
from audit_logs.serializers import AuditEntriesSerializer, AuditEntrySerializer
from grades.serializers import GradeSerializer, GradesSerializer, GradeDetailsSerializer
from terms.serializers import  TermsSerializer, TermSerializer, ClassesSerializer
from subjects.serializers import SubjectSerializer, SubjectDetailsSerializer
from classes.serializers import TeacherClassesSerializer
from assessments.serializers import DueAssessmentsSerializer, CollectedAssessmentsSerializer, DueAssessmentSerializer, CollectedAssessmentSerializer
from activities.serializers import ActivitiesSerializer
from daily_schedules.serializers import DailyScheduleSerializer

# checks
from users.checks import permission_checks

# utility functions 
from users import utils as users_utilities
from permissions import utils as permissions_utilities
from audit_logs import utils as audits_utilities
from attendances import utils as attendances_utilities
    
    
@database_sync_to_async
def search_school_details(user, role):
    try:
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = users_utilities.get_account_and_linked_school(user, role)

        # Serialize the school object into a dictionary
        serialized_school = SchoolDetailsSerializer(requesting_account.school).data
        
        return {"school": serialized_school}

    except Exception as e:
        # Handle any unexpected errors with a general error message
        return {'error': str(e)}


@database_sync_to_async
def search_audit_entries(user, role, details):
    try:
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = users_utilities.get_account_and_linked_school(user, role)

        # Check if the user has permission to create an assessment
        if role != 'PRINCIPAL' and not permissions_utilities.has_permission(requesting_account, 'VIEW', 'AUDIT_ENTRY'):
            response = f'could not proccess your request, you do not have the necessary permissions to view audit entries. please contact your administrator to adjust you permissions for viewing audit entries.'
            audits_utilities.log_audit(actor=requesting_account, action='VIEW', target_model='AUDIT_ENTRIES', outcome='DENIED', response=response, school=requesting_account.school)

            return {'error': response}
        
        if 'action' not in details or details['action'] not in [choice[0] for choice in AuditLog.ACTION_CHOICES]:
            response = f'could not proccess your request, the provided information is invalid for the action you are trying to perform. please make sure the audit entries action query is correct and try again'
            audits_utilities.log_audit(actor=requesting_account, action='VIEW', target_model='AUDIT_ENTRY', outcome='ERROR', response=response, school=requesting_account.school)

            return {'error': response}

        entries = requesting_account.school.audit_logs.only('actor', 'actor__name', 'actor__surname', 'outcome', 'target_model', 'timestamp', 'audit_id').filter(action=details['action'])
        serialized_entries = AuditEntriesSerializer(instance=entries, many=True).data

        return {"entries": serialized_entries}

    except Exception as e:
        # Handle any unexpected errors with a general error message
        return {'error': str(e)}


@database_sync_to_async
def search_audit_entry(user, role, details):
    try:
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = users_utilities.get_account_and_linked_school(user, role)

        # Check if the user has permission to create an assessment
        if role != 'PRINCIPAL' and not permissions_utilities.has_permission(requesting_account, 'VIEW', 'AUDIT_ENTRY'):
            response = f'could not proccess your request, you do not have the necessary permissions to view audit entries. please contact your administrator to adjust you permissions for viewing audit entries.'
            audits_utilities.log_audit(actor=requesting_account, action='VIEW', target_model='AUDIT_ENTRIES', outcome='DENIED', response=response, school=requesting_account.school)

            return {'error': response}
        
        if 'entry' not in details:
            response = f'could not proccess your request, the provided information is invalid for the action you are trying to perform. please make sure to provide a valid audit entry ID and try again'
            audits_utilities.log_audit(actor=requesting_account, action='VIEW', target_model='AUDIT_ENTRY', outcome='ERROR', response=response, school=requesting_account.school)

            return {'error': response}
     
        entries = requesting_account.school.audit_logs.only('actor', 'outcome', 'target_model', 'response', 'timestamp').get(audit_id=details['entry'])
        serialized_entry = AuditEntrySerializer(instance=entries).data

        return {"entry": serialized_entry}

    except Exception as e:
        # Handle any unexpected errors with a general error message
        return {'error': str(e)}


@database_sync_to_async
def search_accounts(user, role, details):
    try:
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = users_utilities.get_account_and_linked_school(user, role)

        if role != 'PRINCIPAL' and not permissions_utilities.has_permission(requesting_account, 'VIEW', 'ACCOUNT'):
            response = f'could not proccess your request, you do not have the necessary permissions to view accounts. please contact your administrator to adjust you permissions for viewing accounts.'
            audits_utilities.log_audit(actor=requesting_account, action='VIEW', target_model='ACCOUNT', outcome='DENIED', response=response, school=requesting_account.school)

            return {'error': response}

        if 'role' not in details or details['role'] not in ['admins', 'teachers']:
            response = f'could not proccess your request, the provided information is invalid for the action you are trying to perform. please make sure to provide a valid accounts role and try again'
            audits_utilities.log_audit(actor=requesting_account, action='VIEW', target_model='ACCOUNT', outcome='ERROR', response=response, school=requesting_account.school)

            return {'error': response}
 
        if details['role'] == 'admins':
            # Fetch all admin accounts in the school
            admins = requesting_account.school.admins.all().exclude(account_id=user)
            serialized_accounts = AdminAccountSerializer(admins, many=True).data

            # If the user is not a principal
            if role != 'PRINCIPAL':
                principal = requesting_account.school.principal
                if principal:
                    serialized_principal = PrincipalAccountSerializer(principal).data
                    serialized_accounts.append(serialized_principal)

        elif details['role'] == 'teachers':
            # Fetch all teacher accounts in the school, excluding the current user
            teachers = requesting_account.school.teachers.all()
            serialized_accounts = TeacherAccountSerializer(teachers, many=True).data

        return {"users": serialized_accounts}

    except Exception as e:
        # Handle any unexpected errors with a general error message
        return {'error': str(e)} 
    

@database_sync_to_async
def search_students(user, role, details):
    try:
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = users_utilities.get_account_and_linked_school(user, role)

        if role != 'PRINCIPAL' and not permissions_utilities.has_permission(requesting_account, 'VIEW', 'ACCOUNT'):
            response = f'could not proccess your request, you do not have the necessary permissions to view accounts. please contact your administrator to adjust you permissions for viewing accounts.'
            audits_utilities.log_audit(actor=requesting_account, action='VIEW', target_model='ACCOUNT', outcome='DENIED', response=response, school=requesting_account.school)

            return {'error': response}

        if 'grade' not in details:
            response = f'could not proccess your request, the provided information is invalid for the action you are trying to perform. please make sure to provide a valid grade ID and try again'
            audits_utilities.log_audit(actor=requesting_account, action='VIEW', target_model='ACCOUNT', outcome='ERROR', response=response, school=requesting_account.school)

            return {'error': response}

        grade = requesting_account.school.grades.prefetch_related('students').get(grade_id=details['grade'])
        serialized_students = StudentSourceAccountSerializer(grade.students.all(), many=True).data

        return {"students": serialized_students}
    
    except Grade.DoesNotExist:
        # Handle the case where the provided grade ID does not exist
        return { 'error': 'a grade in your school with the provided credentials does not exist, please check the grade details and try again'}

    except Exception as e:
        # Handle any unexpected errors with a general error message
        return {'error': str(e)}


@database_sync_to_async
def search_grades(user, role, details):
    try:
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = users_utilities.get_account_and_linked_school(user, role)
        
        if role != 'PRINCIPAL' and not permissions_utilities.has_permission(requesting_account, 'VIEW', 'GRADE'):
            response = f'could not proccess your request, you do not have the necessary permissions to view school grades. please contact your administrator to adjust you permissions for viewing school grades.'
            audits_utilities.log_audit(actor=requesting_account, action='VIEW', target_model='GRADE', outcome='DENIED', response=response, school=requesting_account.school)

            return {'error': response}

        if details.get('last_updated'):
            # Convert the timestamp to a string in ISO format
            time_stamp = datetime.fromtimestamp((details['last_updated'] + 1) / 1000).isoformat()
            # Filter grades created after the given timestamp
            grades = requesting_account.school.grades.filter(last_updated__gt=time_stamp)            
        
        else:
            grades = requesting_account.school.grades.all()

        # Serialize the grade objects into a dictionary
        serialized_grades = GradesSerializer(grades, many=True).data

        return {'grades': serialized_grades}

    except Exception as e:
        # Handle any unexpected errors with a general error message
        return {'error': str(e)}
    

@database_sync_to_async
def search_grade(user, role, details):
    try:
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = users_utilities.get_account_and_linked_school(user, role)

        if role != 'PRINCIPAL' and not permissions_utilities.has_permission(requesting_account, 'VIEW', 'GRADE'):
            response = f'could not proccess your request, you do not have the necessary permissions to view grades. please contact your administrator to adjust you permissions for viewing grades.'
            audits_utilities.log_audit(actor=requesting_account, action='VIEW', target_model='GRADE', outcome='DENIED', response=response, school=requesting_account.school)

            return {'error': response}

        if 'grade' not in details:
            response = f'could not proccess your request, the provided information is invalid for the action you are trying to perform. please make sure to provide a valid grade ID and try again'
            audits_utilities.log_audit(actor=requesting_account, action='VIEW', target_model='GRADE', outcome='ERROR', response=response, school=requesting_account.school)

            return {'error': response}

        grade  = requesting_account.school.grades.get(grade_id=details['grade'])
        serialized_grade = GradeSerializer(instance=grade).data

        return {'grade' : serialized_grade}
    
    except Grade.DoesNotExist:
        # Handle the case where the provided grade ID does not exist
        return {'error': 'a grade in your school with the provided credentials does not exist, please check the grade details and try again'}

    except Exception as e:
        # Handle any unexpected errors with a general error message
        return {'error': str(e)}


@database_sync_to_async
def search_grade_details(user, role, details):
    try:
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = users_utilities.get_account_and_linked_school(user, role)

        if role != 'PRINCIPAL' and not permissions_utilities.has_permission(requesting_account, 'VIEW', 'GRADE'):
            response = f'could not proccess your request, you do not have the necessary permissions to view grades. please contact your administrator to adjust you permissions for viewing grades.'
            audits_utilities.log_audit(actor=requesting_account, action='VIEW', target_model='GRADE', outcome='DENIED', response=response, school=requesting_account.school)

            return {'error': response}

        if 'grade' not in details:
            response = f'could not proccess your request, the provided information is invalid for the action you are trying to perform. please make sure to provide a valid grade ID and try again'
            audits_utilities.log_audit(actor=requesting_account, action='VIEW', target_model='GRADE', outcome='ERROR', response=response, school=requesting_account.school)

            return {'error': response}

        grade = requesting_account.grades.get(grade_id=details['grade'])
        serialized_grade = GradeDetailsSerializer(grade).data
        
        # Return the serialized grade in a dictionary
        return {'grade': serialized_grade}
    
    except Grade.DoesNotExist:
        # Handle the case where the provided grade ID does not exist
        return {'error': 'a grade in your school with the provided credentials does not exist, please check the grade details and try again'}

    except Exception as e:
        # Handle any unexpected errors with a general error message
        return {'error': f'An unexpected error occurred: {str(e)}'}


@database_sync_to_async
def search_grade_terms(user, role, details):
    try:
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = users_utilities.get_account_and_linked_school(user, role)

        if role != 'PRINCIPAL' and not permissions_utilities.has_permission(requesting_account, 'VIEW', 'TERM'):
            response = f'could not proccess your request, you do not have the necessary permissions to view terms. please contact your administrator to adjust you permissions for viewing terms.'
            audits_utilities.log_audit(actor=requesting_account, action='VIEW', target_model='TERM', outcome='DENIED', response=response, school=requesting_account.school)

            return {'error': response}

        if 'grade' not in details:
            response = f'could not proccess your request, the provided information is invalid for the action you are trying to perform. please make sure to provide a valid grade ID and try again'
            audits_utilities.log_audit(actor=requesting_account, action='VIEW', target_model='TERM', outcome='ERROR', response=response, school=requesting_account.school)

            return {'error': response}

        # Prefetch related school terms to minimize database hits
        grade_terms = requesting_account.school.terms.filter(grade__grade_id=details['grade'])
        serialized_terms = TermsSerializer(grade_terms, many=True).data
        
        # Return the serialized terms in a dictionary
        return {'terms': serialized_terms}

    except Exception as e:
        # Handle any unexpected errors with a general error message
        return {'error': f'An unexpected error occurred: {str(e)}'}


@database_sync_to_async
def search_grade_register_classes(user, role, details):
    try:
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = users_utilities.get_account_and_linked_school(user, role)

        if role != 'PRINCIPAL' and not permissions_utilities.has_permission(requesting_account, 'VIEW', 'CLASSROOM'):
            response = f'could not proccess your request, you do not have the necessary permissions to view classrooms. please contact your administrator to adjust you permissions for viewing classrooms.'
            audits_utilities.log_audit(actor=requesting_account, action='VIEW', target_model='CLASSROOM', outcome='DENIED', response=response, school=requesting_account.school)

            return {'error': response}

        if 'grade' not in details:
            response = f'could not proccess your request, the provided information is invalid for the action you are trying to perform. please make sure to provide a valid grade ID and try again'
            audits_utilities.log_audit(actor=requesting_account, action='VIEW', target_model='CLASSROOM', outcome='ERROR', response=response, school=requesting_account.school)

            return {'error': response}

        grade  = requesting_account.school.grades.prefetch_related(Prefetch('classrooms', queryset=Classroom.objects.filter(register_class=True))).get(grade_id=details['grade'])
        serialized_classes = ClassesSerializer(grade.classes.all(), many=True).data

        return {"classes": serialized_classes}
    
    except Grade.DoesNotExist:
        # Handle the case where the provided grade ID does not exist
        return {'error': 'a grade in your school with the provided credentials does not exist, please check the grade details and try again'}

    except Exception as e:
        # Handle any unexpected errors with a general error message
        return {'error': str(e)}


@database_sync_to_async
def search_term_details(user, role, details):
    try:
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = users_utilities.get_account_and_linked_school(user, role)

        if role != 'PRINCIPAL' and not permissions_utilities.has_permission(requesting_account, 'VIEW', 'TERM'):
            response = f'could not proccess your request, you do not have the necessary permissions to view terms. please contact your administrator to adjust you permissions for viewing terms.'
            audits_utilities.log_audit(actor=requesting_account, action='VIEW', target_model='TERM', outcome='DENIED', response=response, school=requesting_account.school)

            return {'error': response}

        if 'term' not in details:
            response = f'could not proccess your request, the provided information is invalid for the action you are trying to perform. please make sure to provide a valid term ID and try again'
            audits_utilities.log_audit(actor=requesting_account, action='VIEW', target_model='TERM', outcome='ERROR', response=response, school=requesting_account.school)

            return {'error': response}

        term = requesting_account.school.terms.get(term_id=details['term'])
        serialized_term = TermSerializer(term).data
        
        # Return the serialized terms in a dictionary
        return {'term': serialized_term}
    
    except Term.DoesNotExist:
        # Handle the case where the provided term ID does not exist
        return {'error': 'a term in your school with the provided credentials does not exist, please check the term details and try again'}

    except Exception as e:
        # Handle any unexpected errors with a general error message
        return {'error': f'An unexpected error occurred: {str(e)}'}


@database_sync_to_async
def search_subject(user, role, details):
    try:
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = users_utilities.get_account_and_linked_school(user, role)

        if role != 'PRINCIPAL' and not permissions_utilities.has_permission(requesting_account, 'VIEW', 'SUBJECT'):
            response = f'could not proccess your request, you do not have the necessary permissions to view subjects. please contact your administrator to adjust you permissions for viewing subjects.'
            audits_utilities.log_audit(actor=requesting_account, action='VIEW', target_model='CLASSROOM', outcome='DENIED', response=response, school=requesting_account.school)

            return {'error': response}

        if 'subject' not in details:
            response = f'could not proccess your request, the provided information is invalid for the action you are trying to perform. please make sure to provide a valid subject ID and try again'
            audits_utilities.log_audit(actor=requesting_account, action='VIEW', target_model='SUBJECT', outcome='ERROR', response=response, school=requesting_account.school)

            return {'error': response}

        # Retrieve the subject
        subject = Subject.objects.get(subject_id=details['subject'], grade__school=requesting_account.school)
        serialized_subject = SubjectSerializer(subject).data

        return {"subject": serialized_subject}
    
    except Subject.DoesNotExist:
        # Handle case where the subject does not exist
        return {'error': 'a subject in your school with the provided credentials does not exist, please check the subject details and try again'}

    except Exception as e:
        # Handle any unexpected errors with a general error message
        return {'error': str(e)}


@database_sync_to_async
def search_subject_details(user, role, details):
    try:
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = users_utilities.get_account_and_linked_school(user, role)

        if role != 'PRINCIPAL' and not permissions_utilities.has_permission(requesting_account, 'VIEW', 'SUBJECT'):
            response = f'could not proccess your request, you do not have the necessary permissions to view subjects. please contact your administrator to adjust you permissions for viewing subjects.'
            audits_utilities.log_audit(actor=requesting_account, action='VIEW', target_model='CLASSROOM', outcome='DENIED', response=response, school=requesting_account.school)

            return {'error': response}

        if 'subject' not in details:
            response = f'could not proccess your request, the provided information is invalid for the action you are trying to perform. please make sure to provide a valid subject ID and try again'
            audits_utilities.log_audit(actor=requesting_account, action='VIEW', target_model='SUBJECT', outcome='ERROR', response=response, school=requesting_account.school)

            return {'error': response}

        subject = Subject.objects.get(subject_id=details['subject'], grade__school=requesting_account.school)
        serialized_subject = SubjectDetailsSerializer(subject).data
        
        return {'subject': serialized_subject}
    
    except Subject.DoesNotExist:
        # Handle case where the subject does not exist
        return {'error': 'a subject in your school with the provided credentials does not exist, please check the subject details and try again'}

    except Exception as e:
        # Handle any unexpected errors with a general error message
        return {'error': f'An unexpected error occurred: {str(e)}'}


@database_sync_to_async
def search_assessments(user, role, details):
    try:
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = users_utilities.get_account_and_linked_school(user, role)
        
        # Check if the user has permission to create an assessment
        if role != 'PRINCIPAL' and not permissions_utilities.has_permission(requesting_account, 'VIEW', 'ASSESSMENT'):
            response = f'could not proccess your request, you do not have the necessary permissions to view assessments. please contact your principal to adjust you permissions for viewing assessments.'
            audits_utilities.log_audit(actor=requesting_account, action='VIEW', target_model='ASSESSMENTS', outcome='DENIED', response=response, school=requesting_account.school)

            return {'error': response}
        
        # Determine the classroom based on the request details
        if details.get('grade') and details.get('subject'):
            grade = requesting_account.school.grades.get(grade_id=details['grade'])
            subject = grade.subjects.get(subject_id=details['subject'])

            assessments = subject.assessments.filter(collected=details.get('collected'), grades_released=False)

        elif details.get('classroom'):
            # Fetch the specific classroom based on classroom_id and school
            classroom = requesting_account.school.classrooms.get(classroom_id=details['classroom'])
        
            assessments = classroom.assessments.filter(collected=details.get('collected'), grades_released=False)

        else:
            response = f'could not proccess your request, the provided information is invalid for the action you are trying to perform. please make sure to provide valid grade and subject IDs or a valid classroom ID and try again'
            audits_utilities.log_audit(actor=requesting_account, action='VIEW', target_model='ASSESSMENT', outcome='ERROR', response=response, school=requesting_account.school)

            return {'error': response}

        if assessments:
            serialized_assessments = CollectedAssessmentsSerializer(assessments, many=True).data if details.get('collected') else DueAssessmentsSerializer(assessments, many=True).data
        else:
            serialized_assessments = []

        return {"assessments": serialized_assessments}
        
    except Grade.DoesNotExist:
        # Handle the case where the provided grade ID does not exist
        return { 'error': 'a grade in your school with the provided credentials does not exist, please check the grade details and try again'}
    
    except Subject.DoesNotExist:
        # Handle case where the subject does not exist
        return {'error': 'a subject in your school with the provided credentials does not exist, please check the subject details and try again'}

    except Classroom.DoesNotExist:
        # Handle case where the classroom does not exist
        return {'error': _('A classroom in your school with the provided details does not exist. Please check the classroom details and try again.')}
    
    except Exception as e:
        # Handle any other unexpected errors
        return {'error': str(e)}


@database_sync_to_async
def search_assessment(user, role, details):
    try:
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = users_utilities.get_account_and_linked_school(user, role)
        
        # Check if the user has permission to create an assessment
        if role != 'PRINCIPAL' and not permissions_utilities.has_permission(requesting_account, 'VIEW', 'ASSESSMENT'):
            response = f'could not proccess your request, you do not have the necessary permissions to view assessments. please contact your principal to adjust you permissions for viewing assessments.'
            audits_utilities.log_audit(actor=requesting_account, action='VIEW', target_model='ASSESSMENTS', outcome='DENIED', response=response, school=requesting_account.school)

            return {'error': response}
        
        if 'assessment' not in details:
            response = f'could not proccess your request, the provided information is invalid for the action you are trying to perform. please make sure to provide a valid assessment ID and try again'
            audits_utilities.log_audit(actor=requesting_account, action='VIEW', target_model='ASSESSMENT', outcome='ERROR', response=response, school=requesting_account.school)

            return {'error': response}

        assessment = requesting_account.school.assessments.get(assessment_id=details['assessment'], collected=details.get('collected'), grades_released=False)
        serialized_assessment = CollectedAssessmentSerializer(assessment).data if details.get('collected') else DueAssessmentSerializer(assessment).data

        return {"assessment": serialized_assessment}
        
    except Assessment.DoesNotExist:
        # Handle the case where the provided assessment ID does not exist
        return { 'error': 'an assessment in your school with the provided credentials does not exist, please check the assessment details and try again'}
        
    except Exception as e:
        # Handle any other unexpected errors
        return {'error': str(e)}


@database_sync_to_async
def search_student_class_card(user, role, details):
    try:
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = users_utilities.get_account_and_attr(user, role)

        if role != 'PRINCIPAL' and not permissions_utilities.has_permission(requesting_account, 'VIEW', 'ACCOUNT'):
            response = f'could not proccess your request, you do not have the necessary permissions to view classrooms. please contact your administrator to adjust you permissions for viewing classrooms.'
            audits_utilities.log_audit(actor=requesting_account, action='VIEW', target_model='ACCOUNT', outcome='DENIED', response=response, school=requesting_account.school)

            return {'error': response}

        if not {'account', 'classroom'}.issubset(details):
            response = f'could not proccess your request, the provided information is invalid for the action you are trying to perform. please make sure to provide valid account and classroom IDs and try again'
            audits_utilities.log_audit(actor=requesting_account, action='VIEW', target_model='ACCOUNT', outcome='ERROR', response=response, school=requesting_account.school)

            return {'error': response}

        # Retrieve the requested users account and related school in a single query using select_related
        requested_account = users_utilities.get_account_and_attr(details['account'], 'STUDENT')

        # Check permissions
        permission_error = permission_checks.check_profile_or_details_view_permissions(requesting_account, requested_account)
        if permission_error:
            return permission_error

        # retrieve the students activities 
        activities = requested_account.my_activities.filter(classroom__classroom_id=details['classroom'])
        
        serialized_student = StudentSourceAccountSerializer(instance=requested_account).data
        serialized_activities = ActivitiesSerializer(activities, many=True).data

        return {"student": serialized_student, 'activities': serialized_activities}

    except Classroom.DoesNotExist:
        # Handle case where the classroom does not exist
        return {'error': 'a classroom in your school with the provided credentials does not exist. please check the classroom details and try again.'}

    except Exception as e:
        # Handle any other unexpected errors
        return {'error': str(e)}


@database_sync_to_async
def search_subscribed_students(user, role, details):
    try:
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = users_utilities.get_account_and_linked_school(user, role)

        if role != 'PRINCIPAL' and not permissions_utilities.has_permission(requesting_account, 'VIEW', 'GROUP_TIMETABLE'):
            response = f'could not proccess your request, you do not have the necessary permissions to view group schedules. please contact your administrator to adjust you permissions for viewing group schedules.'
            audits_utilities.log_audit(actor=requesting_account, action='VIEW', target_model='GROUP_TIMETABLE', outcome='DENIED', response=response, school=requesting_account.school)

            return {'error': response}

        if 'group_timetable' not in details:
            response = f'could not proccess your request, the provided information is invalid for the action you are trying to perform. please make sure to provide a valid group schedule ID and try again'
            audits_utilities.log_audit(actor=requesting_account, action='VIEW', target_model='GROUP_TIMETABLE', outcome='ERROR', response=response, school=requesting_account.school)

            return {'error': response}

        # Retrieve the group schedule
        group_schedule = requesting_account.school.group_timetables.prefetch_related('students').get(group_timetable_id=details['group_timetable'])
        serialized_students = StudentSourceAccountSerializer(group_schedule.students.all(), many=True).data

        return {"students": serialized_students}
                
    except StudentGroupTimetable.DoesNotExist:
        return {'error': 'a group schedule in your school with the provided credentials does not exist. Please check the group schedule details and try again.'}

    except Exception as e:
        # Handle any unexpected errors with a general error message
        return {'error': str(e)}


@database_sync_to_async
def search_month_attendance_records(user, role, details):
    try:
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = users_utilities.get_account_and_linked_school(user, role)
 
        if role != 'PRINCIPAL' and not permissions_utilities.has_permission(requesting_account, 'VIEW', 'ATTENDANCE'):
            response = f'could not proccess your request, you do not have the necessary permissions to view classrooms. please contact your administrator to adjust you permissions for viewing classrooms.'
            audits_utilities.log_audit(actor=requesting_account, action='VIEW', target_model='ATTENDANCE', outcome='DENIED', response=response, school=requesting_account.school)

            return {'error': response}

        if not {'month_name', 'classroom'}.issubset(details):
            response = f'could not proccess your request, the provided information is invalid for the action you are trying to perform. please make sure to provide a valid month name and classroom ID and try again'
            audits_utilities.log_audit(actor=requesting_account, action='VIEW', target_model='ATTENDANCE', outcome='ERROR', response=response, school=requesting_account.school)

            return {'error': response}

        classroom = requesting_account.school.classrooms.get(classroom_id=details['classroom'], register_class=True)
        
        start_date, end_date = attendances_utilities.get_month_dates(details['month_name'])

        # Query for the Absent instances where absentes is True
        attendances = requesting_account.school.attendances.prefetch_related('absent_students').filter(Q(date__gte=start_date) & Q(date__lt=end_date) & Q(classroom=classroom) & Q(absentes=True))

        # For each absent instance, get the corresponding Late instance
        attendance_records = []
        for attendance in attendances:
            record = {
                'date': attendance.date.isoformat(),
                'absent_students': LeastAccountDetailsSerializer(attendance.absent_students.all(), many=True).data,
                'late_students': LeastAccountDetailsSerializer(attendance.late_students.all(), many=True).data if attendance.late_students else [],
            }
            attendance_records.append(record)

        return {'records': attendance_records}
    
    except Classroom.DoesNotExist:
        return {'error': 'a classroom in your school with the provided credentials does not exist. Please check the classrooms details and try again.'}

    except Exception as e:
        return {'error': str(e)}


@database_sync_to_async
def search_teacher_classes(user, role, details):
    try:
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = users_utilities.get_account_and_linked_school(user, role)

        if role != 'PRINCIPAL' and not permissions_utilities.has_permission(requesting_account, 'VIEW', 'CLASSROOM'):
            response = f'could not proccess your request, you do not have the necessary permissions to view classrooms. please contact your administrator to adjust you permissions for viewing classrooms.'
            audits_utilities.log_audit(actor=requesting_account, action='VIEW', target_model='CLASSROOM', outcome='DENIED', response=response, school=requesting_account.school)

            return {'error': response}

        if 'teacher' not in details:
            response = f'could not proccess your request, the provided information is invalid for the action you are trying to perform. please make sure to provide a valid account ID and try again'
            audits_utilities.log_audit(actor=requesting_account, action='VIEW', target_model='CLASSROOM', outcome='ERROR', response=response, school=requesting_account.school)

            return {'error': response}

        teacher = requesting_account.school.teachers.prefetch_related('taught_classes').get(account_id=details['teacher'])
        serializer = TeacherClassesSerializer(teacher.taught_classes, many=True)

        return {"classes": serializer.data}
               
    except Teacher.DoesNotExist:
        # Handle the case where the requested teacher account does not exist.
        return {'error': 'a teacher account in your school with the provided credentials does not exist. please check the account details and try again'}
    
    except Exception as e:
        return { 'error': str(e) }


@database_sync_to_async
def search_teacher_schedule_schedules(user, role, details):
    try:
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = users_utilities.get_account_and_linked_school(user, role)

        if role != 'PRINCIPAL' and not permissions_utilities.has_permission(requesting_account, 'VIEW', 'TEACHER_TIMETABLE'):
            response = f'could not proccess your request, you do not have the necessary permissions to view teacher timetables. please contact your administrator to adjust you permissions for viewing teacher timetables.'
            audits_utilities.log_audit(actor=requesting_account, action='VIEW', target_model='TEACHER_TIMETABLE', outcome='DENIED', response=response, school=requesting_account.school)

            return {'error': response}

        if 'teacher' not in details:
            response = f'could not proccess your request, the provided information is invalid for the action you are trying to perform. please make sure to provide a valid account ID and try again'
            audits_utilities.log_audit(actor=requesting_account, action='VIEW', target_model='TEACHER_TIMETABLE', outcome='ERROR', response=response, school=requesting_account.school)

            return {'error': response}

        teacher = requesting_account.school.teachers.prefetch_related('teacher_schedule__schedules').get(account_id=details['teacher'])

        # Check if the teacher has a schedule
        if hasattr(teacher, 'teacher_schedule'):
            serialized_schedules = DailyScheduleSerializer(teacher.teacher_schedule.schedules.all(), many=True).data
        else:
            serialized_schedules = []

        return {"schedules": serialized_schedules}
               
    except Teacher.DoesNotExist:
        # Handle the case where the requested teacher account does not exist.
        return {'error': 'a teacher account in your school with the provided credentials does not exist. please check the account details and try again'}
    
    except Exception as e:
        # Handle any other unexpected errors
        return {'error': str(e)}
