# channels
from channels.db import database_sync_to_async

# django
from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils import timezone

# models 
from assessments.models import Assessment
from assessment_transcripts.models import AssessmentTranscript
from topics.models import Topic

# serilializers
from assessments.serializers import AssessmentUpdateSerializer

# utility functions 
from accounts import utils as accounts_utilities
from account_permissions import utils as permissions_utilities
from audit_logs import utils as audits_utilities


@database_sync_to_async
def update_assessment(user, role, details):
    try:
        assessment = None  # Initialize assessment as None to prevent issues in error handling
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = accounts_utilities.get_account_and_linked_school(user, role)

        # Check if the user has permission to create an assessment
        if not permissions_utilities.has_permission(requesting_account, 'UPDATE', 'ASSESSMENT'):
            response = f'could not proccess your request, you do not have the necessary permissions to update assessments.'
            audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='ASSESSMENT', outcome='DENIED', response=response, school=requesting_account.school)

            return {'error': response}
        
        assessment = Assessment.objects.get(assessment_id=details.get('assessment'), school=requesting_account.school)

        # Ensure only authorized users can delete
        if assessment.assessor != requesting_account:
            response = f'could not proccess your request, you do not have the necessary permissions to update assessments that are not assessed by you.'
            audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='ASSESSMENT', outcome='DENIED', response=response, school=requesting_account.school)

            return {'error': response}

        # Serialize the details for assessment creation
        serializer = AssessmentUpdateSerializer(instance=assessment, data=details)
        if serializer.is_valid():
            # Create the assessment within a transaction to ensure atomicity
            with transaction.atomic():
                serializer.save()

                if details.get('topics'):
                    topics = []
                    for name in details['topics']:
                        topic, _ = Topic.objects.get_or_create(name=name)
                        topics.append(topic)

                    assessment.topics.set(topics)
                    
                response = f'assessment {assessment.unique_identifier} has been successfully updated, the new updates will reflect imemdiately to all the students being assessed and their parents'
                audits_utilities.log_audit(actor=user,action='UPDATE', target_model='ASSESSMENT', target_object_id=str(assessment.assessment_id), outcome='UPDATED', response=response, school=assessment.school)

            return {"message": response}

        # Return serializer errors if the data is not valid, format it as a string
        error_response = '; '.join([f"{key}: {', '.join(value)}" for key, value in serializer.errors.items()])
        audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='ASSESSMENT', target_object_id=str(assessment.assessment_id) if assessment else 'N/A', outcome='ERROR', response=f'Validation failed: {error_response}', school=requesting_account.school)

        return {"error": error_response}

    except Assessment.DoesNotExist:
        # Handle the case where the provided assessment ID does not exist
        return {'error': 'an assessment in your school with the provided credentials does not exist, please check the assessment details and try again'}

    except ValidationError as e:
        error_message = e.messages[0].lower() if isinstance(e.messages, list) and e.messages else str(e).lower()
        audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='ASSESSMENT', target_object_id=str(assessment.assessment_id) if assessment else 'N/A', outcome='ERROR', response=error_message, school=requesting_account.school)

        return {"error": error_message}

    except Exception as e:
        error_message = str(e)
        audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='ASSESSMENT', target_object_id=str(assessment.assessment_id) if assessment else 'N/A', outcome='ERROR', response=error_message, school=requesting_account.school)

        return {'error': error_message}


