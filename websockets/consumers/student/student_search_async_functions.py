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
from accounts.models import Student
from classrooms.models import Classroom
from terms.models import Term
from assessments.models import Assessment
from assessment_transcripts.models import AssessmentTranscript
from timetables.models import Timetable
from student_activities.models import StudentActivity

# serilializers
from accounts.serializers.students.serializers import StudentBasicAccountDetailsEmailSerializer
from accounts.serializers.parents.serializers import ParentAccountSerializer
from student_subject_performances.serializers import StudentPerformanceSerializer
from school_announcements.serializers import AnnouncementSerializer
from terms.serializers import  TermsSerializer
from classrooms.serializers import ClassroomSerializer
from school_attendances.serializers import ClassroomAttendanceSerializer, StudentAttendanceSerializer
from classroom_performances.serializers import ClassroomPerformanceSerializer
from assessments.serializers import DueAssessmentsSerializer, CollectedAssessmentsSerializer, GradedAssessmentsSerializer, DueAssessmentSerializer, CollectedAssessmentSerializer, GradedAssessmentSerializer
from assessment_transcripts.serializers import TranscriptsSerializer, TranscriptSerializer, DetailedTranscriptSerializer
from timetables.serializers import TimetableSerializer
from student_activities.serializers import ActivitiesSerializer, ActivitySerializer
from timetable_sessions.serializers import SessoinsSerializer

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
def search_grade_terms(account, role, details):
    try:
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = accounts_utilities.get_account_and_linked_school(account, role)

        if not 'classroom' in details:
            response = f'could not proccess your request, the provided information is invalid for the action you are trying to perform. please make sure to provide valid classroom ID and try again'
            return {'error': response}

        # Fetch the specific classroom based on class_id and school
        classroom = requesting_account.enrolled_classrooms.get(classroom_id=details['classroom'])

        # Prefetch related school terms to minimize database hits
        grade_terms = classroom.grade.terms.only('term_name', 'weight', 'start_date', 'end_date', 'term_id')
        serialized_terms = TermsSerializer(grade_terms, many=True).data
        
        # Return the serialized terms in a dictionary
        return {'terms': serialized_terms}

    except Exception as e:
        # Handle any unexpected errors with a general error message
        return {'error': str(e)}


@database_sync_to_async
def search_classroom_subject_performance(account, role, details):
    try:
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = accounts_utilities.get_account_and_linked_school(account, role)

        if not permissions_utilities.has_permission(requesting_account, 'VIEW', 'CLASSROOM'):
            response = f'could not proccess your request, you do not have the necessary permissions to view term performances. please contact your administrator to adjust you permissions for viewing term details.'
            audits_utilities.log_audit(actor=requesting_account, action='VIEW', target_model='CLASSROOM', outcome='DENIED', server_response=response, school=requesting_account.school)
            return {'error': response}

        if not {'term', 'classroom'}.issubset(details):
            response = f'could not proccess your request, the provided information is invalid for the action you are trying to perform. please make sure to provide valid term and classroom IDs and try again'
            audits_utilities.log_audit(actor=requesting_account, action='VIEW', target_model='CLASSROOM', outcome='ERROR', server_response=response, school=requesting_account.school)
            return {'error': response}

        # Fetch the specific classroom based on class_id and school
        classroom = requesting_account.taught_classrooms.get(classroom_id=details['classroom'], register_classroom=False)
        term = classroom.grade.terms.get(term_id=details['term'])

        performance, created = classroom.classroom_performances.only(
            'pass_rate', 'highest_score', 'lowest_score', 'average_score', 'median_score', 'standard_deviation', 'percentile_distribution', 'completion_rate', 'top_performers', 'students_failing_the_classroom', 'improvement_rate'
        ).get_or_create(term=term, defaults={'school': requesting_account.school, 'classroom': classroom})
        serialized_term = ClassroomPerformanceSerializer(performance).data
        
        # Return the serialized terms in a dictionary
        return {'performance': serialized_term}
    
    except Classroom.DoesNotExist:
        # Handle case where the subject does not exist
        return {'error': 'Could not process your request, a classroom in your school with the provided credentials does not exist, please review the classroom details and try again.'}
    
    except Term.DoesNotExist:
        # Handle the case where the provided term ID does not exist
        return {'error': 'Could not process your request, a term in your school with the provided credentials does not exist, please review the term details and try again.'}

    except Exception as e:
        # Handle any unexpected errors with a general error message
        return {'error': str(e)}


