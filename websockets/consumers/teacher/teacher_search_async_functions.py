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
from classrooms.models import Classroom
from school_attendances.models import SchoolAttendance

# serilializers
from accounts.serializers.students.serializers import StudentSourceAccountSerializer, LeastAccountDetailsSerializer
from accounts.serializers.parents.serializers import ParentAccountSerializer
from school_announcements.serializers import AnnouncementSerializer
from classrooms.serializers import TeacherClassesSerializer
from assessments.serializers import DueAssessmentsSerializer, CollectedAssessmentsSerializer
from student_activities.serializers import ActivitiesSerializer
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
def search_parents(account, role, details):
    try:
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = accounts_utilities.get_account_and_linked_school(account, role)

        if not permissions_utilities.has_permission(requesting_account, 'VIEW', 'ACCOUNT'):
            response = f'could not proccess your request, you do not have the necessary permissions to view accounts. please contact your administrator to adjust you permissions for viewing accounts.'
            audits_utilities.log_audit(actor=requesting_account, action='VIEW', target_model='ACCOUNT', outcome='DENIED', server_response=response, school=requesting_account.school)
            return {'error': response}

        if 'account' not in details:
            response = f'could not proccess your request, the provided information is invalid for the action you are trying to perform. please make sure to provide a valid account ID and try again'
            audits_utilities.log_audit(actor=requesting_account, action='VIEW', target_model='ACCOUNT', outcome='ERROR', server_response=response, school=requesting_account.school)
            return {'error': response}

        requested_account = requesting_account.students.prefetch_related('parents').get(account_id=details['account'])
    
        # Check if the requesting user has permission to view the requested user's profile or details.
        permission_error = permission_checks.view_account(requesting_account, requested_account)
        if permission_error:
            # Return an error message if the requesting user does not have the necessary permissions.
            return permission_error

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
def search_account(account, role, details):
    try:
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = accounts_utilities.get_account_and_linked_school(account, role)

        if not permissions_utilities.has_permission(requesting_account, 'VIEW', 'ACCOUNT'):
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

        # Return the serialized user data if everything is successful.
        return {"account": serialized_account}
    
    except Exception as e:
        # Handle any other unexpected errors and return the error message.
        return {'error': str(e)}


@database_sync_to_async
def search_announcement(account, role, details):
    try:
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = accounts_utilities.get_account_and_linked_school(account, role)
        
        if not 'announcement' in details:
            response = f'could not proccess your request, the provided information is invalid for the action you are trying to perform. please make sure to provide a valid announcement ID and try again'
            audits_utilities.log_audit(actor=requesting_account, action='VIEW', target_model='ANNOUNCEMENT', outcome='ERROR', server_response=response, school=requesting_account.school)
            return {'error': response}

        # Retrieve the specified announcement
        announcement = requesting_account.announcements.get(announcement_id=details.get('announcement'))

        # Check if the user is already in the reached list and add if not
        if not announcement.accounts_reached.filter(pk=requesting_account.pk).exists():
            with transaction.atomic():
                announcement.reached(account)

        # Serialize and return the announcement data
        serialized_announcement = AnnouncementSerializer(announcement).data

        return {'announcement': serialized_announcement}
    
    except Exception as e:
        # Handle any other unexpected errors
        return {'error': str(e)}


@database_sync_to_async
def search_assessments(account, details):
    try:
        # Build the queryset for the requesting account with the necessary related fields.
        requesting_account = Teacher.objects.select_related('school').get(account_id=account)
        
        # Check if the user has permission to create an assessment
        if not permissions_utilities.has_permission(requesting_account, 'VIEW', 'ASSESSMENTS'):
            response = f'could not proccess your request, you do not have the necessary permissions to view assessments. please contact your administrators to adjust you permissions for viewing assessments.'
            audits_utilities.log_audit(actor=requesting_account, action='VIEW', target_model='ASSESSMENTS', outcome='DENIED', response=response, school=requesting_account.school)

            return {'error': response}
        
        # Fetch the specific classroom based on classroom_id and school
        classroom = requesting_account.taught_classes.get(classroom_id=details['classroom'])
        assessments = classroom.assessments.filter(collected=details.get('collected'), grades_released=False)
        
        if not assessments:
            return {"assessments": []}

        # Serialize and return the assessments data
        serialized_assessments = CollectedAssessmentsSerializer(assessments, many=True).data if details.get('collected') else DueAssessmentsSerializer(assessments, many=True).data

        return {"assessments": serialized_assessments}

    except Classroom.DoesNotExist:
        # Handle case where the classroom does not exist
        return {'error': _('A classroom in your school with the provided details does not exist. Please check the classroom details and try again.')}
    
    except Exception as e:
        # Handle any other unexpected errors
        return {'error': str(e)}