@database_sync_to_async
def collect_assessment(user, role, details):
    try:
        assessment = None  # Initialize assessment as None to prevent issues in error handling
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = accounts_utilities.get_account_and_linked_school(user, role)

        # Check if the user has permission to create an assessment
        if not permissions_utilities.has_permission(requesting_account, 'COLLECT', 'ASSESSMENT'):
            response = f'could not proccess your request, you do not have the necessary permissions to collect assessments.'
            audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='ASSESSMENT', outcome='DENIED', response=response, school=requesting_account.school)

            return {'error': response}

        assessment = Assessment.objects.get(assessment_id=details.get('assessment'), school=requesting_account.school)
        
        # Ensure only authorized users can delete
        if assessment.assessor != requesting_account:
            response = f'could not proccess your request, you do not have the necessary permissions to collect assessments that are not assessed by you.'
            audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='ASSESSMENT', target_object_id=str(assessment.assessment_id) if assessment else 'N/A', outcome='DENIED', response=response, school=requesting_account.school)

            return {'error': response}

        students = assessment.students_assessed.filter(account_id__in=details.get('students'))

        with transaction.atomic():
            assessment.ontime_submission.add(*students)

            response = f"assessment successfully collected from {len(students)} assessed students."
            audits_utilities.log_audit(actor=user,action='UPDATE', target_model='ASSESSMENT', target_object_id=str(assessment.assessment_id) if assessment else 'N/A', outcome='UPDATED', response=response, school=assessment.school)

        return {"message": response}

    except Assessment.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'an assessment in your school with the provided credentials does not exist, please check the assessment details and try again'}

    except ValidationError as e:
        error_message = e.messages[0].lower() if isinstance(e.messages, list) and e.messages else str(e).lower()
        audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='ASSESSMENT', target_object_id=str(assessment.assessment_id) if assessment else 'N/A', outcome='ERROR', response=error_message, school=requesting_account.school)

        return {"error": error_message}

    except Exception as e:
        error_message = str(e)
        audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='ASSESSMENT', target_object_id=str(assessment.assessment_id) if assessment else 'N/A', outcome='ERROR', response=error_message, school=requesting_account.school)

        return {'error': error_message}


@database_sync_to_async
def submit_late_assessment_submitions(user, role, details):
    try:
        assessment = None  # Initialize assessment as None to prevent issues in error handling
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = accounts_utilities.get_account_and_linked_school(user, role)

        # Check if the user has permission to create an assessment
        if not permissions_utilities.has_permission(requesting_account, 'COLLECT', 'ASSESSMENT'):
            response = f'could not proccess your request, you do not have the necessary permissions to collect assessments.'
            audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='ASSESSMENT', outcome='DENIED', response=response, school=requesting_account.school)

            return {'error': response}

        assessment = Assessment.objects.get(assessment_id=details.get('assessment'), school=requesting_account.school)
        
        # Ensure only authorized users can delete
        if role == 'TEACHER' and assessment.assessor != requesting_account:
            response = f'could not proccess your request, you do not have the necessary permissions to collect late assessment submitions that are not assessed by you.'
            audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='ASSESSMENT', target_object_id=str(assessment.assessment_id) if assessment else 'N/A', outcome='DENIED', response=response, school=requesting_account.school)

            return {'error': response}
        
        students = assessment.not_submitted.filter(account_id__in=details.get('students'))

        with transaction.atomic():
            assessment.not_submitted.remove(*students)
            assessment.late_submission.add(*students)

            response = f"assessment late submitions successfully collected from {len(students)} students."
            audits_utilities.log_audit(actor=user,action='UPDATE', target_model='ASSESSMENT', target_object_id=str(assessment.assessment_id) if assessment else 'N/A', outcome='UPDATED', response=response, school=assessment.school)

        return {"message": response}

    except Assessment.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'an assessment in your school with the provided credentials does not exist, please check the assessment details and try again'}

    except ValidationError as e:
        error_message = e.messages[0].lower() if isinstance(e.messages, list) and e.messages else str(e).lower()
        audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='ASSESSMENT', target_object_id=str(assessment.assessment_id) if assessment else 'N/A', outcome='ERROR', response=error_message, school=requesting_account.school)

        return {"error": error_message}

    except Exception as e:
        error_message = str(e)
        audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='ASSESSMENT', target_object_id=str(assessment.assessment_id) if assessment else 'N/A', outcome='ERROR', response=error_message, school=requesting_account.school)

        return {'error': error_message}


