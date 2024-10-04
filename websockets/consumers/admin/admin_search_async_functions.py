# python
import base64
import zlib
import json

# channels
from channels.db import database_sync_to_async

# django
from django.db import models, transaction
from django.utils.translation import gettext as _

# models 
from accounts.models import Teacher, Student
from audit_logs.models import AuditLog
from permission_groups.models import AdminPermissionGroup, TeacherPermissionGroup
from account_permissions.models import AdminAccountPermission, TeacherAccountPermission
from grades.models import Grade
from terms.models import Term
from subjects.models import Subject
from classrooms.models import Classroom
from assessments.models import Assessment
from assessment_transcripts.models import AssessmentTranscript
from student_activities.models import StudentActivity
from timetables.models import Timetable
from student_group_timetables.models import StudentGroupTimetable

# serilializers
from accounts.serializers.general_serializers import BasicAccountDetailsEmailSerializer
from accounts.serializers.principals.serializers import PrincipalAccountSerializer
from accounts.serializers.students.serializers import StudentSourceAccountSerializer, LeastAccountDetailsSerializer
from accounts.serializers.admins.serializers import AdminAccountSerializer
from accounts.serializers.teachers.serializers import TeacherAccountSerializer
from accounts.serializers.parents.serializers import ParentAccountSerializer
from audit_logs.serializers import AuditEntriesSerializer, AuditEntrySerializer
from permission_groups.serializers import AdminPermissionGroupsSerializer, TeacherPermissionGroupsSerializer, AdminPermissionGroupSerializer, TeacherPermissionGroupSerializer
from school_announcements.serializers import AnnouncementSerializer
from grades.serializers import GradeSerializer, GradesSerializer, GradeDetailsSerializer
from terms.serializers import  TermsSerializer, TermSerializer
from term_subject_performances.serializers import TermSubjectPerformanceSerializer
from subjects.serializers import SubjectSerializer, SubjectDetailsSerializer
from classrooms.serializers import TeacherClassroomsSerializer, ClassesSerializer, ClassroomSerializer
from assessments.serializers import DueAssessmentsSerializer, CollectedAssessmentsSerializer, GradedAssessmentsSerializer, DueAssessmentSerializer, CollectedAssessmentSerializer, GradedAssessmentSerializer
from assessment_transcripts.serializers import TranscriptsSerializer, TranscriptSerializer
from student_activities.serializers import ActivitiesSerializer, ActivitySerializer
from student_group_timetables.serializers import StudentGroupTimetablesSerializer, StudentGroupTimetableDetailsSerializer
from timetables.serializers import TimetableSerializer

# checks
from accounts.checks import permission_checks

# mappings
from accounts.mappings import serializer_mappings

# utility functions 
from accounts import utils as accounts_utilities
from account_permissions import utils as permissions_utilities
from audit_logs import utils as audits_utilities
from school_attendances import utils as attendances_utilities

    
@database_sync_to_async
def search_audit_entries(user, role, details):
    try:
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = accounts_utilities.get_account_and_linked_school(user, role)

        # Check if the user has permission to create an assessment
        if role != 'PRINCIPAL' and not permissions_utilities.has_permission(requesting_account, 'VIEW', 'AUDIT_ENTRY'):
            response = f'could not proccess your request, you do not have the necessary permissions to view audit entries. please contact your administrators to adjust you permissions for viewing audit entries.'
            audits_utilities.log_audit(actor=requesting_account, action='VIEW', target_model='AUDIT_ENTRIES', outcome='DENIED', server_response=response, school=requesting_account.school)
            return {'error': response}
        
        if 'action' not in details or details['action'] not in [choice[0] for choice in AuditLog.ACTION_CHOICES]:
            response = f'could not proccess your request, the provided information is invalid for the action you are trying to perform. please make sure the audit entries action query is correct and try again'
            audits_utilities.log_audit(actor=requesting_account, action='VIEW', target_model='AUDIT_ENTRY', outcome='ERROR', server_response=response, school=requesting_account.school)
            return {'error': response}

        entries = requesting_account.school.audit_logs.only('actor__name', 'actor__surname', 'outcome', 'target_model', 'timestamp', 'audit_entry_id').filter(action=details['action'])
        serialized_entries = AuditEntriesSerializer(entries, many=True).data

        return {"entries": serialized_entries}

    except Exception as e:
        # Handle any unexpected errors with a general error message
        return {'error': str(e)}


@database_sync_to_async
def search_audit_entry(user, role, details):
    try:
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = accounts_utilities.get_account_and_linked_school(user, role)

        # Check if the user has permission to create an assessment
        if role != 'PRINCIPAL' and not permissions_utilities.has_permission(requesting_account, 'VIEW', 'AUDIT_ENTRY'):
            response = f'Could not proccess your request, you do not have the necessary permissions to view an audit entry. Please contact your administrators to adjust you permissions for viewing audit entries.'
            audits_utilities.log_audit(actor=requesting_account, action='VIEW', target_model='AUDIT_ENTRIES', outcome='DENIED', server_response=response, school=requesting_account.school)
            return {'error': response}
        
        if 'entry' not in details:
            response = f'Could not proccess your request, the provided information is invalid for the action you are trying to perform. Please make sure to provide a valid audit entry ID and try again'
            audits_utilities.log_audit(actor=requesting_account, action='VIEW', target_model='AUDIT_ENTRY', outcome='ERROR', server_response=response, school=requesting_account.school)
            return {'error': response}
     
        entries = requesting_account.school.audit_logs.only('actor', 'outcome', 'target_model', 'server_response', 'timestamp').get(audit_entry_id=details['entry'])
        serialized_entry = AuditEntrySerializer(instance=entries).data

        return {"entry": serialized_entry}
    
    except AuditLog.DoesNotExist:
        # Handle the case where the provided grade ID does not exist
        return { 'error': 'Could not process your request, a audit entry in your school with the provided credentials does not exist. Please review the entries details and try again'}

    except Exception as e:
        # Handle any unexpected errors with a general error message
        return {'error': str(e)}


@database_sync_to_async
def search_permission_groups(user, role, details):
    try:
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = accounts_utilities.get_account_and_linked_school(user, role)

        # Check if the user has permission to create an assessment
        if role != 'PRINCIPAL' and not permissions_utilities.has_permission(requesting_account, 'VIEW', 'PERMISSION'):
            response = f'Could not proccess your request, you do not have the necessary permissions to view permission groups. Please contact your administrators to adjust you permissions for viewing permissions.'
            audits_utilities.log_audit(actor=requesting_account, action='VIEW', target_model='PERMISSION', outcome='DENIED', server_response=response, school=requesting_account.school)
            return {'error': response}
        
        if 'group' not in details or details['group'] not in ['admins', 'teachers']:
            response = f'Could not proccess your request, the provided information is invalid for the action you are trying to perform. Please make sure to provide a valid group (admin or teacher) for which to filter the permission groups and try again'
            audits_utilities.log_audit(actor=requesting_account, action='VIEW', target_model='PERMISSION', outcome='ERROR', server_response=response, school=requesting_account.school)
            return {'error': response}
        
        # Determine the group type based on the role
        if details['group'] == 'admins':
            # Create an admin permission group
            groups = requesting_account.school.admin_permission_groups.only('group_name', 'subscribers_count', 'permissions_count', 'last_updated', 'permission_group_id')
            serialized_permission_groups = AdminPermissionGroupsSerializer(groups, many=True).data
            
        elif details['group'] == 'teachers':
            # Create a teacher permission group
            groups = requesting_account.school.teacher_permission_groups.only('group_name', 'subscribers_count', 'permissions_count', 'last_updated', 'permission_group_id')
            serialized_permission_groups = TeacherPermissionGroupsSerializer(groups, many=True).data

        return {"permission_groups": serialized_permission_groups}

    except Exception as e:
        # Handle any unexpected errors with a general error message
        return {'error': str(e)}


