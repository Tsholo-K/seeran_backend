# channels
from channels.db import database_sync_to_async

# django
from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _

# models 
from accounts.models import Teacher, Student
from assessments.models import Assessment
from topics.models import Topic
from student_activities.models import StudentActivity

# serilializers
from assessments.serializers import AssessmentCreationSerializer
from student_activities.serializers import ActivityCreationSerializer

# utility functions 
from accounts import utils as accounts_utilities
from account_permissions import utils as permissions_utilities
from audit_logs import utils as audits_utilities


@database_sync_to_async
def set_assessment(user, details):
    try:
        assessment = None  # Initialize assessment as None to prevent issues in error handling
        # Retrieve the user and related school in a single query using select_related
        requesting_account = Teacher.objects.select_related('school').get(account_id=user)

        # Check if the user has permission to create an assessment
        if not permissions_utilities.has_permission(requesting_account, 'CREATE', 'ASSESSMENT'):
            response = f'could not proccess your request, you do not have the necessary permissions to create assessments.'
            audits_utilities.log_audit(actor=requesting_account, action='CREATE', target_model='ASSESSMENT', outcome='DENIED', response=response, school=requesting_account.school)

            return {'error': response}

        classroom = requesting_account.taught_classes.select_related('grade', 'subject').prefetch_related('grade__terms').filter(classroom_id=details.get('classroom')).first()
        term = classroom.grade.terms.filter(term_id=details.get('term')).first()
        subject = classroom.subject.pk
        
        if not classroom:
            response = "the provided classroom is either not assigned to you or does not exist. please check the classroom details and try again"
            audits_utilities.log_audit(actor=requesting_account, action='CREATE', target_model='ASSESSMENT', outcome='DENIED', response=response, school=requesting_account.school)

            return {'error': response}
        
        elif not term:
            response = "a term for your school with the provided credentials does not exist. please check the term details and try again"
            audits_utilities.log_audit(actor=requesting_account, action='CREATE', target_model='ASSESSMENT', outcome='ERROR', response=response, school=requesting_account.school)

            return {'error': response}
        
        elif not subject:
            response = "a subject for your school with the provided credentials does not exist. please check the subject details and try again"
            audits_utilities.log_audit(actor=requesting_account, action='CREATE', target_model='ASSESSMENT', outcome='ERROR', response=response, school=requesting_account.school)

            return {'error': response}

        details['classroom'] = classroom.pk
        details['grade'] = classroom.grade.pk
        details['assessor'] = requesting_account.pk
        details['school'] = requesting_account.school.pk
        details['term'] = term.pk
        details['subject'] = subject.pk

        # Serialize the details for assessment creation
        serializer = AssessmentCreationSerializer(data=details)
        if serializer.is_valid():
            # Create the assessment within a transaction to ensure atomicity
            with transaction.atomic():
                assessment = Assessment.objects.create(**serializer.validated_data)

                if details.get('topics'):
                    topics = []
                    for name in details['topics']:
                        topic, _ = Topic.objects.get_or_create(name=name)
                        topics.append(topic)

                    assessment.topics.set(topics)
                    
                response = f'assessment {assessment.unique_identifier} has been successfully created, and will become accessible to all the students being assessed and their parents'
                audits_utilities.log_audit(actor=requesting_account, action='CREATE', target_model='ASSESSMENT', target_object_id=str(assessment.assessment_id), outcome='CREATED', response=response, school=requesting_account.school,)

            return {"message": response}
        
        # Return serializer errors if the data is not valid, format it as a string
        error_response = '; '.join([f"{key}: {', '.join(value)}" for key, value in serializer.errors.items()])
        audits_utilities.log_audit(actor=requesting_account, action='CREATE', target_model='ASSESSMENT', target_object_id=str(assessment.assessment_id) if assessment else 'N/A', outcome='ERROR', response=f'Validation failed: {error_response}', school=requesting_account.school)

        return {"error": error_response}
                   
    except Teacher.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'a teacher account with the provided credentials does not exist, please check your account details and try again'}

    except ValidationError as e:
        error_message = e.messages[0].lower() if isinstance(e.messages, list) and e.messages else str(e).lower()
        audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='ACCOUNT', target_object_id=str(assessment.assessment_id) if assessment else 'N/A', outcome='ERROR', response=error_message, school=requesting_account.school)

        return {"error": error_message}

    except Exception as e:
        error_message = str(e)
        audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='ACCOUNT', target_object_id=str(assessment.assessment_id) if assessment else 'N/A', outcome='ERROR', response=error_message, school=requesting_account.school)

        return {'error': error_message}