@database_sync_to_async
def search_classroom(account, role, details):
    try:
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = accounts_utilities.get_account_and_linked_school(account, role)

        if not 'classroom' in details:
            response = f'could not proccess your request, the provided information is invalid for the action you are trying to perform. please make sure to provide valid classroom ID and try again'
            audits_utilities.log_audit(actor=requesting_account, action='VIEW', target_model='CLASSROOM', outcome='ERROR', server_response=response, school=requesting_account.school)
            return {'error': response}

        # Fetch the specific classroom based on class_id and school
        classroom = requesting_account.enrolled_classrooms.get(classroom_id=details['classroom'])
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
            response = f'could not proccess your request, you do not have the necessary permissions to view classrooms. please contact your administrator to adjust you permissions for viewing classrooms.'
            audits_utilities.log_audit(actor=requesting_account, action='VIEW', target_model='ATTENDANCE', outcome='DENIED', server_response=response, school=requesting_account.school)

            return {'error': response}

        if not {'month_name', 'classroom'}.issubset(details):
            response = f'could not proccess your request, the provided information is invalid for the action you are trying to perform. please make sure to provide a valid month name and classroom ID and try again'
            audits_utilities.log_audit(actor=requesting_account, action='VIEW', target_model='ATTENDANCE', outcome='ERROR', server_response=response, school=requesting_account.school)
            return {'error': response}

        classroom = requesting_account.taught_classrooms.get(classroom_id=details['classroom'], register_classroom=True)
        start_date, end_date = attendances_utilities.get_month_dates(details['month_name'])

        # Query for the Absent instances where absentes is True
        attendances = classroom.attendances.prefetch_related('absent_students', 'late_students').filter(models.Q(timestamp__gte=start_date) & models.Q(timestamp__lt=end_date) & models.Q(absentes=True))

        # For each absent instance, get the corresponding Late instance
        attendance_records = ClassroomAttendanceSerializer(attendances, many=True).data

        # Compress the serialized data
        compressed_attendance_records = zlib.compress(json.dumps(attendance_records).encode('utf-8'))

        # Encode compressed data as base64 for safe transport
        encoded_attendance_records = base64.b64encode(compressed_attendance_records).decode('utf-8')

        return {'records': encoded_attendance_records}
    
    except Classroom.DoesNotExist:
        return {'error': 'a classroom in your school with the provided credentials does not exist. Please check the classrooms details and try again.'}

    except Exception as e:
        return {'error': str(e)}


@database_sync_to_async
def search_student_classroom_performance(account, role, details):
    try:
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = accounts_utilities.get_account_and_linked_school(account, role)

        if not {'term', 'classroom'}.issubset(details):
            response = f'could not proccess your request, the provided information is invalid for the action you are trying to perform. please make sure to provide valid student, term and classroom IDs and try again'
            return {'error': response}

        # Fetch the specific classroom based on class_id and school
        classroom = requesting_account.enrolled_classrooms.get(classroom_id=details['classroom'], register_classroom=False)
        term = classroom.grade.terms.get(term_id=details['term'])

        student_performance, created = requesting_account.subject_performances.only(
            'pass_rate', 'highest_score', 'lowest_score', 'average_score', 'median_score', 'completion_rate', 'mode_score', 'passed'
        ).get_or_create(term=term, subject=classroom.subject, grade=classroom.grade, defaults={'school': requesting_account.school, 'student': requesting_account})
        serialized_student_performance = StudentPerformanceSerializer(student_performance).data
        
        # Return the serialized terms in a dictionary
        return {'performance': serialized_student_performance}
    
    except Classroom.DoesNotExist:
        # Handle case where the subject does not exist
        return {'error': 'Could not process your request, a classroom in your school with the provided credentials does not exist, please review the classroom details and try again.'}
    
    except Term.DoesNotExist:
        # Handle the case where the provided term ID does not exist
        return {'error': 'Could not process your request, a term in your school with the provided credentials does not exist, please review the term details and try again.'}

    except Exception as e:
        # Handle any unexpected errors with a general error message
        return {'error': str(e)}