@database_sync_to_async
def search_permission_group(user, role, details):
    try:
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = accounts_utilities.get_account_and_linked_school(user, role)

        # Check if the user has permission to create an assessment
        if role != 'PRINCIPAL' and not permissions_utilities.has_permission(requesting_account, 'VIEW', 'PERMISSION'):
            response = f'Could not proccess your request, you do not have the necessary permissions to view permission group details. Please contact your administrators to adjust you permissions for viewing permissions.'
            audits_utilities.log_audit(actor=requesting_account, action='VIEW', target_model='PERMISSION', outcome='DENIED', server_response=response, school=requesting_account.school)
            return {'error': response}
        
        if not {'permission_group', 'group'}.issubset(details) or details['group'] not in ['admins', 'teachers']:
            response = f'Could not proccess your request, the provided information is invalid for the action you are trying to perform. Please make sure to provide a valid group ID and group (admin or teacher) for which to filter the permission groups and try again'
            audits_utilities.log_audit(actor=requesting_account, action='VIEW', target_model='PERMISSION', outcome='ERROR', server_response=response, school=requesting_account.school)
            return {'error': response}
        
        # Determine the group type based on the role
        if details['group'] == 'admins':
            group = requesting_account.school.admin_permission_groups.only(
                'group_name', 'permissions_count', 'description', 'timestamp'
            ).prefetch_related(
                models.Prefetch('permissions', queryset=AdminAccountPermission.objects.only('action', 'target_model'))
            ).get(permission_group_id=details['permission_group'])
            serialized_permission_group = AdminPermissionGroupSerializer(instance=group).data
      
        else:
            group = requesting_account.school.teacher_permission_groups.only(
                'group_name', 'permissions_count', 'description', 'timestamp'
            ).prefetch_related(
                models.Prefetch('permissions', queryset=TeacherAccountPermission.objects.only('action', 'target_model'))
            ).get(permission_group_id=details['permission_group'])
            serialized_permission_group = TeacherPermissionGroupSerializer(instance=group).data

        return {"permission_group": serialized_permission_group}
    
    except AdminPermissionGroup.DoesNotExist:
        # Handle the case where the provided grade ID does not exist
        return { 'error': 'Could not process your request, a admin permission group in your school with the provided credentials does not exist. Please review the group details and try again'}
    
    except TeacherPermissionGroup.DoesNotExist:
        # Handle the case where the provided grade ID does not exist
        return { 'error': 'Could not process your request, a teacher permission group  in your school with the provided credentials does not exist. Please review the group details and try again'}

    except Exception as e:
        # Handle any unexpected errors with a general error message
        return {'error': str(e)}


@database_sync_to_async
def search_permission_group_subscribers(user, role, details):
    try:
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = accounts_utilities.get_account_and_linked_school(user, role)

        # Check if the user has permission to create an assessment
        if role != 'PRINCIPAL' and not permissions_utilities.has_permission(requesting_account, 'VIEW', 'PERMISSION'):
            response = f'could not proccess your request, you do not have the necessary permissions to view permission group subscribers. please contact your administrators to adjust you permissions for viewing permissions.'
            audits_utilities.log_audit(actor=requesting_account, action='VIEW', target_model='PERMISSION', outcome='DENIED', server_response=response, school=requesting_account.school)
            return {'error': response}
        
        if not {'permission_group', 'group'}.issubset(details) or details['group'] not in ['admins', 'teachers']:
            response = f'could not proccess your request, the provided information is invalid for the action you are trying to perform. please make sure to provide a valid group ID and group (admin or teacher) for which to filter the permission groups and try again'
            audits_utilities.log_audit(actor=requesting_account, action='VIEW', target_model='PERMISSION', outcome='ERROR', server_response=response, school=requesting_account.school)
            return {'error': response}
        
        # Determine the group type based on the role
        if details['group'] == 'admins':
            group = requesting_account.school.admin_permission_groups.prefetch_related('subscribers').get(permission_group_id=details['permission_group'])
            subscribers = group.subscribers.only('name', 'surname', 'email_address', 'profile_picture')
      
        elif details['group'] == 'teachers':
            group = requesting_account.school.teacher_permission_groups.prefetch_related('subscribers').get(permission_group_id=details['permission_group'])
            subscribers = group.subscribers.only('name', 'surname', 'email_address', 'profile_picture')

        serialized_subscribers = BasicAccountDetailsEmailSerializer(subscribers, many=True).data

        # Compress the serialized data
        compressed_subscribers = zlib.compress(json.dumps(serialized_subscribers).encode('utf-8'))

        # Encode compressed data as base64 for safe transport
        encoded_subscribers = base64.b64encode(compressed_subscribers).decode('utf-8')

        return {"subscribers": encoded_subscribers}
    
    except AdminPermissionGroup.DoesNotExist:
        # Handle the case where the provided grade ID does not exist
        return { 'error': 'Could not process your request, a admin permission group in your school with the provided credentials does not exist. Please review the group details and try again'}
    
    except TeacherPermissionGroup.DoesNotExist:
        # Handle the case where the provided grade ID does not exist
        return { 'error': 'Could not process your request, a teacher permission group  in your school with the provided credentials does not exist. Please review the group details and try again'}

    except Exception as e:
        # Handle any unexpected errors with a general error message
        return {'error': str(e)}


@database_sync_to_async
def search_school_announcement(user, role, details):
    try:
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = accounts_utilities.get_account_and_linked_school(user, role)
        
        if not 'announcement' in details:
            response = f'could not proccess your request, the provided information is invalid for the action you are trying to perform. please make sure to provide a valid announcement ID and try again'
            audits_utilities.log_audit(actor=requesting_account, action='VIEW', target_model='ANNOUNCEMENT', outcome='ERROR', server_response=response, school=requesting_account.school)
            return {'error': response}

        # Retrieve the specified announcement
        announcement = requesting_account.announcements.get(announcement_id=details.get('announcement'))

        # Check if the user is already in the reached list and add if not
        if not announcement.accounts_reached.filter(pk=requesting_account.pk).exists():
            with transaction.atomic():
                announcement.reached(user)

        # Serialize and return the announcement data
        serialized_announcement = AnnouncementSerializer(announcement).data

        return {'announcement': serialized_announcement}
    
    except Exception as e:
        # Handle any other unexpected errors
        return {'error': str(e)}


@database_sync_to_async
def search_accounts(user, role, details):
    try:
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = accounts_utilities.get_account_and_linked_school(user, role)

        if role != 'PRINCIPAL' and not permissions_utilities.has_permission(requesting_account, 'VIEW', 'ACCOUNT'):
            response = f'could not proccess your request, you do not have the necessary permissions to view accounts. please contact your administrator to adjust you permissions for viewing accounts.'
            audits_utilities.log_audit(actor=requesting_account, action='VIEW', target_model='ACCOUNT', outcome='DENIED', server_response=response, school=requesting_account.school)
            return {'error': response}

        if 'role' not in details or details['role'] not in ['admins', 'teachers']:
            response = f'could not proccess your request, the provided information is invalid for the action you are trying to perform. please make sure to provide a valid accounts role and try again'
            audits_utilities.log_audit(actor=requesting_account, action='VIEW', target_model='ACCOUNT', outcome='ERROR', server_response=response, school=requesting_account.school)
            return {'error': response}
 
        if details['role'] == 'admins':
            # Fetch all admin accounts in the school
            admins = requesting_account.school.admins.only('name', 'surname', 'email_address', 'profile_picture', 'account_id').exclude(account_id=user)
            serialized_accounts = AdminAccountSerializer(admins, many=True).data

            # If the user is not a principal
            if role != 'PRINCIPAL':
                principal = requesting_account.school.principal.only('name', 'surname', 'email_address', 'profile_picture', 'account_id')
                if principal:
                    serialized_principal = PrincipalAccountSerializer(principal).data
                    serialized_accounts.append(serialized_principal)

        else:
            # Fetch all teacher accounts in the school, excluding the current user
            teachers = requesting_account.school.teachers.only('name', 'surname', 'email_address', 'profile_picture', 'account_id')
            serialized_accounts = TeacherAccountSerializer(teachers, many=True).data

        # Compress the serialized data
        compressed_accounts = zlib.compress(json.dumps(serialized_accounts).encode('utf-8'))
        # Encode compressed data as base64 for safe transport
        encoded_accounts = base64.b64encode(compressed_accounts).decode('utf-8')

        return {"accounts": encoded_accounts}

    except Exception as e:
        # Handle any unexpected errors with a general error message
        return {'error': str(e)} 