@database_sync_to_async
def search_month_attendance_records(user, details):
    try:
        # Build the queryset for the requesting account with the necessary related fields.
        requesting_account = Teacher.objects.select_related('school').get(account_id=user)

        classroom = requesting_account.taught_classes.filter(register_class=True).first()
        if not classroom:
            return {"error": _("could not proccess your request. the account making the request has no register class assigned to it")}
        
        start_date, end_date = attendances_utilities.get_month_dates(details.get('month_name'))

        # Query for the Absent instances where absentes is True
        absents = SchoolAttendance.objects.prefetch_related('absent_students').filter(models.Q(date__gte=start_date) & models.Q(date__lt=end_date) & models.Q(classroom=classroom) & models.Q(absentes=True))

        # For each absent instance, get the corresponding Late instance
        attendance_records = []
        for absent in absents:
            late = SchoolAttendance.objects.prefetch_related('late_students').filter(date__date=absent.date.date(), classroom=classroom).first()
            record = {
                'date': absent.date.isoformat(),
                'absent_students': LeastAccountDetailsSerializer(absent.absent_students.all(), many=True).data,
                'late_students': LeastAccountDetailsSerializer(late.late_students.all(), many=True).data if late else [],
            }
            attendance_records.append(record)

        return {'records': attendance_records}
               
    except Teacher.DoesNotExist:
        # Handle the case where the requested teacher account does not exist.
        return {'error': 'A teacher account with the provided credentials does not exist, please check the account details and try again'}
    
    except Classroom.DoesNotExist:
        return { 'error': 'a classroom in your school with the provided credentials does not exist' }

    except Exception as e:
        return { 'error': str(e) }


@database_sync_to_async
def search_teacher_classes(user):
    try:
        requesting_account = Teacher.objects.prefetch_related('taught_classes').get(account_id=user)
        classes = requesting_account.taught_classes.exclude(register_class=True)

        serializer = TeacherClassesSerializer(classes, many=True)

        return {"classes": serializer.data}
               
    except Teacher.DoesNotExist:
        # Handle the case where the requested teacher account does not exist.
        return {'error': 'A teacher account with the provided credentials does not exist, please check the account details and try again'}
    
    except Exception as e:
        return { 'error': str(e) }


@database_sync_to_async
def search_teacher_schedule_schedules(user, role, details):
    try:
        teacher = Teacher.objects.prefetch_related('teacher_schedule__schedules').get(account_id=user)

        # Check if the teacher has a schedule
        if hasattr(teacher, 'teacher_schedule'):
            schedules = teacher.teacher_schedule.schedules.all()

        else:
            return {'schedules': []}
        
        # Serialize the schedules to return them in the response
        serialized_schedules = TimetableSerializer(schedules, many=True).data

        return {"schedules": serialized_schedules}
               
    except Teacher.DoesNotExist:
        # Handle the case where the requested teacher account does not exist.
        return {'error': 'A teacher account with the provided credentials does not exist, please check the account details and try again'}
    
    except Exception as e:
        # Handle any other unexpected errors
        return {'error': str(e)}


@database_sync_to_async
def search_student_class_card(user, role, details):
    try:
        # Retrieve the requesting users account and related attr
        requesting_account = accounts_utilities.get_account_and_attr(user, role)

        # Retrieve the requested users account and related attr
        requested_account = accounts_utilities.get_account_and_attr(user, role)

        # Check permissions
        permission_error = permission_checks.check_profile_or_details_view_permissions(requesting_account, requested_account)
        if permission_error:
            return permission_error
        
        # Determine the classroom based on the request details
        if details.get('class') == 'requesting my own class data':
            # Fetch the classroom where the user is the teacher and it is a register class
            classroom = requesting_account.taught_classes.filter(register_class=True).first()
            if classroom is None:
                return {"error": _("could not proccess your request. the account making the request has no register class assigned to it")}

        else:
            # Fetch the specific classroom based on class_id and school
            classroom = Classroom.objects.get(classroom_id=details.get('classroom'), school=requesting_account.school)

        # retrieve the students activities 
        activities = requested_account.my_activities.filter(classroom=classroom)
        
        serialized_student = StudentSourceAccountSerializer(instance=requested_account).data
        serialized_activities = ActivitiesSerializer(activities, many=True).data

        return {"user": serialized_student, 'activities': serialized_activities}

    except Classroom.DoesNotExist:
        # Handle case where the classroom does not exist
        return {'error': 'a classroom in your school with the provided credentials does not exist. please check the classroom details and try again.'}

    except Exception as e:
        # Handle any other unexpected errors
        return {'error': str(e)}