@database_sync_to_async
def search_student_attendance(account, role):
    try:
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = accounts_utilities.get_account(account, role)

        # Query for the Absent instances where absentes is True
        attendances = []
        attendances.extend(requesting_account.absences.all())
        days_absent = requesting_account.absences.count()
        attendances.extend(requesting_account.late_arrivals.all())

        # Now sort the combined attendances list by 'timestamp'
        sorted_attendances = sorted(attendances, key=lambda attendance: attendance.timestamp, reverse=True)

        # For each absent instance, get the corresponding Late instance
        attendance_records = StudentAttendanceSerializer(sorted_attendances, many=True, context={'student': requesting_account.id}).data

        # Compress the serialized data
        compressed_attendance_records = zlib.compress(json.dumps({'records': attendance_records, 'days_absent': days_absent}).encode('utf-8'))

        # Encode compressed data as base64 for safe transport
        encoded_attendance_records = base64.b64encode(compressed_attendance_records).decode('utf-8')

        return {'records': encoded_attendance_records}
    
    except Classroom.DoesNotExist:
        return {'error': 'Could not process your request, a classroom in your school with the provided credentials does not exist. Please check the classrooms details and try again.'}
                   
    except Student.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'Could not process your request, a student account with the provided credentials does not exist. Please review your account details and try again.'}

    except Exception as e:
        return {'error': str(e)}


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
            assessment = requesting_account.school.assessments.get(
                assessment_id=details['assessment'], 
                classroom_id__in=requesting_account.taught_classrooms.values_list('id', flat=True), 
                collected=False, 
                grades_released=False
            )
            serialized_assessment = DueAssessmentSerializer(assessment).data
        elif status == 'collected':
            assessment = requesting_account.school.assessments.get(
                assessment_id=details['assessment'], 
                classroom_id__in=requesting_account.taught_classrooms.values_list('id', flat=True), 
                collected=True, 
                releasing_grades=False, 
                grades_released=False
            )
            serialized_assessment = CollectedAssessmentSerializer(assessment).data 
        elif status == 'graded':
            assessment = requesting_account.school.assessments.get(
                models.Q(releasing_grades=True) | models.Q(grades_released=True), 
                assessment_id=details['assessment'], 
                classroom_id__in=requesting_account.taught_classrooms.values_list('id', flat=True)
            )
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

        assessment = requesting_account.school.assessments.prefetch_related('transcripts').get(assessment_id=details['assessment'], classroom_id__in=requesting_account.taught_classrooms.values_list('id', flat=True))
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
def search_student_assessment_transcript(account, role, details):
    try:
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = accounts_utilities.get_account_and_permission_check_attr(account, role)

        if not {'term', 'classroom', 'assessment'}.issubset(details):
            response = f'could not proccess your request, the provided information is invalid for the action you are trying to perform. please make sure to provide valid term, classroom and assessment IDs and try again'
            return {'error': response}

        classroom = requesting_account.taught_classrooms.get(classroom_id=details['classroom'])

        assessment = requesting_account.school.assessments.get(models.Q(releasing_grades=True) | models.Q(grades_released=True), term__term_id=details['term'], assessment_id=details['assessment'], subject=classroom.subject, grade=classroom.grade,)
        transcript = assessment.transcripts.get(student=requesting_account)

        serialized_transcript = DetailedTranscriptSerializer(transcript).data 

        return {"transcript": serialized_transcript}

    except Classroom.DoesNotExist:
        # Handle case where the classroom does not exist
        return {'error': _('Could not process your request, classroom in your school with the provided details does not exist. Please review the classroom details and try again.')}

    except AssessmentTranscript.DoesNotExist:
        # Handle the case where the provided assessment ID does not exist
        return { 'error': 'Could not process your request, a transcript in your school with the provided credentials does not exist, please review the transcript details and try again.'}
        
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

        transcript = requesting_account.school.transcripts.select_related('student').get(transcript_id=details['transcript'], assessment__classroom_id__in=requesting_account.taught_classrooms.values_list('id', flat=True))
        serialized_transcript = TranscriptSerializer(transcript).data 

        return {"transcript": serialized_transcript}
        
    except AssessmentTranscript.DoesNotExist:
        # Handle the case where the provided assessment ID does not exist
        return { 'error': 'Could not process your request, a transcript in your school with the provided credentials does not exist, please review the transcript details and try again.'}
        
    except Exception as e:
        # Handle any other unexpected errors
        return {'error': str(e)}