@database_sync_to_async
def search_account(user, role, details):
    try:
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = accounts_utilities.get_account_and_linked_school(user, role)

        if role != 'PRINCIPAL' and not permissions_utilities.has_permission(requesting_account, 'VIEW', 'ACCOUNT'):
            response = f'could not proccess your request, you do not have the necessary permissions to view accounts. please contact your administrator to adjust you permissions for viewing accounts.'
            audits_utilities.log_audit(actor=requesting_account, action='VIEW', target_model='ACCOUNT', outcome='DENIED', server_response=response, school=requesting_account.school)
            return {'error': response}

        if not {'account', 'role', 'reason'}.issubset(details) or details['reason'] not in ['details', 'profile'] or details['role'] not in ['PRINCIPAL', 'ADMIN', 'TEACHER', 'STUDENT', 'PARENT']:
            response = f'could not proccess your request, the provided information is invalid for the action you are trying to perform. please make sure to provide a valid account ID, role and reason and try again'
            audits_utilities.log_audit(actor=requesting_account, action='VIEW', target_model='ACCOUNT', outcome='ERROR', server_response=response, school=requesting_account.school)
            return {'error': response}

        # Build the queryset for the requested account with the necessary related fields.
        requested_account = accounts_utilities.get_account_and_permission_check_attr(details['account'], details['role'])

        # Check if the requesting user has permission to view the requested user's profile or details.
        permission_error = permission_checks.view_account(requesting_account, requested_account)
        if permission_error:
            # Return an error message if the requesting user does not have the necessary permissions.
            return permission_error

        # Handle the request based on the reason provided (either 'details' or 'profile').
        if details.get('reason') == 'details':
            # Get the appropriate serializer for the requested user's role.
            Serializer = serializer_mappings.account_details[details['role']]
            # Serialize the requested user's details and return the serialized data.
            serialized_account = Serializer(instance=requested_account).data

        elif details.get('reason') == 'profile':
            # Get the appropriate serializer for the requested user's role.
            Serializer = serializer_mappings.account_profile[details['role']]
            # Serialize the requested user's details and return the serialized data.
            serialized_account = Serializer(instance=requested_account).data

        # Compress the serialized data
        compressed_account = zlib.compress(json.dumps(serialized_account).encode('utf-8'))
        # Encode compressed data as base64 for safe transport
        encoded_account = base64.b64encode(compressed_account).decode('utf-8')

        # Return the serialized user data if everything is successful.
        return {"account": encoded_account}
    
    except Exception as e:
        # Handle any other unexpected errors and return the error message.
        return {'error': str(e)}


@database_sync_to_async
def search_students(user, role, details):
    try:
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = accounts_utilities.get_account_and_linked_school(user, role)

        if role != 'PRINCIPAL' and not permissions_utilities.has_permission(requesting_account, 'VIEW', 'ACCOUNT'):
            response = f'could not proccess your request, you do not have the necessary permissions to view accounts. please contact your administrator to adjust you permissions for viewing accounts.'
            audits_utilities.log_audit(actor=requesting_account, action='VIEW', target_model='ACCOUNT', outcome='DENIED', server_response=response, school=requesting_account.school)
            return {'error': response}

        if 'grade' not in details:
            response = f'could not proccess your request, the provided information is invalid for the action you are trying to perform. please make sure to provide a valid grade ID and try again'
            audits_utilities.log_audit(actor=requesting_account, action='VIEW', target_model='ACCOUNT', outcome='ERROR', server_response=response, school=requesting_account.school)
            return {'error': response}

        grade = requesting_account.school.grades.prefetch_related('students').get(grade_id=details['grade'])
        serialized_students = StudentSourceAccountSerializer(grade.students.only('name', 'surname', 'id_number', 'passport_number', 'email_address', 'profile_picture', 'account_id'), many=True).data

        # Compress the serialized data
        compressed_students = zlib.compress(json.dumps(serialized_students).encode('utf-8'))
        # Encode compressed data as base64 for safe transport
        encoded_students = base64.b64encode(compressed_students).decode('utf-8')

        return {"students": encoded_students}
    
    except Grade.DoesNotExist:
        # Handle the case where the provided grade ID does not exist
        return { 'error': 'Could not process your request, a grade in your school with the provided credentials does not exist. Please check the grade details and try again'}

    except Exception as e:
        # Handle any unexpected errors with a general error message
        return {'error': str(e)}


@database_sync_to_async
def search_parents(user, role, details):
    try:
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = accounts_utilities.get_account_and_linked_school(user, role)

        if role != 'PRINCIPAL' and not permissions_utilities.has_permission(requesting_account, 'VIEW', 'ACCOUNT'):
            response = f'could not proccess your request, you do not have the necessary permissions to view accounts. please contact your administrator to adjust you permissions for viewing accounts.'
            audits_utilities.log_audit(actor=requesting_account, action='VIEW', target_model='ACCOUNT', outcome='DENIED', server_response=response, school=requesting_account.school)
            return {'error': response}

        if 'account' not in details:
            response = f'could not proccess your request, the provided information is invalid for the action you are trying to perform. please make sure to provide a valid account ID and try again'
            audits_utilities.log_audit(actor=requesting_account, action='VIEW', target_model='ACCOUNT', outcome='ERROR', server_response=response, school=requesting_account.school)
            return {'error': response}

        requested_account = requesting_account.school.students.prefetch_related('parents').get(account_id=details['account'])
    
        parents = requested_account.parents

        # Serialize the parents to return them in the response
        serialized_parents = ParentAccountSerializer(parents, many=True).data

        # Compress the serialized data
        compressed_parents = zlib.compress(json.dumps(serialized_parents).encode('utf-8'))
        # Encode compressed data as base64 for safe transport
        encoded_parents = base64.b64encode(compressed_parents).decode('utf-8')

        return {"parents": encoded_parents}
                       
    except Student.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'Could not process your request, a student account with the provided credentials in your school does not exist. Please review the account details and try again.'}

    except Exception as e:
        # Handle any other unexpected errors and return the error message.
        return {'error': str(e)}


