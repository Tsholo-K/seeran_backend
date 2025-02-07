# python
from decimal import Decimal

# channels
from channels.db import database_sync_to_async

# django
from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _

# models 
from accounts.models import BaseAccount, Student
from classrooms.models import Classroom
from school_attendances.models import ClassroomAttendanceRegister
from assessments.models import Assessment

# serilializers
from assessment_transcripts.serializers import TranscriptUpdateSerializer

# utility functions 
from accounts import utils as accounts_utilities
from account_permissions import utils as permissions_utilities
from audit_logs import utils as audits_utilities


@database_sync_to_async
def submit_attendance_register(account, role, details):
    try:
        classroom = None  # Initialize classroom as None to prevent issues in error handling

        requesting_user = BaseAccount.objects.get(account_id=account)
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = accounts_utilities.get_account_and_linked_school(account, role)

        # Check if the user has permission to create an assessment
        if not permissions_utilities.has_permission(requesting_account, 'SUBMIT', 'ATTENDANCE'):
            response = f'could not proccess your request, you do not have the necessary permissions to grade assessments.'
            audits_utilities.log_audit(actor=requesting_account, action='SUBMIT', target_model='ATTENDANCE', outcome='DENIED', server_response=response, school=requesting_account.school)
            return {'error': response}
        
        if not {'classroom'}.issubset(details):
            response = f'could not proccess your request, the provided information is invalid for the action you are trying to perform. please make sure to provide a valid classroom ID and try again'
            audits_utilities.log_audit(actor=requesting_account, action='SUBMIT', target_model='ATTENDANCE', outcome='ERROR', server_response=response, school=requesting_account.school)
            return {'error': response}

        classroom = requesting_account.taught_classrooms.get(classroom_id=details['classroom'], register_classroom=True)
        
        today = timezone.localdate()
        
        with transaction.atomic():
            # Check if an Absent instance exists for today and the given class
            attendance_register, created = classroom.attendances.get_or_create(timestamp__date=today, defaults={'attendance_taker': requesting_user, 'classroom': classroom, 'school': requesting_account.school})
            students = details.get('students', '').split(', ')

            if created:
                if not students or students == ['']:
                    students = None
                absent = True
                response = 'attendance register successfully taken for today'

            else:                    
                if not students or students == ['']:
                    return {'error': 'Could not process your request, no students were provided.'}
                
                absent = False
                response = 'students marked as late, attendance register successfully updated'
            
            attendance_register.update_attendance_register(students=students, absent=absent)
            audits_utilities.log_audit(actor=requesting_account, action='SUBMIT', target_model='ATTENDANCE', target_object_id=str(classroom.classroom_id) if classroom else 'N/A', outcome='SUBMITTED', server_response=response, school=requesting_account.school,)

        return {'message': response}

    except BaseAccount.DoesNotExist:
        # Handle case where the user or teacher account does not exist
        return {'error': 'The account with the provided credentials does not exist. Please check the account details and try again.'}
    
    except Classroom.DoesNotExist:
        return { 'error': 'class with the provided credentials does not exist' }
    
    except ClassroomAttendanceRegister.DoesNotExist:
        return { 'error': 'class with the provided credentials does not exist' }

    except ValidationError as e:
        error_message = e.messages[0].lower() if isinstance(e.messages, list) and e.messages else str(e).lower()
        audits_utilities.log_audit(actor=requesting_account, action='SUBMIT', target_model='ATTENDANCE', target_object_id=str(classroom.classroom_id) if classroom else 'N/A', outcome='ERROR', server_response=error_message, school=requesting_account.school)

        return {"error": error_message}

    except Exception as e:
        error_message = str(e)
        audits_utilities.log_audit(actor=requesting_account, action='SUBMIT', target_model='ATTENDANCE', target_object_id=str(classroom.classroom_id) if classroom else 'N/A', outcome='ERROR', server_response=error_message, school=requesting_account.school)

        return {'error': error_message}


@database_sync_to_async
def submit_assessment_submissions(account, role, details):
    try:
        students = details.get('students', '').split(', ')
        if not students or students == ['']:
            return {'error': 'your request could not be proccessed.. no students were provided'}

        assessment = None  # Initialize assessment as None to prevent issues in error handling
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = accounts_utilities.get_account_and_linked_school(account, role)

        # Check if the user has permission to create an assessment
        if not permissions_utilities.has_permission(requesting_account, 'COLLECT', 'ASSESSMENT'):
            response = f'could not proccess your request, you do not have the necessary permissions to collect assessments.'
            audits_utilities.log_audit(
                actor=requesting_account, 
                action='COLLECT', 
                target_model='ASSESSMENT', 
                outcome='DENIED', 
                server_response=response, 
                school=requesting_account.school
            )
            return {'error': response}
        
        if 'assessment' not in details:
            response = f'could not proccess your request, the provided information is invalid for the action you are trying to perform. please make sure to provide a valid assessment ID and try again'
            audits_utilities.log_audit(
                actor=requesting_account, 
                action='COLLECT', 
                target_model='ASSESSMENT',
                outcome='ERROR', 
                server_response=response, 
                school=requesting_account.school
            )
            return {'error': response}

        assessment = requesting_account.school.assessments.get(assessment_id=details['assessment'])
        
        # Check if the user has permission to grade the assessment
        if (assessment.assessor and account != assessment.assessor.account_id) and (assessment.moderator and account != assessment.moderator.account_id):
            response = f'could not proccess your request, you do not have the necessary permissions to collect this assessment. only the assessments assessor or moderator can collect the assessment.'
            audits_utilities.log_audit(
                actor=requesting_account, 
                action='COLLECT', 
                target_model='ASSESSMENT', 
                target_object_id=str(assessment.assessment_id) if assessment else 'N/A', 
                outcome='DENIED', 
                server_response=response, 
                school=requesting_account.school
            )
            return {'error': response}
        
        with transaction.atomic():
            # Bulk create Submission objects
            assessment.collect_submissions(school=requesting_account.school, students=students)

            response = f"{len(students)} submissions successfully collected from students for an assessment in your school with assessment ID: {assessment.assessment_id}."
            audits_utilities.log_audit(actor=requesting_account, action='COLLECT', target_model='ASSESSMENT', target_object_id=str(assessment.assessment_id), outcome='COLLECTED', server_response=response, school=assessment.school)

        return {"message": response}

    except Assessment.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'could not proccess your request, an assessment in your school with the provided credentials does not exist, please check the assessment details and try again'}

    except ValidationError as e:
        error_message = e.messages[0].lower() if isinstance(e.messages, list) and e.messages else str(e).lower()
        audits_utilities.log_audit(
            actor=requesting_account, 
            action='COLLECT', 
            target_model='ASSESSMENT', 
            target_object_id=str(assessment.assessment_id) if assessment else 'N/A', 
            outcome='ERROR', 
            server_response=error_message, 
            school=requesting_account.school
        )
        return {"error": error_message}

    except Exception as e:
        error_message = str(e)
        audits_utilities.log_audit(
            actor=requesting_account, 
            action='COLLECT', 
            target_model='ASSESSMENT', 
            target_object_id=str(assessment.assessment_id) if assessment else 'N/A', 
            outcome='ERROR', 
            server_response=error_message, 
            school=requesting_account.school
        )
        return {'error': error_message}



