# python
import base64
import zlib
import json

# channels
from channels.db import database_sync_to_async

# django
from django.utils import timezone
from django.utils.translation import gettext as _

# models 
from accounts.models import Teacher, Student
from classrooms.models import Classroom
from assessments.models import Assessment
from assessment_submissions.models import AssessmentSubmission

# serializers
from accounts.serializers.students.serializers import StudentSourceAccountSerializer
from terms.serializers import FormTermsSerializer
from assessments.serializers import DueAssessmentUpdateFormDataSerializer, CollectedAssessmentUpdateFormDataSerializer
from assessment_transcripts.serializers import TranscriptFormSerializer

# utility functions 
from accounts import utils as accounts_utilities
from account_permissions import utils as permissions_utilities
from audit_logs import utils as audits_utilities


@database_sync_to_async
def form_data_for_classroom_attendance_register(account, role, details):
    try:
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = accounts_utilities.get_account_and_linked_school(account, role)

        # Check if the user has permission to create an assessment
        if role != 'PRINCIPAL' and not permissions_utilities.has_permission(requesting_account, 'SUBMIT', 'ATTENDANCE'):
            response = f'could not proccess your request, you do not have the necessary permissions to submit classroom attendance register. please contact your principal to adjust you permissions for submitting classroom data.'
            audits_utilities.log_audit(actor=requesting_account, action='SUBMIT', target_model='CLASSROOM', outcome='DENIED', server_response=response, school=requesting_account.school)
            return {'error': response}
        
        if not {'classroom'}.issubset(details):
            response = f'could not proccess your request, the provided information is invalid for the action you are trying to perform. please make sure to provide a valid classroom ID and try again'
            audits_utilities.log_audit(actor=requesting_account, action='SUBMIT', target_model='ATTENDANCE', outcome='ERROR', server_response=response, school=requesting_account.school)
            return {'error': response}
        
        classroom = requesting_account.taught_classrooms.get(classroom_id=details['classroom'], register_classroom=True)

        # Get today's date
        today = timezone.now()
            
        # Check if an Absent instance exists for today and the given class
        attendance = classroom.attendances.prefetch_related('absent_students').filter(timestamp__date=today).first()

        if attendance:
            students = attendance.absent_students
            attendance_register_taken = True

        else:
            students = classroom.students
            attendance_register_taken = False

        serialized_students = StudentSourceAccountSerializer(students, many=True).data

        # Compress the serialized data
        compressed_students = zlib.compress(json.dumps(serialized_students).encode('utf-8'))

        # Encode compressed data as base64 for safe transport
        encoded_students = base64.b64encode(compressed_students).decode('utf-8')

        return {"students": encoded_students, "attendance_register_taken" : attendance_register_taken}
            
    except Classroom.DoesNotExist:
        return {'error': 'Could not proccess your request, a classroom in your school with the provided credentials does not exist. Please review the classroom details and try again.'}

    except Exception as e:
        return { 'error': str(e) }


@database_sync_to_async
def form_data_for_setting_assessment(user, details):

    try:
        classroom = None  # Initialize classroom as None to prevent issues in error handling
        requesting_account = Teacher.objects.select_related('school').get(account_id=user)

        # Check if the user has permission to create an assessment
        if not permissions_utilities.has_permission(requesting_account, 'CREATE', 'ASSESSMENT'):
            response = f'could not proccess your request, you do not have the necessary permissions to create assessments.'
            audits_utilities.log_audit(actor=requesting_account, action='CREATE', target_model='ASSESSMENT', outcome='DENIED', response=response, school=requesting_account.school)

            return {'error': response}

        classroom = requesting_account.taught_classrooms.select_related('grade', 'teacher').prefetch_related('grade__terms').filter(classroom_id=details.get('classroom')).first()
        if not classroom:
            response = f'could not proccess your request, you can not set assessments for classrooms that are not assigned to you.'
            audits_utilities.log_audit(actor=requesting_account, action='CREATE', target_model='ASSESSMENT', outcome='DENIED', response=response, school=requesting_account.school)

            return {'error': response}
        
        terms = classroom.grade.terms.all()
        
        serialized_terms = FormTermsSerializer(terms, many=True).data

        return {"terms": serialized_terms}
                   
    except Teacher.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'a teacher account with the provided credentials does not exist, please check your account details and try again'}

    except Exception as e:
        error_message = str(e)
        audits_utilities.log_audit(actor=requesting_account, action='CREATE', target_model='ASSESSMENT', target_object_id=str(classroom.classroom_id) if classroom else 'N/A', outcome='ERROR', response=error_message, school=requesting_account.school)

        return {'error': error_message}