@database_sync_to_async
def search_grades(user, role, details):
    try:
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = accounts_utilities.get_account_and_linked_school(user, role)
        
        if role != 'PRINCIPAL' and not permissions_utilities.has_permission(requesting_account, 'VIEW', 'GRADE'):
            response = f'could not proccess your request, you do not have the necessary permissions to view school grades. please contact your administrator to adjust you permissions for viewing school grades.'
            audits_utilities.log_audit(actor=requesting_account, action='VIEW', target_model='GRADE', outcome='DENIED', server_response=response, school=requesting_account.school)
            return {'error': response}

        if details.get('timestamp'):
            # Filter grades created after the given timestamp
            grades = requesting_account.school.grades.filter(models.Q(last_updated__gt=details['timestamp']) | models.Q(timestamp__gt=details['timestamp']))

        else:
            grades = requesting_account.school.grades

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
        requesting_account = accounts_utilities.get_account_and_linked_school(user, role)

        if role != 'PRINCIPAL' and not permissions_utilities.has_permission(requesting_account, 'VIEW', 'GRADE'):
            response = f'could not proccess your request, you do not have the necessary permissions to view grades. please contact your administrator to adjust you permissions for viewing grades.'
            audits_utilities.log_audit(actor=requesting_account, action='VIEW', target_model='GRADE', outcome='DENIED', server_response=response, school=requesting_account.school)
            return {'error': response}

        if 'grade' not in details:
            response = f'could not proccess your request, the provided information is invalid for the action you are trying to perform. please make sure to provide a valid grade ID and try again'
            audits_utilities.log_audit(actor=requesting_account, action='VIEW', target_model='GRADE', outcome='ERROR', server_response=response, school=requesting_account.school)
            return {'error': response}

        grade  = requesting_account.school.grades.get(grade_id=details['grade'])
        serialized_grade = GradeSerializer(instance=grade).data

        return {'grade' : serialized_grade}
    
    except Grade.DoesNotExist:
        # Handle the case where the provided grade ID does not exist
        return {'error': 'Could not process your request, a grade in your school with the provided credentials does not exist, please check the grade details and try again.'}

    except Exception as e:
        # Handle any unexpected errors with a general error message
        return {'error': str(e)}


@database_sync_to_async
def search_grade_details(user, role, details):
    try:
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = accounts_utilities.get_account_and_linked_school(user, role)

        if role != 'PRINCIPAL' and not permissions_utilities.has_permission(requesting_account, 'VIEW', 'GRADE'):
            response = f'could not proccess your request, you do not have the necessary permissions to view grades. please contact your administrator to adjust you permissions for viewing grades.'
            audits_utilities.log_audit(actor=requesting_account, action='VIEW', target_model='GRADE', outcome='DENIED', server_response=response, school=requesting_account.school)
            return {'error': response}

        if 'grade' not in details:
            response = f'could not proccess your request, the provided information is invalid for the action you are trying to perform. please make sure to provide a valid grade ID and try again'
            audits_utilities.log_audit(actor=requesting_account, action='VIEW', target_model='GRADE', outcome='ERROR', server_response=response, school=requesting_account.school)
            return {'error': response}

        grade = requesting_account.school.grades.get(grade_id=details['grade'])
        serialized_grade = GradeDetailsSerializer(grade).data
        
        # Return the serialized grade in a dictionary
        return {'grade': serialized_grade}
    
    except Grade.DoesNotExist:
        # Handle the case where the provided grade ID does not exist
        return {'error': 'Could not process your request, a grade in your school with the provided credentials does not exist, please check the grade details and try again.'}

    except Exception as e:
        # Handle any unexpected errors with a general error message
        return {'error': f'An unexpected error occurred: {str(e)}'}


@database_sync_to_async
def search_grade_register_classrooms(user, role, details):
    try:
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = accounts_utilities.get_account_and_linked_school(user, role)

        if role != 'PRINCIPAL' and not permissions_utilities.has_permission(requesting_account, 'VIEW', 'CLASSROOM'):
            response = f'could not proccess your request, you do not have the necessary permissions to view classrooms. please contact your administrator to adjust you permissions for viewing classrooms.'
            audits_utilities.log_audit(actor=requesting_account, action='VIEW', target_model='CLASSROOM', outcome='DENIED', server_response=response, school=requesting_account.school)
            return {'error': response}

        if 'grade' not in details:
            response = f'could not proccess your request, the provided information is invalid for the action you are trying to perform. please make sure to provide a valid grade ID and try again'
            audits_utilities.log_audit(actor=requesting_account, action='VIEW', target_model='CLASSROOM', outcome='ERROR', server_response=response, school=requesting_account.school)
            return {'error': response}

        grade  = requesting_account.school.grades.prefetch_related(models.Prefetch('classrooms', queryset=Classroom.objects.filter(register_class=True))).get(grade_id=details['grade'])
        serialized_classrooms = ClassesSerializer(grade.classes, many=True).data

        return {"classrooms": serialized_classrooms}
    
    except Grade.DoesNotExist:
        # Handle the case where the provided grade ID does not exist
        return {'error': 'Could not process your request, a grade in your school with the provided credentials does not exist, please check the grade details and try again.'}

    except Exception as e:
        # Handle any unexpected errors with a general error message
        return {'error': str(e)}


@database_sync_to_async
def search_subject(user, role, details):
    try:
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = accounts_utilities.get_account_and_linked_school(user, role)

        if role != 'PRINCIPAL' and not permissions_utilities.has_permission(requesting_account, 'VIEW', 'SUBJECT'):
            response = f'could not proccess your request, you do not have the necessary permissions to view subjects. please contact your administrator to adjust you permissions for viewing subjects.'
            audits_utilities.log_audit(actor=requesting_account, action='VIEW', target_model='CLASSROOM', outcome='DENIED', server_response=response, school=requesting_account.school)
            return {'error': response}

        if 'subject' not in details:
            response = f'could not proccess your request, the provided information is invalid for the action you are trying to perform. please make sure to provide a valid subject ID and try again'
            audits_utilities.log_audit(actor=requesting_account, action='VIEW', target_model='SUBJECT', outcome='ERROR', server_response=response, school=requesting_account.school)
            return {'error': response}

        # Retrieve the subject
        subject = requesting_account.subjects.prefetch_related('classrooms').get(subject_id=details['subject'])
        serialized_subject = SubjectSerializer(subject).data

        return {"subject": serialized_subject}
    
    except Subject.DoesNotExist:
        # Handle case where the subject does not exist
        return {'error': 'Could not process your request, a subject in your school with the provided credentials does not exist, please check the subject details and try again.'}

    except Exception as e:
        # Handle any unexpected errors with a general error message
        return {'error': str(e)}


@database_sync_to_async
def search_subject_details(user, role, details):
    try:
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = accounts_utilities.get_account_and_linked_school(user, role)

        if role != 'PRINCIPAL' and not permissions_utilities.has_permission(requesting_account, 'VIEW', 'SUBJECT'):
            response = f'Could not proccess your request, you do not have the necessary permissions to view subjects. please contact your administrator to adjust you permissions for viewing subjects.'
            audits_utilities.log_audit(actor=requesting_account, action='VIEW', target_model='CLASSROOM', outcome='DENIED', server_response=response, school=requesting_account.school)
            return {'error': response}

        if 'subject' not in details:
            response = f'Could not proccess your request, the provided information is invalid for the action you are trying to perform. please make sure to provide a valid subject ID and try again.'
            audits_utilities.log_audit(actor=requesting_account, action='VIEW', target_model='SUBJECT', outcome='ERROR', server_response=response, school=requesting_account.school)
            return {'error': response}

        subject = requesting_account.subjects.only('student_count', 'teacher_count', 'classroom_count', 'major_subject', 'pass_mark').get(subject_id=details['subject'])
        serialized_subject = SubjectDetailsSerializer(subject).data
        
        return {'subject': serialized_subject}
    
    except Subject.DoesNotExist:
        # Handle case where the subject does not exist
        return {'error': 'Could not process your request, a subject in your school with the provided credentials does not exist, please check the subject details and try again'}

    except Exception as e:
        # Handle any unexpected errors with a general error message
        return {'error': str(e)}


