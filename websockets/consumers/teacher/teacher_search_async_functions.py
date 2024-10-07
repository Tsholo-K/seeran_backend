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
from school_attendances.models import ClassroomAttendanceRegister
from assessments.models import Assessment
from assessment_transcripts.models import AssessmentTranscript

# serilializers
from accounts.serializers.students.serializers import StudentSourceAccountSerializer, LeastAccountDetailsSerializer
from accounts.serializers.parents.serializers import ParentAccountSerializer
from school_announcements.serializers import AnnouncementSerializer
from classrooms.serializers import ClassroomSerializer
from assessments.serializers import DueAssessmentsSerializer, CollectedAssessmentsSerializer, GradedAssessmentsSerializer, DueAssessmentSerializer, CollectedAssessmentSerializer, GradedAssessmentSerializer
from assessment_transcripts.serializers import TranscriptsSerializer, TranscriptSerializer
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

        requested_account = requesting_account.school.students.select_related('school').prefetch_related('parents').get(account_id=details['account'])
    
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
        if details['reason'] == 'profile':
            # Get the appropriate serializer for the requested user's role.
            Serializer = serializer_mappings.account_profile[details['role']]
            # Serialize the requested user's details and return the serialized data.
            serialized_account = Serializer(instance=requested_account).data

        else:
            # Get the appropriate serializer for the requested user's role.
            Serializer = serializer_mappings.account_details[details['role']]
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
def search_school_announcement(account, role, details):
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
        if not announcement.accounts_reached.filter(id=requesting_account.id).exists():
            with transaction.atomic():
                announcement.reached(account)

        # Serialize and return the announcement data
        serialized_announcement = AnnouncementSerializer(announcement).data

        return {'announcement': serialized_announcement}
    
    except Exception as e:
        # Handle any other unexpected errors
        return {'error': str(e)}


@database_sync_to_async
def search_classroom(account, role, details):
    try:
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = accounts_utilities.get_account_and_linked_school(account, role)

        if not permissions_utilities.has_permission(requesting_account, 'VIEW', 'CLASSROOM'):
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
def search_month_attendance_records(account, role, details):
    try:
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = accounts_utilities.get_account_and_linked_school(account, role)

        if not permissions_utilities.has_permission(requesting_account, 'VIEW', 'ATTENDANCE'):
            response = f'could not proccess your request, you do not have the necessary permissions to view attendances. please contact your administrator to adjust you permissions for viewing attendance details.'
            audits_utilities.log_audit(actor=requesting_account, action='VIEW', target_model='ATTENDANCE', outcome='DENIED', server_response=response, school=requesting_account.school)
            return {'error': response}

        if not 'classroom' in details:
            response = f'could not proccess your request, the provided information is invalid for the action you are trying to perform. please make sure to provide valid classroom ID and try again'
            audits_utilities.log_audit(actor=requesting_account, action='VIEW', target_model='ATTENDANCE', outcome='ERROR', server_response=response, school=requesting_account.school)
            return {'error': response}

        # Fetch the specific classroom based on class_id and school
        classroom = requesting_account.taught_classrooms.filter(register_class=True).first()
        if not classroom:
            return {"error": _("could not proccess your request, you don\'t seem to be assigned a register classroom")}
        
        start_date, end_date = attendances_utilities.get_month_dates(details.get('month_name'))

        # Query for the Absent instances where absentes is True
        absents = ClassroomAttendanceRegister.objects.prefetch_related('absent_students').filter(models.Q(date__gte=start_date) & models.Q(date__lt=end_date) & models.Q(classroom=classroom) & models.Q(absentes=True))

        # For each absent instance, get the corresponding Late instance
        attendance_records = []
        for absent in absents:
            late = ClassroomAttendanceRegister.objects.prefetch_related('late_students').filter(date__date=absent.date.date(), classroom=classroom).first()
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
def search_assessments(account, role, details):
    try:
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = accounts_utilities.get_account_and_linked_school(account, role)
        
        # Check if the user has permission to create an assessment
        if not permissions_utilities.has_permission(requesting_account, 'VIEW', 'ASSESSMENT'):
            response = f'could not proccess your request, you do not have the necessary permissions to view assessments. please contact your principal to adjust you permissions for viewing assessments.'
            audits_utilities.log_audit(actor=requesting_account, action='VIEW', target_model='ASSESSMENTS', outcome='DENIED', server_response=response, school=requesting_account.school)
            return {'error': response}

        if not {'classroom', 'status'}.issubset(details) or details['status'] not in ['due', 'collected', 'graded']:
            response = f'could not proccess your request, the provided information is invalid for the action you are trying to perform. please make sure to provide a valid assessment ID and status and try again'
            audits_utilities.log_audit(actor=requesting_account, action='VIEW', target_model='SUBJECT', outcome='ERROR', server_response=response, school=requesting_account.school)
            return {'error': response}
        
        status = details.get('status')
        # Fetch the specific classroom based on classroom_id and school
        classroom = requesting_account.taught_classrooms.get(classroom_id=details['classroom'])

        if status == 'due':
            assessments = classroom.assessments.filter(collected=False, grades_released=False)
        elif status == 'collected':
            assessments = classroom.assessments.filter(collected=True, releasing_grades=False, grades_released=False)
        elif status == 'graded':
            assessments = classroom.assessments.filter(models.Q(releasing_grades=True) | models.Q(grades_released=True))

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

    except Classroom.DoesNotExist:
        # Handle case where the classroom does not exist
        return {'error': _('Could not process your request, classroom in your school with the provided details does not exist. Please review the classroom details and try again.')}
    
    except Exception as e:
        # Handle any other unexpected errors
        return {'error': str(e)}