@database_sync_to_async
def form_data_for_updating_assessment(account, role, details):
    try:
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = accounts_utilities.get_account_and_linked_school(account, role)

        # Check if the user has permission to create an assessment
        if not permissions_utilities.has_permission(requesting_account, 'UPDATE', 'ASSESSMENT'):
            response = f'could not proccess your request, you do not have the necessary permissions to update assessments.'
            audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='ASSESSMENT', outcome='DENIED', server_response=response, school=requesting_account.school)

            return {'error': response}
        
        if 'assessment' not in details:
            response = f'could not proccess your request, the provided information is invalid for the action you are trying to perform. please make sure to provide a valid assessment ID and try again'
            audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='ASSESSMENT', outcome='ERROR', server_response=response, school=requesting_account.school)
            return {'error': response}

        if details.get('collected'):
            assessment = requesting_account.school.assessments.select_related('moderator').get(assessment_id=details['assessment'], classroom_id__in=requesting_account.taught_classrooms.values_list('id', flat=True))
            serialized_assessment = CollectedAssessmentUpdateFormDataSerializer(assessment).data

            return {"assessment": serialized_assessment}
        
        else:
            assessment = requesting_account.school.assessments.select_related('grade', 'assessor', 'moderator').prefetch_related('grade__terms').get(assessment_id=details['assessment'], classroom_id__in=requesting_account.taught_classrooms.values_list('id', flat=True))

            terms = assessment.grade.terms
            serialized_terms = FormTermsSerializer(terms, many=True).data

            serialized_assessment = DueAssessmentUpdateFormDataSerializer(assessment).data

            return {"terms": serialized_terms, "assessment": serialized_assessment}
    
    except Assessment.DoesNotExist:
        # Handle the case where the provided grade ID does not exist
        return { 'error': 'an assessment in your school with the provided credentials does not exist, please check the assessment details and try again'}

    except Exception as e:
        # Handle any other unexpected errors
        return {'error': str(e)}


@database_sync_to_async
def form_data_for_collecting_assessment_submissions(account, role, details):
    try:
        # Retrieve the requesting user's account and related school in a single query using select_related
        requesting_account = accounts_utilities.get_account_and_linked_school(account, role)

        # Check if the user has permission to collect assessment submissions
        if not permissions_utilities.has_permission(requesting_account, 'COLLECT', 'ASSESSMENT'):
            response = 'You do not have the necessary permissions to collect assessment submissions.'
            audits_utilities.log_audit(actor=requesting_account, action='COLLECT', target_model='ASSESSMENT', outcome='DENIED', server_response=response, school=requesting_account.school)
            return {'error': response}
        
        if not {'assessment'}.issubset(details):
            response = f'could not proccess your request, the provided information is invalid for the action you are trying to perform. please make sure to provide a valid assessment ID and try again.'
            audits_utilities.log_audit(actor=requesting_account, action='VIEW', target_model='ASSESSMENT', outcome='ERROR', server_response=response, school=requesting_account.school)
            return {'error': response}

        # Fetch the assessment from the requesting user's school
        assessment = requesting_account.taught_classrooms.assessments.select_related('classroom', 'grade').get(assessment_id=details['assessment'])

        # Get the list of students who have already submitted the assessment
        submitted_student_ids = assessment.submissions.values_list('student__id', flat=True)

        # Fetch students in the classroom who haven't submitted
        students = assessment.classroom.students.only('name', 'surname', 'id_number', 'passport_number', 'account_id', 'profile_picture').exclude(id__in=submitted_student_ids)
        
        # Serialize the student data
        serialized_students = StudentSourceAccountSerializer(students, many=True).data

        # Compress the serialized data
        compressed_students = zlib.compress(json.dumps(serialized_students).encode('utf-8'))

        # Encode compressed data as base64 for safe transport
        encoded_students = base64.b64encode(compressed_students).decode('utf-8')

        return {'students': encoded_students}
    
    except Assessment.DoesNotExist:
        # Handle the case where the provided grade ID does not exist
        return { 'error': 'an assessment in your school with the provided credentials does not exist, please check the assessment details and try again'}

    except Exception as e:
        return {'error': str(e)}