@database_sync_to_async
def search_grade_terms(user, role, details):
    try:
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = accounts_utilities.get_account_and_linked_school(user, role)

        if role != 'PRINCIPAL' and not permissions_utilities.has_permission(requesting_account, 'VIEW', 'TERM'):
            response = f'could not proccess your request, you do not have the necessary permissions to view terms. please contact your administrator to adjust you permissions for viewing terms.'
            audits_utilities.log_audit(actor=requesting_account, action='VIEW', target_model='TERM', outcome='DENIED', server_response=response, school=requesting_account.school)
            return {'error': response}

        if 'grade' not in details:
            response = f'could not proccess your request, the provided information is invalid for the action you are trying to perform. please make sure to provide a valid grade ID and try again'
            audits_utilities.log_audit(actor=requesting_account, action='VIEW', target_model='TERM', outcome='ERROR', server_response=response, school=requesting_account.school)
            return {'error': response}

        # Prefetch related school terms to minimize database hits
        grade_terms = requesting_account.school.terms.only('term', 'weight', 'start_date', 'end_date', 'term_id').filter(grade__grade_id=details['grade'])
        serialized_terms = TermsSerializer(grade_terms, many=True).data
        
        # Return the serialized terms in a dictionary
        return {'terms': serialized_terms}

    except Exception as e:
        # Handle any unexpected errors with a general error message
        return {'error': str(e)}


@database_sync_to_async
def search_term_details(user, role, details):
    try:
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = accounts_utilities.get_account_and_linked_school(user, role)

        if role != 'PRINCIPAL' and not permissions_utilities.has_permission(requesting_account, 'VIEW', 'TERM'):
            response = f'could not proccess your request, you do not have the necessary permissions to view terms. please contact your administrator to adjust you permissions for viewing terms.'
            audits_utilities.log_audit(actor=requesting_account, action='VIEW', target_model='TERM', outcome='DENIED', server_response=response, school=requesting_account.school)
            return {'error': response}

        if 'term' not in details:
            response = f'could not proccess your request, the provided information is invalid for the action you are trying to perform. please make sure to provide a valid term ID and try again'
            audits_utilities.log_audit(actor=requesting_account, action='VIEW', target_model='TERM', outcome='ERROR', server_response=response, school=requesting_account.school)
            return {'error': response}

        term = requesting_account.school.terms.only('term', 'weight', 'start_date', 'end_date', 'school_days').get(term_id=details['term'])
        serialized_term = TermSerializer(term).data
        
        # Return the serialized terms in a dictionary
        return {'term': serialized_term}
    
    except Term.DoesNotExist:
        # Handle the case where the provided term ID does not exist
        return {'error': 'Could not process your request, a term in your school with the provided credentials does not exist, please check the term details and try again.'}

    except Exception as e:
        # Handle any unexpected errors with a general error message
        return {'error': f'An unexpected error occurred: {str(e)}'}


@database_sync_to_async
def search_term_subject_performance(user, role, details):
    try:
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = accounts_utilities.get_account_and_linked_school(user, role)

        if role != 'PRINCIPAL' and not permissions_utilities.has_permission(requesting_account, 'VIEW', 'TERM'):
            response = f'could not proccess your request, you do not have the necessary permissions to view term performances. please contact your administrator to adjust you permissions for viewing term details.'
            audits_utilities.log_audit(actor=requesting_account, action='VIEW', target_model='TERM', outcome='DENIED', server_response=response, school=requesting_account.school)
            return {'error': response}

        if not {'term', 'subject'}.issubset(details):
            response = f'could not proccess your request, the provided information is invalid for the action you are trying to perform. please make sure to provide valid term and subject IDs and try again'
            audits_utilities.log_audit(actor=requesting_account, action='VIEW', target_model='TERM', outcome='ERROR', server_response=response, school=requesting_account.school)
            return {'error': response}
        
        term = requesting_account.school.terms.get(term_id=details['term'])
        subject = requesting_account.subjects.get(subject_id=details['subject'])

        performance, created = requesting_account.school.termly_subject_performances.only(
            'pass_rate', 'highest_score', 'lowest_score', 'average_score', 'median_score', 'standard_deviation', 'percentile_distribution', 'completion_rate', 'top_performers', 'students_failing_the_subject_in_the_term', 'improvement_rate'
        ).get_or_create(term=term, subject=subject, defaults={'school': requesting_account.school})
        serialized_term = TermSubjectPerformanceSerializer(performance).data
        
        # Return the serialized terms in a dictionary
        return {'performance': serialized_term}
    
    except Term.DoesNotExist:
        # Handle the case where the provided term ID does not exist
        return {'error': 'Could not process your request, a term in your school with the provided credentials does not exist, please review the term details and try again.'}
    
    except Subject.DoesNotExist:
        # Handle case where the subject does not exist
        return {'error': 'Could not process your request, a subject in your school with the provided credentials does not exist, please review the subject details and try again.'}

    except Exception as e:
        # Handle any unexpected errors with a general error message
        return {'error': str(e)}


@database_sync_to_async
def search_classroom(account, role, details):
    try:
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = accounts_utilities.get_account_and_linked_school(account, role)

        if role != 'PRINCIPAL' and not permissions_utilities.has_permission(requesting_account, 'VIEW', 'CLASSROOM'):
            response = f'could not proccess your request, you do not have the necessary permissions to view classrooms. please contact your administrator to adjust you permissions for viewing classroom details.'
            audits_utilities.log_audit(actor=requesting_account, action='VIEW', target_model='CLASSROOM', outcome='DENIED', server_response=response, school=requesting_account.school)
            return {'error': response}

        if not 'classroom' in details:
            response = f'could not proccess your request, the provided information is invalid for the action you are trying to perform. please make sure to provide valid classroom ID and try again'
            audits_utilities.log_audit(actor=requesting_account, action='VIEW', target_model='CLASSROOM', outcome='ERROR', server_response=response, school=requesting_account.school)
            return {'error': response}

        # Fetch the specific classroom based on class_id and school
        classroom = requesting_account.school.classrooms.get(classroom_id=details['classroom'])
        serialized_classroom = ClassroomSerializer(classroom).data

        return {"classroom": serialized_classroom}
    
    except Classroom.DoesNotExist:
        # Handle case where the classroom does not exist
        return {'error': _('Could not process your request, a classroom with the provided details does not exist. Please review the classroom details and try again.')}
    
    except Exception as e:
        # Handle any other unexpected errors
        return {'error': str(e)}


@database_sync_to_async
def search_teacher_classrooms(user, role, details):
    try:
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = accounts_utilities.get_account_and_linked_school(user, role)

        if role != 'PRINCIPAL' and not permissions_utilities.has_permission(requesting_account, 'VIEW', 'CLASSROOM'):
            response = f'could not proccess your request, you do not have the necessary permissions to view classrooms. please contact your administrator to adjust you permissions for viewing classrooms.'
            audits_utilities.log_audit(actor=requesting_account, action='VIEW', target_model='CLASSROOM', outcome='DENIED', server_response=response, school=requesting_account.school)
            return {'error': response}

        if 'account' not in details:
            response = f'could not proccess your request, the provided information is invalid for the action you are trying to perform. please make sure to provide a valid account ID and try again'
            audits_utilities.log_audit(actor=requesting_account, action='VIEW', target_model='CLASSROOM', outcome='ERROR', server_response=response, school=requesting_account.school)
            return {'error': response}

        teacher = requesting_account.school.teachers.prefetch_related('taught_classrooms').get(account_id=details['account'])
        serialized_classrooms = TeacherClassroomsSerializer(teacher.taught_classrooms, many=True).data

        return {"classrooms": serialized_classrooms}
               
    except Teacher.DoesNotExist:
        # Handle the case where the requested teacher account does not exist.
        return {'error': 'Could not process your request, a teacher account in your school with the provided credentials does not exist. please review the account details and try again.'}
    
    except Exception as e:
        return { 'error': str(e) }