@database_sync_to_async
def search_assessment(account, role, details):
    try:
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = accounts_utilities.get_account_and_linked_school(account, role)
        
        # Check if the user has permission to create an assessment
        if not permissions_utilities.has_permission(requesting_account, 'VIEW', 'ASSESSMENT'):
            response = f'could not proccess your request, you do not have the necessary permissions to view assessments. please contact your principal to adjust you permissions for viewing assessments.'
            audits_utilities.log_audit(actor=requesting_account, action='VIEW', target_model='ASSESSMENTS', outcome='DENIED', server_response=response, school=requesting_account.school)
            return {'error': response}
        
        if not {'assessment', 'status'}.issubset(details) or details['status'] not in ['due', 'collected', 'graded']:
            response = f'could not proccess your request, the provided information is invalid for the action you are trying to perform. please make sure to provide a valid assessment ID and status and try again.'
            audits_utilities.log_audit(actor=requesting_account, action='VIEW', target_model='ASSESSMENT', outcome='ERROR', server_response=response, school=requesting_account.school)
            return {'error': response}

        status = details['status']

        if status == 'due':
            assessment = requesting_account.school.assessments.get(assessment_id=details['assessment'], collected=False, grades_released=False)
        elif status == 'collected':
            assessment = requesting_account.school.assessments.get(assessment_id=details['assessment'], collected=True, releasing_grades=False, grades_released=False)
        elif status == 'graded':
            assessment = requesting_account.school.assessments.get(models.Q(releasing_grades=True) | models.Q(grades_released=True), assessment_id=details['assessment'])

        if not requesting_account.taught_classrooms.filter(id=assessment.classroom):
            response = f'Could not process your request, you do not have the necessary permissions to view this assessments. You can not view assessement you do not assess or moderate.'
            audits_utilities.log_audit(actor=requesting_account, action='VIEW', target_model='ASSESSMENT', outcome='DENIED', server_response=response, school=requesting_account.school)
            return {'error': response}

        if status == 'due':
            serialized_assessment = DueAssessmentSerializer(assessment).data
        elif status == 'collected':
            serialized_assessment = CollectedAssessmentSerializer(assessment).data 
        elif status == 'graded':
            serialized_assessment = GradedAssessmentSerializer(assessment).data 

        return {"assessment": serialized_assessment}
        
    except Assessment.DoesNotExist:
        # Handle the case where the provided assessment ID does not exist
        return { 'error': 'Could not process your request, an assessment in any of your classrooms with the provided credentials does not exist, please review the assessment details and try again.'}
        
    except Exception as e:
        # Handle any other unexpected errors
        return {'error': str(e)}


