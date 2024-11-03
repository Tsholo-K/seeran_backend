# channels
from channels.db import database_sync_to_async

# django
from django.db import transaction
from django.core.exceptions import ValidationError


# models 
from accounts.models import BaseAccount, Teacher, Student
from assessments.models import Assessment
from topics.models import Topic
from assessment_transcripts.models import AssessmentTranscript

# serilializers
from assessments.serializers import DueAssessmentUpdateSerializer, CollectAssessmentUpdateSerializer, GradesReleasedAssessmentUpdateSerializer
from assessment_transcripts.serializers import TranscriptUpdateSerializer

# utility functions 
from accounts import utils as accounts_utilities
from account_permissions import utils as permissions_utilities
from audit_logs import utils as audits_utilities

# tasks
from assessments.tasks import release_grades_task


@database_sync_to_async
def grade_student(user, details):
    try:
        assessment = None  # Initialize assessment as None to prevent issues in error handling
        # Retrieve the user and related school in a single query using select_related
        requesting_account = Teacher.objects.select_related('school').get(account_id=user)

        # Check if the user has permission to create an assessment
        if not permissions_utilities.has_permission(requesting_account, 'GRADE', 'ASSESSMENT'):
            response = f'could not proccess your request, you do not have the necessary permissions to grade assessments.'
            audits_utilities.log_audit(actor=requesting_account, action='GRADE', target_model='ASSESSMENT', outcome='DENIED', response=response, school=requesting_account.school)

            return {'error': response}

        assessment = Assessment.objects.select_related('assessor').get(assessment_id=details.get('assessment'), school=requesting_account.school)

        # Ensure only authorized users can delete
        if assessment.assessor != requesting_account:
            response = f'could not proccess your request, you do not have the necessary permissions to grade assessments that are not assessed by you.'
            audits_utilities.log_audit(actor=requesting_account, action='GRADE', target_model='ASSESSMENT', outcome='DENIED', response=response, school=requesting_account.school)

            return {'error': response}
        
        student = Student.objects.get(student_id=details.get('student'))
        
        with transaction.atomic():
            transcript = AssessmentTranscript.objects.create(student=student, score=details.get('student'), assessment=assessment)
            response = f"student graded for assessment {assessment.unique_identifier}."
            audits_utilities.log_audit(actor=requesting_account, action='GRADE', target_model='ASSESSMENT', target_object_id=str(transcript.transcript_id), outcome='GRADED', response=response, school=requesting_account.school,)

        return {"message": response}
               
    except Teacher.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'a teacher account with the provided credentials does not exist, please check your account details and try again'}

    except Student.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'a student account with the provided credentials does not exist, please check the accounts details and try again'}

    except Assessment.DoesNotExist:
        # Handle the case where the provided assessment ID does not exist
        return {'error': 'an assessment in your school with the provided credentials does not exist, please check the assessment details and try again'}

    except ValidationError as e:
        error_message = e.messages[0].lower() if isinstance(e.messages, list) and e.messages else str(e).lower()
        audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='ACCOUNT', target_object_id=str(assessment.assessment_id) if assessment else 'N/A', outcome='ERROR', response=error_message, school=requesting_account.school)

        return {"error": error_message}

    except Exception as e:
        error_message = str(e)
        audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='ACCOUNT', target_object_id=str(assessment.assessment_id) if assessment else 'N/A', outcome='ERROR', response=error_message, school=requesting_account.school)

        return {'error': error_message}
    