@database_sync_to_async
def search_assessments(user, role, details):
    try:
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = accounts_utilities.get_account_and_linked_school(user, role)
        
        # Check if the user has permission to create an assessment
        if role != 'PRINCIPAL' and not permissions_utilities.has_permission(requesting_account, 'VIEW', 'ASSESSMENT'):
            response = f'could not proccess your request, you do not have the necessary permissions to view assessments. please contact your principal to adjust you permissions for viewing assessments.'
            audits_utilities.log_audit(actor=requesting_account, action='VIEW', target_model='ASSESSMENTS', outcome='DENIED', server_response=response, school=requesting_account.school)
            return {'error': response}

        status = details.get('status')
        if not status or status not in ['due', 'collected', 'graded']:
            response = f'could not proccess your request, the provided information is invalid for the action you are trying to perform. please make sure to provide a valid assessment status and try again'
            audits_utilities.log_audit(actor=requesting_account, action='VIEW', target_model='SUBJECT', outcome='ERROR', server_response=response, school=requesting_account.school)
            return {'error': response}
        
        # Determine the classroom based on the request details
        if details.get('grade') and details.get('subject'):
            grade = requesting_account.school.grades.get(grade_id=details['grade'])
            subject = grade.subjects.get(subject_id=details['subject'])

            if status == 'due':
                assessments = subject.assessments.filter(collected=False, grades_released=False)
            elif status == 'collected':
                assessments = subject.assessments.filter(collected=True, releasing_grades=False, grades_released=False)
            elif status == 'graded':
                assessments = subject.assessments.filter(models.Q(releasing_grades=True) | models.Q(grades_released=True))

        elif details.get('classroom'):
            # Fetch the specific classroom based on classroom_id and school
            classroom = requesting_account.school.classrooms.get(classroom_id=details['classroom'])

            if status == 'due':
                assessments = classroom.assessments.filter(collected=False, grades_released=False)
            elif status == 'collected':
                assessments = classroom.assessments.filter(collected=True, releasing_grades=False, grades_released=False)
            elif status == 'graded':
                assessments = classroom.assessments.filter(models.Q(releasing_grades=True) | models.Q(grades_released=True))

        else:
            response = f'could not proccess your request, the provided information is invalid for the action you are trying to perform. please make sure to provide valid grade and subject IDs or a valid classroom ID and try again'
            audits_utilities.log_audit(actor=requesting_account, action='VIEW', target_model='ASSESSMENT', outcome='ERROR', server_response=response, school=requesting_account.school)

            return {'error': response}

        if assessments.exists():
            if status == 'due':
                serialized_assessments = DueAssessmentsSerializer(assessments, many=True).data
            elif status == 'collected':
                serialized_assessments = CollectedAssessmentsSerializer(assessments, many=True).data 
            elif status == 'graded':
                serialized_assessments = GradedAssessmentsSerializer(assessments, many=True).data 
        else:
            serialized_assessments = []

        return {"assessments": serialized_assessments}
        
    except Grade.DoesNotExist:
        # Handle the case where the provided grade ID does not exist
        return { 'error': 'Could not process your request, a grade in your school with the provided credentials does not exist. Please review the grade details and try again'}
    
    except Subject.DoesNotExist:
        # Handle case where the subject does not exist
        return {'error': 'Could not process your request, a subject in your school with the provided credentials does not exist. Please review the subject details and try again'}

    except Classroom.DoesNotExist:
        # Handle case where the classroom does not exist
        return {'error': _('Could not process your request, classroom in your school with the provided details does not exist. Please review the classroom details and try again.')}
    
    except Exception as e:
        # Handle any other unexpected errors
        return {'error': str(e)}


@database_sync_to_async
def search_assessment(user, role, details):
    try:
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = accounts_utilities.get_account_and_linked_school(user, role)
        
        # Check if the user has permission to create an assessment
        if role != 'PRINCIPAL' and not permissions_utilities.has_permission(requesting_account, 'VIEW', 'ASSESSMENT'):
            response = f'could not proccess your request, you do not have the necessary permissions to view assessments. please contact your principal to adjust you permissions for viewing assessments.'
            audits_utilities.log_audit(actor=requesting_account, action='VIEW', target_model='ASSESSMENTS', outcome='DENIED', server_response=response, school=requesting_account.school)
            return {'error': response}
        
        if not {'assessment', 'status'}.issubset(details) or details['status'] not in ['due', 'collected', 'graded']:
            response = f'could not proccess your request, the provided information is invalid for the action you are trying to perform. please make sure to provide a valid assessment ID and status and try again.'
            audits_utilities.log_audit(actor=requesting_account, action='VIEW', target_model='ASSESSMENT', outcome='ERROR', server_response=response, school=requesting_account.school)
            return {'error': response}

        status = details['status']
        assessment = requesting_account.school.assessments.get(assessment_id=details['assessment'])

        if status == 'due':
            serialized_assessment = DueAssessmentSerializer(assessment).data
        elif status == 'collected':
            serialized_assessment = CollectedAssessmentSerializer(assessment).data 
        elif status == 'graded':
            serialized_assessment = GradedAssessmentSerializer(assessment).data 

        return {"assessment": serialized_assessment}
        
    except Assessment.DoesNotExist:
        # Handle the case where the provided assessment ID does not exist
        return { 'error': 'Could not process your request, an assessment in your school with the provided credentials does not exist, please review the assessment details and try again.'}
        
    except Exception as e:
        # Handle any other unexpected errors
        return {'error': str(e)}


@database_sync_to_async
def search_transcripts(user, role, details):
    try:
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = accounts_utilities.get_account_and_linked_school(user, role)
        
        # Check if the user has permission to create an assessment
        if role != 'PRINCIPAL' and not permissions_utilities.has_permission(requesting_account, 'VIEW', 'ASSESSMENT'):
            response = f'could not proccess your request, you do not have the necessary permissions to view assessments. please contact your principal to adjust you permissions for viewing assessments.'
            audits_utilities.log_audit(actor=requesting_account, action='VIEW', target_model='ASSESSMENTS', outcome='DENIED', server_response=response, school=requesting_account.school)
            return {'error': response}
        
        if 'assessment' not in details:
            response = f'could not proccess your request, the provided information is invalid for the action you are trying to perform. please make sure to provide a valid assessment ID and try again'
            audits_utilities.log_audit(actor=requesting_account, action='VIEW', target_model='ASSESSMENT', outcome='ERROR', server_response=response, school=requesting_account.school)
            return {'error': response}

        assessment = requesting_account.school.assessments.prefetch_related('scores').get(assessment_id=details['assessment'])
        transcripts = assessment.scores.select_related('student').only('student__surname', 'student__name')

        serialized_transcripts = TranscriptsSerializer(transcripts, many=True).data 

        return {"transcripts": serialized_transcripts}
        
    except Assessment.DoesNotExist:
        # Handle the case where the provided assessment ID does not exist
        return { 'error': 'Could not process your request, an assessment in your school with the provided credentials does not exist, please review the assessment details and try again.'}
        
    except Exception as e:
        # Handle any other unexpected errors
        return {'error': str(e)}


@database_sync_to_async
def search_transcript(user, role, details):
    try:
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = accounts_utilities.get_account_and_linked_school(user, role)
        
        # Check if the user has permission to create an assessment
        if role != 'PRINCIPAL' and not permissions_utilities.has_permission(requesting_account, 'VIEW', 'ASSESSMENT'):
            response = f'could not proccess your request, you do not have the necessary permissions to view assessments. please contact your principal to adjust you permissions for viewing assessments.'
            audits_utilities.log_audit(actor=requesting_account, action='VIEW', target_model='ASSESSMENTS', outcome='DENIED', server_response=response, school=requesting_account.school)
            return {'error': response}
        
        if 'transcript' not in details:
            response = f'could not proccess your request, the provided information is invalid for the action you are trying to perform. please make sure to provide a valid transcript ID and try again'
            audits_utilities.log_audit(actor=requesting_account, action='VIEW', target_model='ASSESSMENT', outcome='ERROR', server_response=response, school=requesting_account.school)
            return {'error': response}

        transcript = requesting_account.transcripts.select_related('student').get(transcript_id=details['transcript'])
        serialized_transcript = TranscriptSerializer(transcript).data 

        return {"transcript": serialized_transcript}
        
    except AssessmentTranscript.DoesNotExist:
        # Handle the case where the provided assessment ID does not exist
        return { 'error': 'Could not process your request, a transcript in your school with the provided credentials does not exist, please review the transcript details and try again.'}
        
    except Exception as e:
        # Handle any other unexpected errors
        return {'error': str(e)}