@database_sync_to_async
def form_data_for_assessment_submissions(user, role, details):
    try:
        # Retrieve the requesting user's account and related school in a single query using select_related
        requesting_account = accounts_utilities.get_account_and_linked_school(user, role)

        # Check if the user has permission to collect assessment submissions
        if not permissions_utilities.has_permission(requesting_account, 'SUBMIT', 'ASSESSMENT'):
            response = 'You do not have the necessary permissions to collect assessment submissions.'
            audits_utilities.log_audit(actor=requesting_account, action='SUBMIT', target_model='ASSESSMENT', outcome='DENIED', server_response=response, school=requesting_account.school)
            return {'error': response}
        
        if not {'assessment'}.issubset(details):
            response = f'could not proccess your request, the provided information is invalid for the action you are trying to perform. please make sure to provide a valid assessment ID and try again.'
            audits_utilities.log_audit(actor=requesting_account, action='SUBMIT', target_model='ASSESSMENT', outcome='ERROR', server_response=response, school=requesting_account.school)
            return {'error': response}

        # Fetch the assessment from the requesting user's school
        assessment = requesting_account.taught_classrooms.assessments.select_related('classroom', 'grade').get(assessment_id=details['assessment'])

        # Get the list of students who have already submitted the assessment
        submitted_student_ids = assessment.submissions.values_list('student_id', flat=True)

        # Fetch students in the classroom who haven't submitted
        students = assessment.classroom.students.only('name', 'surname', 'id_number', 'passport_number', 'account_id', 'profile_picture').filter(id__in=submitted_student_ids)
        if not students:
            return {'students': []}
        
        # Serialize the student data
        serialized_students = StudentSourceAccountSerializer(students, many=True).data

        # Compress the serialized data
        compressed_students = zlib.compress(json.dumps(serialized_students).encode('utf-8'))

        # Encode compressed data as base64 for safe transport
        encoded_students = base64.b64encode(compressed_students).decode('utf-8')

        return {'students': encoded_students}
    
    except Assessment.DoesNotExist:
        # Handle the case where the provided grade ID does not exist
        return { 'error': 'an assessment in your school with the provided credentials does not exist, please check the assessment details and try again'}

    except Exception as e:
        return {'error': str(e)}


@database_sync_to_async
def form_data_for_assessment_submission_details(account, role, details):
    try:
        # Retrieve the requesting user's account and related school in a single query using select_related
        requesting_account = accounts_utilities.get_account_and_linked_school(account, role)

        # Check if the user has permission to collect assessment submissions
        if not permissions_utilities.has_permission(requesting_account, 'SUBMIT', 'ASSESSMENT'):
            response = 'You do not have the necessary permissions to grade assessment submissions.'
            audits_utilities.log_audit(actor=requesting_account, action='SUBMIT', target_model='ASSESSMENT', outcome='DENIED', server_response=response, school=requesting_account.school)
            return {'error': response}
        
        if not {'student', 'assessment'}.issubset(details):
            response = f'could not proccess your request, the provided information is invalid for the action you are trying to perform. please make sure to provide valid account and assessnt IDs and try again'
            audits_utilities.log_audit(actor=requesting_account, action='SUBMIT', target_model='ASSESSMENT', outcome='ERROR', server_response=response, school=requesting_account.school)
            return {'error': response}
        
        # Fetch the assessment from the requesting user's school
        assessment = requesting_account.taught_classrooms.assessments.get(assessment_id=details['assessment'])

        transcript = assessment.transcripts.select_related('student').filter(student__account_id=details['student']).first()
        if transcript:
            serialized_submission = TranscriptFormSerializer(transcript).data
        else:
            student = requesting_account.taught_classrooms.students.get(account_id=details['student'])
            serialized_submission = {'student': StudentSourceAccountSerializer(student).data, 'total': str(assessment.total)}

        return {'submission': serialized_submission}
    
    except Assessment.DoesNotExist:
        # Handle the case where the provided grade ID does not exist
        return { 'error': 'an assessment in your school with the provided credentials does not exist, please check the assessment details and try again'}

    except Student.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'a student account with the provided credentials does not exist, please check the accounts details and try again'}

    except AssessmentSubmission.DoesNotExist:
        # Handle the case where the provided submission ID does not exist
        return { 'error': 'a submission for the specified assessment in your school with the provided credentials does not exist, please make sure the student has submitted the assessment and try again'}

    except Exception as e:
        return {'error': str(e)}