@database_sync_to_async
def update_assessment_as_assessed(user, role, details):
    try:
        assessment = None  # Initialize assessment as None to prevent issues in error handling
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = accounts_utilities.get_account_and_linked_school(user, role)

        # Check if the user has permission to create an assessment
        if not permissions_utilities.has_permission(requesting_account, 'UPDATE', 'ASSESSMENT'):
            response = f'could not proccess your request, you do not have the necessary permissions to update assessments.'
            audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='ASSESSMENT', outcome='DENIED', response=response, school=requesting_account.school)

            return {'error': response}

        assessment = Assessment.objects.get(assessment_id=details.get('assessment'), school=requesting_account.school)
        
        # Ensure only authorized users can delete
        if assessment.assessor != requesting_account:
            response = f'could not proccess your request, you do not have the necessary permissions to update assessments that are not assessed by you.'
            audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='ASSESSMENT', target_object_id=str(assessment.assessment_id) if assessment else 'N/A', outcome='DENIED', response=response, school=requesting_account.school)

            return {'error': response}

        with transaction.atomic():
            assessment.assessed = True
            assessment.date_assessed = timezone.now()

            not_submitted_students = assessment.students_assessed.exclude(pk__in=assessment.ontime_submission.all())
            assessment.not_submitted.add(*not_submitted_students)

            assessment.save()

            response = f"assessment {assessment.unique_identifier} has been flagged as collected, and all students that have not submitted their assessments have been flagged as not submitted for the assessment."
            audits_utilities.log_audit(actor=user,action='UPDATE', target_model='ASSESSMENT', target_object_id=str(assessment.assessment_id) if assessment else 'N/A', outcome='UPDATED', response=response, school=assessment.school)

        return {"message": response}

    except Assessment.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'an assessment in your school with the provided credentials does not exist, please check the assessment details and try again'}

    except ValidationError as e:
        error_message = e.messages[0].lower() if isinstance(e.messages, list) and e.messages else str(e).lower()
        audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='ASSESSMENT', target_object_id=str(assessment.assessment_id) if assessment else 'N/A', outcome='ERROR', response=error_message, school=requesting_account.school)

        return {"error": error_message}

    except Exception as e:
        error_message = str(e)
        audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='ASSESSMENT', target_object_id=str(assessment.assessment_id) if assessment else 'N/A', outcome='ERROR', response=error_message, school=requesting_account.school)

        return {'error': error_message}


@database_sync_to_async
def release_assessment_grades(user, role, details):
    try:
        assessment = None  # Initialize assessment as None to prevent issues in error handling
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = accounts_utilities.get_account_and_linked_school(user, role)

        # Check if the user has permission to update assessments
        if not permissions_utilities.has_permission(requesting_account, 'UPDATE', 'ASSESSMENT'):
            response = f'could not proccess your request, you do not have the necessary permissions to update assessments.'
            audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='ASSESSMENT', outcome='DENIED', response=response, school=requesting_account.school)

            return {'error': response}

        assessment = Assessment.objects.get(assessment_id=details.get('assessment'), school=requesting_account.school)
                
        # Ensure only authorized users can delete
        if assessment.assessor != requesting_account:
            response = f'could not proccess your request, you do not have the necessary permissions to update assessments that are not assessed by you.'
            audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='ASSESSMENT', target_object_id=str(assessment.assessment_id) if assessment else 'N/A', outcome='DENIED', response=response, school=requesting_account.school)

            return {'error': response}
        
        not_submitted_students = assessment.not_submitted.all()

        # Create a transcript with a score of 0 for students who didn't submit
        with transaction.atomic():
            assessment.grades_released = True
            assessment.date_grades_released = timezone.now()
            
            for student in not_submitted_students:
                AssessmentTranscript.objects.create(student=student, score=0, assessment=assessment)

            assessment.save()
            
            response = f'Grades released for assessment {assessment.unique_identifier}.'
            audits_utilities.log_audit(actor=user,action='UPDATE', target_model='ASSESSMENT', target_object_id=str(assessment.assessment_id) if assessment else 'N/A', outcome='UPDATED', response=response, school=assessment.school)

        return {"message": response}

    except Assessment.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'an assessment in your school with the provided credentials does not exist, please check the assessment details and try again'}

    except ValidationError as e:
        error_message = e.messages[0].lower() if isinstance(e.messages, list) and e.messages else str(e).lower()
        audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='ASSESSMENT', target_object_id=str(assessment.assessment_id) if assessment else 'N/A', outcome='ERROR', response=error_message, school=requesting_account.school)

        return {"error": error_message}

    except Exception as e:
        error_message = str(e)
        audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='ASSESSMENT', target_object_id=str(assessment.assessment_id) if assessment else 'N/A', outcome='ERROR', response=error_message, school=requesting_account.school)

        return {'error': error_message}