@database_sync_to_async
def search_student_classroom_card(user, role, details):
    try:
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = accounts_utilities.get_account_and_linked_school(user, role)

        if role != 'PRINCIPAL' and not permissions_utilities.has_permission(requesting_account, 'VIEW', 'ACCOUNT'):
            response = f'could not proccess your request, you do not have the necessary permissions to view classrooms. please contact your administrator to adjust you permissions for viewing classrooms.'
            audits_utilities.log_audit(actor=requesting_account, action='VIEW', target_model='ACCOUNT', outcome='DENIED', server_response=response, school=requesting_account.school)
            return {'error': response}

        if not {'account', 'classroom'}.issubset(details):
            response = f'could not proccess your request, the provided information is invalid for the action you are trying to perform. please make sure to provide valid account and classroom IDs and try again'
            audits_utilities.log_audit(actor=requesting_account, action='VIEW', target_model='ACCOUNT', outcome='ERROR', server_response=response, school=requesting_account.school)
            return {'error': response}

        # Retrieve the requested users account and related school in a single query using select_related
        requested_account = accounts_utilities.get_account_and_permission_check_attr(details['account'], 'STUDENT')

        # Check permissions
        permission_error = permission_checks.view_classroom(requesting_account, requested_account)
        if permission_error:
            return permission_error

        # retrieve the students activities 
        activities = requested_account.my_activities.filter(classroom__classroom_id=details['classroom'])
        
        serialized_student = StudentSourceAccountSerializer(instance=requested_account).data
        serialized_activities = ActivitiesSerializer(activities, many=True).data

        return {"student": serialized_student, 'activities': serialized_activities}

    except Classroom.DoesNotExist:
        # Handle case where the classroom does not exist
        return {'error': 'Could not process your request, a classroom in your school with the provided credentials does not exist. please review the classroom details and try again.'}

    except Exception as e:
        # Handle any other unexpected errors
        return {'error': str(e)}


@database_sync_to_async
def search_activity(user, role, details):
    try:
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = accounts_utilities.get_account_and_linked_school(user, role)

        if role != 'PRINCIPAL' and not permissions_utilities.has_permission(requesting_account, 'VIEW', 'ACTIVITY'):
            response = f'could not proccess your request, you do not have the necessary permissions to view classrooms. please contact your administrator to adjust you permissions for viewing classrooms.'
            audits_utilities.log_audit(actor=requesting_account, action='VIEW', target_model='ACTIVITY', outcome='DENIED', server_response=response, school=requesting_account.school)
            return {'error': response}

        if not {'activity'}.issubset(details):
            response = f'could not proccess your request, the provided information is invalid for the action you are trying to perform. please make sure to provide valid account and classroom IDs and try again'
            audits_utilities.log_audit(actor=requesting_account, action='VIEW', target_model='ACTIVITY', outcome='ERROR', server_response=response, school=requesting_account.school)
            return {'error': response}

        # Retrieve the activity based on the provided activity_id
        activity = requesting_account.school.activities.select_related('school', 'logger', 'recipient', 'classroom').get(activity_id=details['activity'])
        serialized_activity = ActivitySerializer(activity).data

        return {"activity": serialized_activity}

    except StudentActivity.DoesNotExist:
        # Handle case where the activity does not exist
        return {'error': 'Could not process your request, an activity in your school with the provided credentials does not exist. Please review the activity details and try again.'}

    except Exception as e:
        # Handle any other unexpected errors
        return {'error': str(e)}


@database_sync_to_async
def search_teacher_timetable(user, role, details):
    try:
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = accounts_utilities.get_account_and_linked_school(user, role)

        if role != 'PRINCIPAL' and not permissions_utilities.has_permission(requesting_account, 'VIEW', 'TEACHER_TIMETABLE'):
            response = f'could not proccess your request, you do not have the necessary permissions to view teacher timetables. please contact your administrator to adjust you permissions for viewing teacher timetables.'
            audits_utilities.log_audit(actor=requesting_account, action='VIEW', target_model='TEACHER_TIMETABLE', outcome='DENIED', server_response=response, school=requesting_account.school)
            return {'error': response}

        if 'account' not in details:
            response = f'could not proccess your request, the provided information is invalid for the action you are trying to perform. please make sure to provide a valid account ID and try again'
            audits_utilities.log_audit(actor=requesting_account, action='VIEW', target_model='TEACHER_TIMETABLE', outcome='ERROR', server_response=response, school=requesting_account.school)
            return {'error': response}

        teacher = requesting_account.school.teachers.prefetch_related('teacher_timetable__timetables').get(account_id=details['account'])

        # Check if the teacher has a schedule
        if hasattr(teacher, 'teacher_timetable'):
            serialized_timetables = TimetableSerializer(teacher.teacher_timetable.timetables, many=True).data
        else:
            serialized_timetables = []

        return {"timetables": serialized_timetables}
               
    except Teacher.DoesNotExist:
        # Handle the case where the requested teacher account does not exist.
        return {'error': 'Could not process your request, a teacher account in your school with the provided credentials does not exist. Please check the account details and try again.'}
    
    except Exception as e:
        # Handle any other unexpected errors
        return {'error': str(e)}
    

@database_sync_to_async
def search_group_timetables(account, role, details):
    try:
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = accounts_utilities.get_account_and_linked_school(account, role)

        if role != 'PRINCIPAL' and not permissions_utilities.has_permission(requesting_account, 'VIEW', 'GROUP_TIMETABLE'):
            response = f'could not proccess your request, you do not have the necessary permissions to view group timetables. please contact your administrator to adjust you permissions for viewing group timetables.'
            audits_utilities.log_audit(actor=requesting_account, action='VIEW', target_model='GROUP_TIMETABLE', outcome='DENIED', server_response=response, school=requesting_account.school)
            return {'error': response}

        elif 'account' not in details and 'grade' not in details:
            response = f'could not proccess your request, the provided information is invalid for the action you are trying to perform. please make sure to provide a valid account or grade ID and try again'
            audits_utilities.log_audit(actor=requesting_account, action='VIEW', target_model='GROUP_TIMETABLE', outcome='ERROR', server_response=response, school=requesting_account.school)
            return {'error': response}

        if details.get('account'):
            # Retrieve the student
            student = requesting_account.school.students.prefetch_related('timetables').get(account_id=details['account'])
            
            # Retrieve all group schedules associated with the student
            if hasattr(student, 'timetables'):
                group_timetables = student.timetables
            else:
                return {"schedules": []}
            
        else:
            # Retrieve the specified grade
            grade = requesting_account.school.grades.prefetch_related('group_timetables').get(grade_id=details['grade'])
            # Retrieve all group schedules associated with the specified grade
            group_timetables = grade.group_timetables

        # Serialize the group schedules to return them in the response
        serialized_timetables = StudentGroupTimetablesSerializer(group_timetables, many=True).data

        return {"timetables": serialized_timetables}
                       
    except Student.DoesNotExist:
        # Handle the case where the requested student account does not exist.
        return {'error': 'Could not process your request, a student account with the provided credentials does not exist. Please review the account details and try again.'}

    except Grade.DoesNotExist:
        # Handle case where the grade does not exist
        return {'error': 'Could not process your request, a grade in your school with the provided credentials does not exist. Please review the grade details and try again.'}

    except Exception as e:
        # Handle any other unexpected errors
        return {'error': str(e)}