@database_sync_to_async
def search_transcripts(account, role, details):
    try:
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = accounts_utilities.get_account_and_linked_school(account, role)
        
        # Check if the user has permission to create an assessment
        if not permissions_utilities.has_permission(requesting_account, 'VIEW', 'ASSESSMENT'):
            response = f'could not proccess your request, you do not have the necessary permissions to view assessments. please contact your principal to adjust you permissions for viewing assessments.'
            audits_utilities.log_audit(actor=requesting_account, action='VIEW', target_model='ASSESSMENTS', outcome='DENIED', server_response=response, school=requesting_account.school)
            return {'error': response}
        
        if 'assessment' not in details:
            response = f'could not proccess your request, the provided information is invalid for the action you are trying to perform. please make sure to provide a valid assessment ID and try again'
            audits_utilities.log_audit(actor=requesting_account, action='VIEW', target_model='ASSESSMENT', outcome='ERROR', server_response=response, school=requesting_account.school)
            return {'error': response}

        assessment = requesting_account.taught_classrooms.assessments.prefetch_related('transcripts').get(assessment_id=details['assessment'])
        transcripts = assessment.transcripts.select_related('student').only('student__surname', 'student__name')

        serialized_transcripts = TranscriptsSerializer(transcripts, many=True).data 

        return {"transcripts": serialized_transcripts}
        
    except Assessment.DoesNotExist:
        # Handle the case where the provided assessment ID does not exist
        return { 'error': 'Could not process your request, an assessment in your school with the provided credentials does not exist, please review the assessment details and try again.'}
        
    except Exception as e:
        # Handle any other unexpected errors
        return {'error': str(e)}


@database_sync_to_async
def search_transcript(account, role, details):
    try:
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = accounts_utilities.get_account_and_linked_school(account, role)
        
        # Check if the user has permission to create an assessment
        if not permissions_utilities.has_permission(requesting_account, 'VIEW', 'ASSESSMENT'):
            response = f'could not proccess your request, you do not have the necessary permissions to view assessments. please contact your principal to adjust you permissions for viewing assessments.'
            audits_utilities.log_audit(actor=requesting_account, action='VIEW', target_model='ASSESSMENTS', outcome='DENIED', server_response=response, school=requesting_account.school)
            return {'error': response}
        
        if 'transcript' not in details:
            response = f'could not proccess your request, the provided information is invalid for the action you are trying to perform. please make sure to provide a valid transcript ID and try again'
            audits_utilities.log_audit(actor=requesting_account, action='VIEW', target_model='ASSESSMENT', outcome='ERROR', server_response=response, school=requesting_account.school)
            return {'error': response}

        transcript = requesting_account.taught_classrooms.assessments.transcripts.select_related('student').get(transcript_id=details['transcript'])
        serialized_transcript = TranscriptSerializer(transcript).data 

        return {"transcript": serialized_transcript}
        
    except AssessmentTranscript.DoesNotExist:
        # Handle the case where the provided assessment ID does not exist
        return { 'error': 'Could not process your request, a transcript in your school with the provided credentials does not exist, please review the transcript details and try again.'}
        
    except Exception as e:
        # Handle any other unexpected errors
        return {'error': str(e)}


@database_sync_to_async
def search_student_class_card(account, role, details):
    try:
        # Retrieve the requesting users account and related attr
        requesting_account = accounts_utilities.get_account_and_attr(account, role)

        # Retrieve the requested users account and related attr
        requested_account = accounts_utilities.get_account_and_attr(account, role)

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