@database_sync_to_async
def update_assessment(user, role, details):
    try:
        assessment = None  # Initialize assessment as None to prevent issues in error handling
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = accounts_utilities.get_account_and_linked_school(user, role)

        # Check if the user has permission to update an assessment
        if role != 'PRINCIPAL' and not permissions_utilities.has_permission(requesting_account, 'UPDATE', 'ASSESSMENT'):
            response = f'could not proccess your request, you do not have the necessary permissions to update assessments.'
            audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='ASSESSMENT', outcome='DENIED', server_response=response, school=requesting_account.school)

            return {'error': response}
        
        if 'assessment' not in details:
            response = f'could not proccess your request, the provided information is invalid for the action you are trying to perform. please make sure to provide a valid assessment ID and try again'
            audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='ASSESSMENT', outcome='ERROR', server_response=response, school=requesting_account.school)
            return {'error': response}

        assessment = requesting_account.school.assessments.get(assessment_id=details['assessment'])

        topics = None
        # Serialize the details for assessment creation
        if assessment.grades_released:
            serializer = GradesReleasedAssessmentUpdateSerializer(instance=assessment, data=details)
        else:
            if details.get('moderator'):
                if details['moderator'] == 'remove current moderator':
                    details['moderator'] = None
                else:
                    moderator = BaseAccount.objects.only('id').get(account_id=details['moderator'])
                    details['moderator'] = moderator.id

            if assessment.collected:
                serializer = CollectAssessmentUpdateSerializer(instance=assessment, data=details)
            else:
                serializer = DueAssessmentUpdateSerializer(instance=assessment, data=details)
                if details.get('topics'):
                    for name in details.get('topics'):
                        topic, _ = Topic.objects.get_or_create(name=name)
                        topics.append(topic)

        if serializer.is_valid():
            # Create the assessment within a transaction to ensure atomicity
            with transaction.atomic():
                serializer.save()
                if topics:
                    assessment.topics.set(topics)
                    
                response = f'assessment {assessment.assessment_id} has been successfully updated, the new updates will reflect imemdiately to all the students being assessed and their parents'
                audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='ASSESSMENT', target_object_id=str(assessment.assessment_id), outcome='UPDATED', server_response=response, school=requesting_account.school,)

            return {"message": response}
                
        # Return serializer errors if the data is not valid, format it as a string
        error_response = '; '.join([f"{key}: {', '.join(value)}" for key, value in serializer.errors.items()])
        audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='ASSESSMENT', target_object_id=str(assessment.assessment_id) if assessment else 'N/A', outcome='ERROR', server_response=f'Validation failed: {error_response}', school=requesting_account.school)
        return {"error": error_response}

    except Assessment.DoesNotExist:
        # Handle the case where the provided assessment ID does not exist
        return {'error': 'Could not process your request, an assessment in your school with the provided credentials does not exist, please check the assessment details and try again'}

    except BaseAccount.DoesNotExist:
        # Handle the case where the provided assessment ID does not exist
        return {'error': 'Could not process your request, an account with the provided credentials does not exist. please check the moderators account ID and try again.'}

    except ValidationError as e:
        error_message = e.messages[0].lower() if isinstance(e.messages, list) and e.messages else str(e).lower()
        audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='ASSESSMENT', target_object_id=str(assessment.assessment_id) if assessment else 'N/A', outcome='ERROR', server_response=error_message, school=requesting_account.school)
        return {"error": error_message}

    except Exception as e:
        error_message = str(e)
        audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='ASSESSMENT', target_object_id=str(assessment.assessment_id) if assessment else 'N/A', outcome='ERROR', server_response=error_message, school=requesting_account.school)
        return {'error': error_message}


@database_sync_to_async
def update_student_assessment_transcript(account, role, details):
    try:
        assessment = None  # Initialize assessment as None to prevent issues in error handling
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = accounts_utilities.get_account_and_linked_school(account, role)

        # Check if the user has permission to create an assessment
        if role != 'PRINCIPAL' and not permissions_utilities.has_permission(requesting_account, 'UPDATE', 'TRANSCRPIT'):
            response = f'could not proccess your request, you do not have the necessary permissions to update transcrpits.'
            audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='TRANSCRPIT', outcome='DENIED', response=response, school=requesting_account.school)

            return {'error': response}
                
        if not {'student', 'assessment'}.issubset(details):
            response = f'could not proccess your request, the provided information is invalid for the action you are trying to perform. please make sure to provide valid account and assessment IDs and try again'
            audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='TRANSCRPIT', outcome='ERROR', response=response, school=requesting_account.school)

            return {'error': response}

        # Fetch the assessment from the requesting user's school
        assessment = requesting_account.school.assessments.select_related('assessor','moderator').get(assessment_id=details['assessment'], grades_released=False)
        
        # Check if the user has permission to grade the assessment
        if (assessment.assessor and account != assessment.assessor.account_id) and (assessment.moderator and account != assessment.moderator.account_id):
            response = f'Could not proccess your request, you do not have the necessary permissions to update this transcrpit. only the assessments assessor or moderator can update scores of this transcrpit.'
            audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='TRANSCRPIT', target_object_id=str(assessment.assessment_id) if assessment else 'N/A', outcome='DENIED', response=response, school=requesting_account.school)
            return {'error': response}

        transcript = assessment.transcripts.get(student__account_id=details['student'])

        serializer = TranscriptUpdateSerializer(instance=transcript, data=details)
        if serializer.is_valid():
            with transaction.atomic():
                serializer.save()

                response = f"student graded for assessment {assessment.unique_identifier} has been successfully updated."
                audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='TRANSCRPIT', target_object_id=str(assessment.assessment_id) if assessment else 'N/A', outcome='GRADED', response=response, school=assessment.school)

            return {"message": response}

        error_response = '; '.join([f"{key}: {', '.join(value)}" for key, value in serializer.errors.items()])
        audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='TRANSCRPIT', target_object_id=str(assessment.assessment_id) if assessment else 'N/A', outcome='ERROR', response=f'Validation failed: {error_response}', school=requesting_account.school)
        return {"error": error_response}

    except Assessment.DoesNotExist:
        # Handle the case where the provided assessment ID does not exist
        return {'error': 'an assessment in your school with the provided credentials does not exist, please check the assessment details and try again'}

    except Student.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'a student account with the provided credentials does not exist, please check the accounts details and try again'}

    except ValidationError as e:
        error_message = e.messages[0].lower() if isinstance(e.messages, list) and e.messages else str(e).lower()
        audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='TRANSCRPIT', target_object_id=str(assessment.assessment_id) if assessment else 'N/A', outcome='ERROR', response=error_message, school=requesting_account.school)
        return {"error": error_message}

    except Exception as e:
        error_message = str(e)
        audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='TRANSCRPIT', target_object_id=str(assessment.assessment_id) if assessment else 'N/A', outcome='ERROR', response=error_message, school=requesting_account.school)
        return {'error': error_message}