@database_sync_to_async
def search_group_timetable_details(account, role, details):
    try:
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = accounts_utilities.get_account_and_linked_school(account, role)

        if role != 'PRINCIPAL' and not permissions_utilities.has_permission(requesting_account, 'VIEW', 'GROUP_TIMETABLE'):
            response = f'could not proccess your request, you do not have the necessary permissions to view group timetables. please contact your administrator to adjust you permissions for viewing group timetables.'
            audits_utilities.log_audit(actor=requesting_account, action='VIEW', target_model='GROUP_TIMETABLE', outcome='DENIED', server_response=response, school=requesting_account.school)
            return {'error': response}

        elif 'group_timetable' not in details:
            response = f'could not proccess your request, the provided information is invalid for the action you are trying to perform. please make sure to provide a valid group timetable ID and try again'
            audits_utilities.log_audit(actor=requesting_account, action='VIEW', target_model='GROUP_TIMETABLE', outcome='ERROR', server_response=response, school=requesting_account.school)
            return {'error': response}

        # Retrieve the specified group schedule
        group_timetable = requesting_account.school.group_timetables.get(group_timetable_id=details['group_timetable'])
        serialized_group_timetable = StudentGroupTimetableDetailsSerializer(group_timetable).data

        return {"group_timetable": serialized_group_timetable}
    
    except StudentGroupTimetable.DoesNotExist:
        # Handle case where the group schedule does not exist
        return {'error': 'Could not process your request, a group schedule with the provided credentials does not exist. Please check the group schedule details and try again.'}
    
    except Exception as e:
        # Handle any other unexpected errors
        return {'error': str(e)}


@database_sync_to_async
def search_group_timetable_timetables(account, role, details):
    try:
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = accounts_utilities.get_account_and_linked_school(account, role)

        if role != 'PRINCIPAL' and not permissions_utilities.has_permission(requesting_account, 'VIEW', 'GROUP_TIMETABLE'):
            response = f'could not proccess your request, you do not have the necessary permissions to view group timetables. please contact your administrator to adjust you permissions for viewing group timetables.'
            audits_utilities.log_audit(actor=requesting_account, action='VIEW', target_model='GROUP_TIMETABLE', outcome='DENIED', server_response=response, school=requesting_account.school)
            return {'error': response}

        elif 'group_timetable' not in details:
            response = f'could not proccess your request, the provided information is invalid for the action you are trying to perform. please make sure to provide a valid group timetable ID and try again'
            audits_utilities.log_audit(actor=requesting_account, action='VIEW', target_model='GROUP_TIMETABLE', outcome='ERROR', server_response=response, school=requesting_account.school)
            return {'error': response}

        # Retrieve the specified group schedule
        group_timetable = requesting_account.school.group_timetables.prefetch_related('timetables').get(group_timetable_id=details['group_timetable'])
        serialized_timetables = TimetableSerializer(group_timetable.timetables, many=True).data

        return {"timetables": serialized_timetables}
    
    except StudentGroupTimetable.DoesNotExist:
        # Handle case where the group schedule does not exist
        return {'error': 'Could not process your request, a group schedule with the provided credentials does not exist. Please check the group schedule details and try again.'}
    
    except Exception as e:
        # Handle any other unexpected errors
        return {'error': str(e)}


@database_sync_to_async
def search_group_timetable_subscribers(user, role, details):
    try:
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = accounts_utilities.get_account_and_linked_school(user, role)

        if role != 'PRINCIPAL' and not permissions_utilities.has_permission(requesting_account, 'VIEW', 'GROUP_TIMETABLE'):
            response = f'could not proccess your request, you do not have the necessary permissions to view group timetable subscribers. please contact your administrators to adjust you permissions for viewing group schedules.'
            audits_utilities.log_audit(actor=requesting_account, action='VIEW', target_model='GROUP_TIMETABLE', outcome='DENIED', server_response=response, school=requesting_account.school)
            return {'error': response}

        if 'group_timetable' not in details:
            response = f'could not proccess your request, the provided information is invalid for the action you are trying to perform. please make sure to provide a valid group schedule ID and try again'
            audits_utilities.log_audit(actor=requesting_account, action='VIEW', target_model='GROUP_TIMETABLE', outcome='ERROR', server_response=response, school=requesting_account.school)
            return {'error': response}

        # Retrieve the group schedule
        group_schedule = requesting_account.school.group_timetables.prefetch_related('subscribers').get(group_timetable_id=details['group_timetable'])
        serialized_students = StudentSourceAccountSerializer(group_schedule.subscribers, many=True).data

        # Compress the serialized data
        compressed_subscribers = zlib.compress(json.dumps(serialized_students).encode('utf-8'))

        # Encode compressed data as base64 for safe transport
        encoded_subscribers = base64.b64encode(compressed_subscribers).decode('utf-8')

        return {"students": encoded_subscribers}
                
    except StudentGroupTimetable.DoesNotExist:
        # Handle case where the group schedule does not exist
        return {'error': 'Could not process your request, a group schedule with the provided credentials does not exist. Please check the group schedule details and try again.'}

    except Exception as e:
        # Handle any unexpected errors with a general error message
        return {'error': str(e)}
    

@database_sync_to_async
def search_timetable_sessions(user, role, details):
    try:
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = accounts_utilities.get_account_and_linked_school(user, role)

        if role != 'PRINCIPAL' and not permissions_utilities.has_permission(requesting_account, 'VIEW', 'DAILY_SCHEDULE'):
            response = f'could not proccess your request, you do not have the necessary permissions to view timetable sessions. please contact your administrators to adjust you permissions for viewing group schedules.'
            audits_utilities.log_audit(actor=requesting_account, action='VIEW', target_model='DAILY_SCHEDULE', outcome='DENIED', server_response=response, school=requesting_account.school)
            return {'error': response}

        if 'timetable' not in details:
            response = f'could not proccess your request, the provided information is invalid for the action you are trying to perform. please make sure to provide a valid timetable ID and try again'
            audits_utilities.log_audit(actor=requesting_account, action='VIEW', target_model='DAILY_SCHEDULE', outcome='ERROR', server_response=response, school=requesting_account.school)
            return {'error': response}

        schedule = Timetable.objects.prefetch_related('sessions').get(timetable_id=details.get('timetable'))
    
        sessions = schedule.sessions.all()

        serialized_sessions = TimetableSerializer(sessions, many=True).data
        
        return {"sessions": serialized_sessions}
    
    except Timetable.DoesNotExist:
        return {"error" : "a schedule with the provided credentials does not exist"}
    
    except Exception as e:
        return { 'error': str(e) }


@database_sync_to_async
def search_month_attendance_records(user, role, details):
    try:
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = accounts_utilities.get_account_and_linked_school(user, role)
 
        if role != 'PRINCIPAL' and not permissions_utilities.has_permission(requesting_account, 'VIEW', 'ATTENDANCE'):
            response = f'could not proccess your request, you do not have the necessary permissions to view classrooms. please contact your administrator to adjust you permissions for viewing classrooms.'
            audits_utilities.log_audit(actor=requesting_account, action='VIEW', target_model='ATTENDANCE', outcome='DENIED', server_response=response, school=requesting_account.school)

            return {'error': response}

        if not {'month_name', 'classroom'}.issubset(details):
            response = f'could not proccess your request, the provided information is invalid for the action you are trying to perform. please make sure to provide a valid month name and classroom ID and try again'
            audits_utilities.log_audit(actor=requesting_account, action='VIEW', target_model='ATTENDANCE', outcome='ERROR', server_response=response, school=requesting_account.school)

            return {'error': response}

        classroom = requesting_account.school.classrooms.get(classroom_id=details['classroom'], register_class=True)
        
        start_date, end_date = attendances_utilities.get_month_dates(details['month_name'])

        # Query for the Absent instances where absentes is True
        attendances = requesting_account.school.attendances.prefetch_related('absent_students').filter(models.Q(date__gte=start_date) & models.Q(date__lt=end_date) & models.Q(classroom=classroom) & models.Q(absentes=True))

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