@database_sync_to_async
def search_student_classroom_card(account, role, details):
    try:
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = accounts_utilities.get_account_and_linked_school(account, role)

        if not {'classroom'}.issubset(details):
            response = f'could not proccess your request, the provided information is invalid for the action you are trying to perform. please make sure to provide valid account and classroom IDs and try again'
            audits_utilities.log_audit(actor=requesting_account, action='VIEW', target_model='ACCOUNT', outcome='ERROR', server_response=response, school=requesting_account.school)
            return {'error': response}

        classroom = requesting_account.enrolled_classrooms.get(classroom_id=details['classroom'])

        # retrieve the students activities 
        activities = requesting_account.my_activities.filter(classroom=classroom)
        
        serialized_student = StudentBasicAccountDetailsEmailSerializer(instance=requesting_account).data
        serialized_activities = ActivitiesSerializer(activities, many=True).data

        return {"student": serialized_student, 'activities': serialized_activities}

    except Classroom.DoesNotExist:
        # Handle case where the classroom does not exist
        return {'error': 'Could not process your request, a classroom in your school with the provided credentials does not exist. please review the classroom details and try again.'}

    except Exception as e:
        # Handle any other unexpected errors
        return {'error': str(e)}



@database_sync_to_async
def search_student_activity(account, role, details):
    try:
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = accounts_utilities.get_account_and_linked_school(account, role)

        if not {'activity'}.issubset(details):
            response = f'could not proccess your request, the provided information is invalid for the action you are trying to perform. please make sure to provide valid account and classroom IDs and try again'
            audits_utilities.log_audit(actor=requesting_account, action='VIEW', target_model='ACTIVITY', outcome='ERROR', server_response=response, school=requesting_account.school)
            return {'error': response}

        # Retrieve the activity based on the provided activity_id
        activity = requesting_account.my_activities.select_related('auditor', 'recipient', 'classroom', 'school').get(student_activity_id=details['activity'])
        serialized_activity = ActivitySerializer(activity).data

        return {"activity": serialized_activity}

    except StudentActivity.DoesNotExist:
        # Handle case where the activity does not exist
        return {'error': 'Could not process your request, an activity in your school with the provided credentials does not exist. Please review the activity details and try again.'}

    except Exception as e:
        # Handle any other unexpected errors
        return {'error': str(e)}



@database_sync_to_async
def search_teacher_timetables(account, role):
    try:
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = accounts_utilities.get_account_and_linked_school(account, role)

        if not permissions_utilities.has_permission(requesting_account, 'VIEW', 'TEACHER_TIMETABLE'):
            response = f'could not proccess your request, you do not have the necessary permissions to view teacher timetables. please contact your administrator to adjust you permissions for viewing teacher timetables.'
            audits_utilities.log_audit(actor=requesting_account, action='VIEW', target_model='TEACHER_TIMETABLE', outcome='DENIED', server_response=response, school=requesting_account.school)
            return {'error': response}

        # Check if the teacher has a schedule
        if hasattr(requesting_account, 'teacher_timetable'):
            serialized_timetables = TimetableSerializer(requesting_account.teacher_timetable.timetables, many=True).data
        else:
            serialized_timetables = []

        return {"timetables": serialized_timetables}
    
    except Exception as e:
        # Handle any other unexpected errors
        return {'error': str(e)}


@database_sync_to_async
def search_timetable_sessions(account, role, details):
    try:
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = accounts_utilities.get_account_and_linked_school(account, role)

        if not permissions_utilities.has_permission(requesting_account, 'VIEW', 'TIMETABLE'):
            response = f'could not proccess your request, you do not have the necessary permissions to view timetable sessions. please contact your administrators to adjust you permissions for viewing group schedules.'
            audits_utilities.log_audit(actor=requesting_account, action='VIEW', target_model='TIMETABLE', outcome='DENIED', server_response=response, school=requesting_account.school)
            return {'error': response}

        if 'timetable' not in details:
            response = f'could not proccess your request, the provided information is invalid for the action you are trying to perform. please make sure to provide a valid timetable ID and try again'
            audits_utilities.log_audit(actor=requesting_account, action='VIEW', target_model='TIMETABLE', outcome='ERROR', server_response=response, school=requesting_account.school)
            return {'error': response}

        timetable = requesting_account.teacher_timetable.timetables.prefetch_related('sessions').get(timetable_id=details['timetable'])
        serialized_sessions = SessoinsSerializer(timetable.sessions, many=True).data
        
        return {"sessions": serialized_sessions}
    
    except Timetable.DoesNotExist:
        return {"error" : "a schedule with the provided credentials does not exist"}
    
    except Exception as e:
        return { 'error': str(e) }