@database_sync_to_async
def delete_assessment(user, details):
    try:
        assessment = None  # Initialize assessment as None to prevent issues in error handling

        # Retrieve the user and related school in a single query using select_related
        requesting_account = Teacher.objects.select_related('school').get(account_id=user)

        # Check if the user has permission to create an assessment
        if not permissions_utilities.has_permission(requesting_account, 'DELETE', 'ASSESSMENT'):
            response = f'could not proccess your request, you do not have the necessary permissions to delete assessments.'
            audits_utilities.log_audit(actor=requesting_account, action='DELETE', target_model='ASSESSMENT', outcome='DENIED', response=response, school=requesting_account.school)

            return {'error': response}

        assessment = Assessment.objects.select_related('assessor').get(assessment_id=details.get('assessment'), school=requesting_account.school)

        # Ensure only authorized users can delete
        if assessment.assessor != requesting_account:
            response = f'could not proccess your request, you do not have the necessary permissions to delete assessments that are not assessed by you.'
            audits_utilities.log_audit(actor=requesting_account, action='DELETE', target_model='ASSESSMENT', outcome='DENIED', response=response, school=requesting_account.school)

            return {'error': response}

        with transaction.atomic():
            response = f"assessment with assessment ID {assessment.assessment_id} has been successfully deleted, along with it's associated data"
            audits_utilities.log_audit(actor=requesting_account, action='DELETE', target_model='ASSESSMENT', target_object_id=str(assessment.assessment_id), outcome='DELETED', response=response, school=requesting_account.school,)

        return {"message": response}
                   
    except Teacher.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'a teacher account with the provided credentials does not exist, please check your account details and try again'}

    except ValidationError as e:
        error_message = e.messages[0].lower() if isinstance(e.messages, list) and e.messages else str(e).lower()
        audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='ACCOUNT', target_object_id=str(assessment.assessment_id) if assessment else 'N/A', outcome='ERROR', response=error_message, school=requesting_account.school)

        return {"error": error_message}

    except Exception as e:
        error_message = str(e)
        audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='ACCOUNT', target_object_id=str(assessment.assessment_id) if assessment else 'N/A', outcome='ERROR', response=error_message, school=requesting_account.school)

        return {'error': error_message}
    

@database_sync_to_async
def create_student_activity(account, role, details):
    try:
        classroom = None
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = accounts_utilities.get_account_and_permission_check_attr(account, role)

        # Check if the user has permission to create activities
        if not permissions_utilities.has_permission(requesting_account, 'CREATE', 'ACTIVITY'):
            response = f'could not proccess your request, you do not have the necessary permissions to log activities assessments.'
            audits_utilities.log_audit(actor=requesting_account, action='CREATE', target_model='ACTIVITY', outcome='DENIED', server_response=response, school=requesting_account.school)
            return {'error': response}

        # Retrieve the student account
        classroom = requesting_account.taught_classrooms.get(classroom_id=details['classroom'])
        requested_account = classroom.students.get(account_id=details['recipient'])
 
        # Prepare the data for serialization
        details['auditor'] = requesting_account.id
        details['recipient'] = requested_account.id
        details['classroom'] = classroom.id
        details['school'] = requesting_account.school.id

        # Initialize the serializer with the prepared data
        serializer = ActivityCreationSerializer(data=details)
        if serializer.is_valid():
            with transaction.atomic():
                StudentActivity.objects.create(**serializer.validated_data)

                response = f'activity successfully logged. the activity is now available to everyone with access to the student\'s data.'
                audits_utilities.log_audit(actor=requesting_account, action='CREATE', target_model='ACTIVITY', target_object_id=str(classroom.classroom_id) if classroom else 'N/A', outcome='CREATED', server_response=response, school=requesting_account.school)

            return {'message': response}

        error_response = '; '.join([f"{key}: {', '.join(value)}" for key, value in serializer.errors.items()])
        audits_utilities.log_audit(actor=requesting_account, action='CREATE', target_model='ACTIVITY', target_object_id=str(classroom.classroom_id) if classroom else 'N/A', outcome='ERROR', server_response=f'Validation failed: {error_response}', school=requesting_account.school)
        return {"error": error_response}

    except Student.DoesNotExist:
        # Handle case where the user or student account does not exist
        return {'error': 'a student account in your school with the provided credentials does not exist. Please check the account details and try again.'}

    except ValidationError as e:
        error_message = e.messages[0].lower() if isinstance(e.messages, list) and e.messages else str(e).lower()
        audits_utilities.log_audit(actor=requesting_account, action='CREATE', target_model='ACTIVITY', target_object_id=str(classroom.classroom_id) if classroom else 'N/A', outcome='ERROR', server_response=error_message, school=requesting_account.school)
        return {"error": error_message}

    except Exception as e:
        error_message = str(e)
        audits_utilities.log_audit(actor=requesting_account, action='CREATE', target_model='ACTIVITY', target_object_id=str(classroom.classroom_id) if classroom else 'N/A', outcome='ERROR', server_response=error_message, school=requesting_account.school)
        return {'error': error_message}