@database_sync_to_async
def submit_student_transcript_score(account, role, details):
    try:
        assessment = None  # Initialize assessment as None to prevent issues in error handling
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = accounts_utilities.get_account_and_linked_school(account, role)

        # Check if the user has permission to create an assessment
        if not permissions_utilities.has_permission(requesting_account, 'SUBMIT', 'ASSESSMENT'):
            response = f'could not proccess your request, you do not have the necessary permissions to grade assessments.'
            audits_utilities.log_audit(actor=requesting_account, action='SUBMIT', target_model='ASSESSMENT', outcome='DENIED', server_response=response, school=requesting_account.school)
            return {'error': response}
                
        if not {'student', 'assessment', 'score'}.issubset(details):
            response = f'could not proccess your request, the provided information is invalid for the action you are trying to perform. please make sure to provide a valid transcript score as well as account and assessnt IDs and try again'
            audits_utilities.log_audit(actor=requesting_account, action='SUBMIT', target_model='ACCOUNT', outcome='ERROR', server_response=response, school=requesting_account.school)
            return {'error': response}

        # Fetch the assessment from the requesting user's school
        assessment = requesting_account.school.assessments.select_related('assessor','moderator').get(assessment_id=details['assessment'])
        
        # Check if the user has permission to grade the assessment
        if (assessment.assessor and account != assessment.assessor.account_id) and (assessment.moderator and account != assessment.moderator.account_id):
            response = f'could not proccess your request, you do not have the necessary permissions to grade this assessment. only the assessments assessor or moderator can assign scores to the assessment.'
            audits_utilities.log_audit(
                actor=requesting_account, 
                action='SUBMIT', 
                target_model='ASSESSMENT', 
                target_object_id=str(assessment.assessment_id) if assessment else 'N/A', 
                outcome='DENIED', 
                server_response=response, 
                school=requesting_account.school
            )
            return {'error': response}

        student = requesting_account.school.students.get(account_id=details['student'])

        transcript, created = student.transcripts.get_or_create(assessment=assessment, defaults={'school': requesting_account.school, 'score': Decimal(details['score'])})

        # Initialize the serializer with the prepared data
        serializer = TranscriptUpdateSerializer(transcript, data=details)
        if serializer.is_valid():
            with transaction.atomic():
                serializer.save()

                response = f"student graded for assessment {assessment.assessment_id}."
                audits_utilities.log_audit(actor=requesting_account, action='SUBMIT', target_model='ASSESSMENT', target_object_id=str(assessment.assessment_id) if assessment else 'N/A', outcome='GRADED', server_response=response, school=assessment.school)

            return {"message": response}

        error_response = '; '.join([f"{key}: {', '.join(value)}" for key, value in serializer.errors.items()])
        audits_utilities.log_audit(actor=requesting_account, action='SUBMIT', target_model='ASSESSMENT', target_object_id=str(assessment.assessment_id) if assessment else 'N/A', outcome='ERROR', server_response=f'Validation failed: {error_response}', school=requesting_account.school)
        return {"error": error_response}

    except Assessment.DoesNotExist:
        # Handle the case where the provided assessment ID does not exist
        return {'error': 'could not proccess your request, an assessment in your school with the provided credentials does not exist, please check the assessment details and try again'}

    except Student.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'could not proccess your request, a student account with the provided credentials does not exist, please check the accounts details and try again'}

    except ValidationError as e:
        error_message = e.messages[0].lower() if isinstance(e.messages, list) and e.messages else str(e).lower()
        audits_utilities.log_audit(actor=requesting_account, action='SUBMIT', target_model='ASSESSMENT', target_object_id=str(assessment.assessment_id) if assessment else 'N/A', outcome='ERROR', server_response=error_message, school=requesting_account.school)
        return {"error": error_message}

    except Exception as e:
        error_message = str(e)
        audits_utilities.log_audit(actor=requesting_account, action='SUBMIT', target_model='ASSESSMENT', target_object_id=str(assessment.assessment_id) if assessment else 'N/A', outcome='ERROR', server_response=error_message, school=requesting_account.school)
        return {'error': error_message}