@database_sync_to_async
def update_assessment_as_collected(user, role, details):
    try:
        assessment = None  # Initialize assessment as None to prevent issues in error handling
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = accounts_utilities.get_account_and_linked_school(user, role)

        # Check if the user has permission to create an assessment
        if role != 'PRINCIPAL' and not permissions_utilities.has_permission(requesting_account, 'UPDATE', 'ASSESSMENT'):
            response = f'could not proccess your request, you do not have the necessary permissions to update assessments.'
            audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='ASSESSMENT', outcome='DENIED', server_response=response, school=requesting_account.school)
            return {'error': response}
        
        if 'assessment' not in details:
            response = f'could not proccess your request, the provided information is invalid for the action you are trying to perform. please make sure to provide a valid assessment ID and try again'
            audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='ASSESSMENT', outcome='ERROR', server_response=response, school=requesting_account.school)
            return {'error': response}

        assessment = requesting_account.school.assessments.get(assessment_id=details['assessment'])
        
        with transaction.atomic():
            assessment.mark_as_collected()

            response = f"An assessment in your school with the following assessment ID: {assessment.assessment_id}, has been successfully flagged as collected. the assessor and moderator (if any) can now grade student submissions. Any submissions collected from here on out will be flagged as late submissions."
            audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='ASSESSMENT', target_object_id=str(assessment.assessment_id), outcome='UPDATED', server_response=response, school=assessment.school)

        return {"message": response}

    except Assessment.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'an assessment in your school with the provided credentials does not exist, please check the assessment details and try again'}

    except ValidationError as e:
        error_message = e.messages[0].lower() if isinstance(e.messages, list) and e.messages else str(e).lower()
        audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='ASSESSMENT', target_object_id=str(assessment.assessment_id) if assessment else 'N/A', outcome='ERROR', server_response=error_message, school=requesting_account.school)
        return {"error": error_message}

    except Exception as e:
        error_message = str(e)
        audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='ASSESSMENT', target_object_id=str(assessment.assessment_id) if assessment else 'N/A', outcome='ERROR', server_response=error_message, school=requesting_account.school)
        return {'error': error_message}


@database_sync_to_async
def update_assessment_as_graded(account, role, details):
    try:
        assessment = None  # Initialize assessment as None to prevent issues in error handling
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = accounts_utilities.get_account_and_linked_school(account, role)

        # Check if the user has permission to create an assessment
        if role != 'PRINCIPAL' and not permissions_utilities.has_permission(requesting_account, 'UPDATE', 'ASSESSMENT'):
            response = f'could not proccess your request, you do not have the necessary permissions to update assessments.'
            audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='ASSESSMENT', outcome='DENIED', server_response=response, school=requesting_account.school)
            return {'error': response}
                
        if 'assessment' not in details:
            response = f'could not proccess your request, the provided information is invalid for the action you are trying to perform. please make sure to provide valid assessment ID and try again'
            audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='ASSESSMENT', outcome='ERROR', server_response=response, school=requesting_account.school)
            return {'error': response}

        # Fetch the assessment from the requesting user's school
        assessment = requesting_account.school.assessments.get(assessment_id=details['assessment'])

        with transaction.atomic():
            # Get the list of students who have already submitted the assessment
            students_who_have_submitted_ids = assessment.submissions.values_list('student_id', flat=True)
            students_who_have_submitted_count = len(students_who_have_submitted_ids)

            graded_student_count = assessment.transcripts.count()

            if students_who_have_submitted_count != graded_student_count:
                response = f"Could not proccess your request, some submissions have not been graded. please make sure to grade all submissions and try again"
                audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='ASSESSMENT', target_object_id=str(assessment.assessment_id), outcome='DENIED', server_response=response, school=assessment.school)
                
                return {'error': response}

            response = f"The grades release process for assessment with assessment ID {assessment.title} has been triggered, results will be made available once performance metrics have been calculated and updated."
            audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='ASSESSMENT', target_object_id=str(assessment.assessment_id), outcome='UPDATED', server_response=response, school=assessment.school)
        
        release_grades_task.delay(assessment.id)

        return {"message": response}

    except Assessment.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'an assessment in your school with the provided credentials does not exist, please check the assessment details and try again'}

    except ValidationError as e:
        error_message = e.messages[0].lower() if isinstance(e.messages, list) and e.messages else str(e).lower()
        audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='ASSESSMENT', target_object_id=str(assessment.assessment_id) if assessment else 'N/A', outcome='ERROR', server_response=error_message, school=requesting_account.school)

        return {"error": error_message}

    except Exception as e:
        error_message = str(e)
        audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='ASSESSMENT', target_object_id=str(assessment.assessment_id) if assessment else 'N/A', outcome='ERROR', server_response=error_message, school=requesting_account.school)

        return {'error': error_message}
