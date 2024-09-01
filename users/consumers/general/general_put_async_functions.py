# python 
import time

# httpx

# channels
from channels.db import database_sync_to_async

# django
from django.db import transaction
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.contrib.auth.password_validation import validate_password
from django.core.cache import cache
from django.utils.translation import gettext as _
from django.utils import timezone

# simple jwt
from rest_framework_simplejwt.tokens import AccessToken as decode

# models 
from access_tokens.models import AccessToken
from users.models import BaseUser, Principal, Admin, Teacher
from schools.models import School
from assessments.models import Assessment
from transcripts.models import Transcript
from assessments.models import Topic
from email_bans.models import EmailBan
from chats.models import ChatRoom, ChatRoomMessage

# serializers
from schools.serializers import UpdateSchoolAccountSerializer, SchoolDetailsSerializer
from assessments.serializers import AssessmentUpdateSerializer

# utility functions 
from users.utils import get_account_and_its_school
from authentication.utils import verify_user_otp
from permissions.utils import has_permission
from audit_logs.utils import log_audit

# mappings
from users.maps import role_specific_maps


@database_sync_to_async
def update_school_details(user, role, details):
    try:
        if role not in ['FOUNDER', 'PRINCIPAL', 'ADMIN']:
            return {"error": 'could not proccess your request.. your account either has insufficient permissions or is invalid for the action you are trying to perform'}
        
        elif details.get('school') == 'requesting my own school':
            # Retrieve the user and related school in a single query using select_related
            if role == 'PRINCIPAL':
                admin = Principal.objects.select_related('school').only('school').get(account_id=user)
            else:
                admin = Admin.objects.select_related('school').only('school').get(account_id=user)

            school = admin.school

        else:
            school = School.objects.get(school_id=details.get('school'))

        # Initialize the serializer with the existing school instance and incoming data
        serializer = UpdateSchoolAccountSerializer(instance=school, data=details)

        # Validate the incoming data
        if serializer.is_valid():
            # Use an atomic transaction to ensure the database is updated safely
            with transaction.atomic():
                serializer.save()
                        
            # Serialize the grade
            serialized_school = SchoolDetailsSerializer(school).data

            return {'school': serialized_school, "message": "school account details have been successfully updated" }
        
        # Return serializer errors if the data is not valid, format it as a string
        return {"error": '; '.join([f"{key}: {', '.join(value)}" for key, value in serializer.errors.items()])}
               
    except Principal.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'a principal account with the provided credentials does not exist, please check the account details and try again'}
                   
    except Admin.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'an admin account with the provided credentials does not exist, please check the account details and try again'}
    
    except School.DoesNotExist:
        # Handle the case where the provided school ID does not exist
        return {"error": "a school with the provided credentials does not exist"}

    except ValidationError as e:
        # Handle validation errors separately with meaningful messages
        return {"error": e.messages[0].lower() if isinstance(e.messages, list) and e.messages else str(e).lower()}

    except Exception as e:
        # Handle any unexpected errors with a general error message
        return {'error': str(e)}


@database_sync_to_async
def update_assessment(user, role, details):
    try:
        if role not in ['PRINCIPAL', 'ADMIN', 'TEACHER']:
            return {"error": 'could not proccess your request.. your account either has insufficient permissions or is invalid for the action you are trying to perform'}

        assessment = None  # Initialize assessment as None to prevent issues in error handling

        # Retrieve the user and related school in a single query using select_related
        requesting_account = get_account_and_its_school(user, role)

        # Check if the user has permission to create an assessment
        if role != 'PRINCIPAL' and not has_permission(requesting_account, 'UPDATE', 'ASSESSMENT'):
            response = f'could not proccess your request, you do not have the necessary permissions to update assessments.'

            log_audit(
                actor=requesting_account,
                action='UPDATE',
                target_model='ASSESSMENT',
                outcome='DENIED',
                response=response,
                school=requesting_account.school
            )

            return {'error': response}

        assessment = Assessment.objects.get(assessment_id=details.get('assessment'), school=requesting_account.school)
        
        # Ensure only authorized users can delete
        if role == 'TEACHER' and assessment.assessor != requesting_account:
            response = f'could not proccess your request, you do not have the necessary permissions to update assessments that are not assessed by you.'

            log_audit(
                actor=requesting_account,
                action='UPDATE',
                target_model='ASSESSMENT',
                outcome='DENIED',
                response=response,
                school=requesting_account.school
            )

            return {'error': response}

        # Serialize the details for assessment creation
        serializer = AssessmentUpdateSerializer(instance=assessment, data=details)
        if serializer.is_valid():
            # Create the assessment within a transaction to ensure atomicity
            with transaction.atomic():
                serializer.save()

                if details.get('topics'):
                    topics = []
                    for name in details.get('topics'):
                        topic, _ = Topic.objects.get_or_create(name=name)
                        topics.append(topic)

                    assessment.topics.set(topics)
                    
                response = f'assessment {assessment.unique_identifier} has been successfully updated, the new updates will reflect imemdiately to all the students being assessed and their parents'

                log_audit(
                    actor=requesting_account,
                    action='CREATE',
                    target_model='ASSESSMENT',
                    target_object_id=str(assessment.assessment_id),
                    outcome='CREATED',
                    response=response,
                    school=requesting_account.school,
                )

            return {"message": response}
        
        error_response = '; '.join([f"{key}: {', '.join(value)}" for key, value in serializer.errors.items()])

        log_audit(
            actor=requesting_account,
            action='UPDATE',
            target_model='ASSESSMENT',
            outcome='ERROR',
            response=f'Validation failed: {error_response}',
            school=requesting_account.school
        )

        return {"error": error_response}
               
    except Principal.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'a principal account with the provided credentials does not exist, please check your account details and try again'}
                   
    except Admin.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'an admin account with the provided credentials does not exist, please check your account details and try again'}
                   
    except Teacher.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'a teacher account with the provided credentials does not exist, please check your account details and try again'}

    except Assessment.DoesNotExist:
        # Handle the case where the provided assessment ID does not exist
        return {'error': 'an assessment in your school with the provided credentials does not exist, please check the assessment details and try again'}

    except ValidationError as e:
        error_message = e.messages[0].lower() if isinstance(e.messages, list) and e.messages else str(e).lower()

        log_audit(
            actor=requesting_account,
            action='UPDATE',
            target_model='ASSESSMENT',
            target_object_id=str(assessment.assessment_id) if assessment else 'N/A',
            outcome='ERROR',
            response=error_message,
            school=requesting_account.school
        )

        return {"error": error_message}

    except Exception as e:
        error_message = str(e)

        log_audit(
            actor=requesting_account,
            action='UPDATE',
            target_model='ASSESSMENT',
            target_object_id=str(assessment.assessment_id) if assessment else 'N/A',
            outcome='ERROR',
            response=error_message,
            school=requesting_account.school
        )

        return {'error': error_message}


@database_sync_to_async
def collect_assessment(user, role, details):
    try:
        if role not in ['PRINCIPAL', 'ADMIN', 'TEACHER']:
            return {"error": 'could not proccess your request.. your account either has insufficient permissions or is invalid for the action you are trying to perform'}

        assessment = None  # Initialize assessment as None to prevent issues in error handling

        # Retrieve the user and related school in a single query using select_related
        requesting_account = get_account_and_its_school(user, role)

        # Check if the user has permission to create an assessment
        if role != 'PRINCIPAL' and not has_permission(requesting_account, 'COLLECT', 'ASSESSMENT'):
            response = f'could not proccess your request, you do not have the necessary permissions to collect assessments.'

            log_audit(
                actor=requesting_account,
                action='COLLECT',
                target_model='ASSESSMENT',
                outcome='DENIED',
                response=response,
                school=requesting_account.school
            )

            return {'error': response}

        assessment = Assessment.objects.select_related('students_assessed').get(assessment_id=details.get('assessment'), school=requesting_account.school)
        
        # Ensure only authorized users can delete
        if role == 'TEACHER' and assessment.assessor != requesting_account:
            response = f'could not proccess your request, you do not have the necessary permissions to collect assessments that are not assessed by you.'

            log_audit(
                actor=requesting_account,
                action='COLLECT',
                target_model='ASSESSMENT',
                outcome='DENIED',
                response=response,
                school=requesting_account.school
            )

            return {'error': response}

        students = assessment.students_assessed.filter(account_id__in=details.get('students'))

        with transaction.atomic():
            assessment.ontime_submission.add(*students)
            response = f"assessment successfully collected from {len(students)} assessed students."

            log_audit(
                actor=user,
                action='COLLECT',
                target_model='ASSESSMENT',
                target_object_id=str(assessment.assessment_id),
                outcome='COLLECTED',
                response=response,
                school=assessment.school
            )

        return {"message": response}
               
    except Principal.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'a principal account with the provided credentials does not exist, please check your account details and try again'}
                   
    except Admin.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'an admin account with the provided credentials does not exist, please check your account details and try again'}
                   
    except Teacher.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'a teacher account with the provided credentials does not exist, please check your account details and try again'}

    except Assessment.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'an assessment in your school with the provided credentials does not exist, please check the assessment details and try again'}

    except Exception as e:
        error_message = str(e)

        log_audit(
            actor=requesting_account,
            action='COLLECT',
            target_model='ASSESSMENT',
            target_object_id=str(assessment.assessment_id) if assessment else 'N/A',
            outcome='ERROR',
            response=error_message,
            school=requesting_account.school
        )

        return {'error': error_message}


@database_sync_to_async
def submit_late_assessment_submitions(user, role, details):
    try:
        if role not in ['PRINCIPAL', 'ADMIN', 'TEACHER']:
            return {"error": 'could not proccess your request.. your account either has insufficient permissions or is invalid for the action you are trying to perform'}

        assessment = None  # Initialize assessment as None to prevent issues in error handling

        # Retrieve the user and related school in a single query using select_related
        requesting_account = get_account_and_its_school(user, role)

        # Check if the user has permission to create an assessment
        if role != 'PRINCIPAL' and not has_permission(requesting_account, 'COLLECT', 'ASSESSMENT'):
            response = f'could not proccess your request, you do not have the necessary permissions to collect assessments.'

            log_audit(
                actor=requesting_account,
                action='COLLECT',
                target_model='ASSESSMENT',
                outcome='DENIED',
                response=response,
                school=requesting_account.school
            )

            return {'error': response}

        assessment = Assessment.objects.select_related('not_submitted').get(assessment_id=details.get('assessment'), school=requesting_account.school)
        
        # Ensure only authorized users can delete
        if role == 'TEACHER' and assessment.assessor != requesting_account:
            response = f'could not proccess your request, you do not have the necessary permissions to collect late assessment submitions that are not assessed by you.'

            log_audit(
                actor=requesting_account,
                action='COLLECT',
                target_model='ASSESSMENT',
                outcome='DENIED',
                response=response,
                school=requesting_account.school
            )

            return {'error': response}
        
        students = assessment.not_submitted.filter(account_id__in=details.get('students'))

        with transaction.atomic():
            assessment.not_submitted.remove(*students)
            assessment.late_submission.add(*students)

            response = f"assessment late submitions successfully collected from {len(students)} students."

            log_audit(
                actor=user,
                action='COLLECT',
                target_model='ASSESSMENT',
                target_object_id=str(assessment.assessment_id),
                outcome='COLLECTED',
                response=response,
                school=assessment.school
            )

        return {"message": response}
               
    except Principal.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'a principal account with the provided credentials does not exist, please check your account details and try again'}
                   
    except Admin.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'an admin account with the provided credentials does not exist, please check your account details and try again'}
                   
    except Teacher.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'a teacher account with the provided credentials does not exist, please check your account details and try again'}

    except Assessment.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'an assessment in your school with the provided credentials does not exist, please check the assessment details and try again'}

    except Exception as e:
        error_message = str(e)

        log_audit(
            actor=requesting_account,
            action='COLLECT',
            target_model='ASSESSMENT',
            target_object_id=str(assessment.assessment_id) if assessment else 'N/A',
            outcome='ERROR',
            response=error_message,
            school=requesting_account.school
        )

        return {'error': error_message}


@database_sync_to_async
def flag_assessment_as_assessed(user, role, details):
    try:
        if role not in ['PRINCIPAL', 'ADMIN', 'TEACHER']:
            return {"error": 'could not proccess your request.. your account either has insufficient permissions or is invalid for the action you are trying to perform'}

        assessment = None  # Initialize assessment as None to prevent issues in error handling

        # Retrieve the user and related school in a single query using select_related
        requesting_account = get_account_and_its_school(user, role)

        # Check if the user has permission to create an assessment
        if role != 'PRINCIPAL' and not has_permission(requesting_account, 'UPDATE', 'ASSESSMENT'):
            response = f'could not proccess your request, you do not have the necessary permissions to update assessments.'

            log_audit(
                actor=requesting_account,
                action='UPDATE',
                target_model='ASSESSMENT',
                outcome='DENIED',
                response=response,
                school=requesting_account.school
            )

            return {'error': response}

        assessment = Assessment.objects.select_related('students_assessed', 'ontime_submission').get(assessment_id=details.get('assessment'), school=requesting_account.school)
        
        # Ensure only authorized users can delete
        if role == 'TEACHER' and assessment.assessor != requesting_account:
            response = f'could not proccess your request, you do not have the necessary permissions to update assessments that are not assessed by you.'

            log_audit(
                actor=requesting_account,
                action='UPDATE',
                target_model='ASSESSMENT',
                outcome='DENIED',
                response=response,
                school=requesting_account.school
            )

            return {'error': response}

        with transaction.atomic():
            assessment.assessed = True
            assessment.date_assessed = timezone.now()

            not_submitted_students = assessment.students_assessed.exclude(pk__in=assessment.ontime_submission.all())
            assessment.not_submitted.add(*not_submitted_students)

            assessment.save()
            response = f"assessment {assessment.unique_identifier} has been flagged as assessed, and all students that have not submitted their assessments have been flagged as not submitted for the assessment."

            log_audit(
                actor=user,
                action='UPDATE',
                target_model='ASSESSMENT',
                target_object_id=str(assessment.assessment_id),
                outcome='ASSESSED',
                response=response,
                school=assessment.school
            )

        return {"message": response}
               
    except Principal.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'a principal account with the provided credentials does not exist, please check your account details and try again'}
                   
    except Admin.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'an admin account with the provided credentials does not exist, please check your account details and try again'}
                   
    except Teacher.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'a teacher account with the provided credentials does not exist, please check your account details and try again'}

    except Assessment.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'an assessment in your school with the provided credentials does not exist, please check the assessment details and try again'}

    except Exception as e:
        error_message = str(e)

        log_audit(
            actor=requesting_account,
            action='UPDATE',
            target_model='ASSESSMENT',
            target_object_id=str(assessment.assessment_id) if assessment else 'N/A',
            outcome='ERROR',
            response=error_message,
            school=requesting_account.school
        )

        return {'error': error_message}


@database_sync_to_async
def release_assessment_grades(user, role, details):
    try:
        if role not in ['PRINCIPAL', 'ADMIN', 'TEACHER']:
            return {"error": 'could not proccess your request.. your account either has insufficient permissions or is invalid for the action you are trying to perform'}

        assessment = None  # Initialize assessment as None to prevent issues in error handling

        # Retrieve the user and related school in a single query using select_related
        requesting_account = get_account_and_its_school(user, role)

        # Check if the user has permission to create an assessment
        if role != 'PRINCIPAL' and not has_permission(requesting_account, 'UPDATE', 'ASSESSMENT'):
            response = f'could not proccess your request, you do not have the necessary permissions to update assessments.'

            log_audit(
                actor=requesting_account,
                action='UPDATE',
                target_model='ASSESSMENT',
                outcome='DENIED',
                response=response,
                school=requesting_account.school
            )

            return {'error': response}

        assessment = Assessment.objects.select_related('not_submitted').get(assessment_id=details.get('assessment'), school=requesting_account.school)
                
        # Ensure only authorized users can delete
        if role == 'TEACHER' and assessment.assessor != requesting_account:
            response = f'could not proccess your request, you do not have the necessary permissions to update assessments that are not assessed by you.'

            log_audit(
                actor=requesting_account,
                action='COLLECT',
                target_model='ASSESSMENT',
                outcome='DENIED',
                response=response,
                school=requesting_account.school
            )

            return {'error': response}
        
        not_submitted_students = assessment.not_submitted.all()

        # Create a transcript with a score of 0 for students who didn't submit
        with transaction.atomic():
            assessment.grades_released = True
            assessment.date_grades_released = timezone.now()
            
            for student in not_submitted_students:
                Transcript.objects.create(student=student, score=0, assessment=assessment)

            assessment.save()

            log_audit(
                actor=user,
                action='UPDATE',
                target_model='ASSESSMENT',
                target_object_id=str(assessment.assessment_id),
                outcome='UPDATED',
                response=f"Grades released for assessment {assessment.unique_identifier}.",
                school=assessment.school
            )

        return {"message": f"Grades released for assessment {assessment.unique_identifier}."}

    except Assessment.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'an assessment in your school with the provided credentials does not exist, please check the assessment details and try again'}

    except Exception as e:
        error_message = str(e)

        log_audit(
            actor=requesting_account,
            action='UPDATE',
            target_model='ASSESSMENT',
            target_object_id=str(assessment.assessment_id) if assessment else 'N/A',
            outcome='ERROR',
            response=error_message,
            school=requesting_account.school
        )

        return {'error': error_message}
    

@database_sync_to_async
def update_email_ban_otp_sends(email_ban_id):
    """
    Updates the OTP sends count for a specific email ban and sets the ban status to 'PENDING'.

    This function increments the count of OTP sends for the specified email ban and updates the status
    to 'PENDING' if it is not already set to that status.

    Args:
        email_ban_id (int): The ID of the email ban to be updated.

    Returns:
        dict: A dictionary containing:
            - 'message': A message indicating that a new OTP has been sent.
            - 'error': A string containing an error message if an exception is raised.

    Raises:
        EmailBan.DoesNotExist: If the email ban with the provided ID does not exist.
        Exception: For any other unexpected errors.

    Example:
        response = await update_email_ban_otp_sends(123)
        if 'error' in response:
            # Handle error
        else:
            message = response['message']
            # Process OTP update
    """
    try:
        # Retrieve the email ban record
        email_ban = EmailBan.objects.get(ban_id=email_ban_id)
        
        # Increment the OTP sends count and update status
        email_ban.otp_send += 1
        if email_ban.status != 'PENDING':
            email_ban.status = 'PENDING'
        email_ban.save()
        
        return {"message": "A new OTP has been sent to your email address."}

    except EmailBan.DoesNotExist:
        return {'error': 'Email ban with the provided ID does not exist. Please verify the ID and try again.'}
    
    except Exception as e:
        return {'error': f'An unexpected error occurred while updating OTP sends: {str(e)}'}


@database_sync_to_async
def update_email(user, details, access_token):
    
    try:
        validate_password(details.get('new_email'))

        if BaseUser.objects.filter(email=details.get('new_email')).exists():
            return {"error": "an account with the provided email address already exists"}

        account = BaseUser.objects.get(account_id=user)
        
        if details.get('new_email') == account.email:
            return {"error": "cannot set current email as new email"}
    
        hashed_authorization_otp = cache.get(account.email + 'authorization_otp')
        if not hashed_authorization_otp:
            return {"denied": "OTP expired, taking you back to email verification.."}
    
        if not verify_user_otp(details.get('authorization_otp'), hashed_authorization_otp):
            return {"denied": "incorrect authorization OTP, action forrbiden"}
    
        EmailBan.objects.filter(email=account.email).delete()
        
        account.email = details.get('new_email')
        account.email_ban_amount = 0
        account.save()
        
        # Decode the token
        token = decode(access_token)
        
        # Calculate the remaining time for the token to expire
        expiration_time = token.payload['exp'] - int(time.time())
        
        if expiration_time > 0:
            cache.set(access_token, 'blacklisted', timeout=expiration_time)
    
        # delete token from database
        AccessToken.objects.filter(token=str(access_token)).delete()
    
        return {"message": "email changed successfully"}
    
    except BaseUser.DoesNotExist:
        return {'error': 'user with the provided credentials does not exist'}

    except Exception as e:
        return {"error": str(e)}


@database_sync_to_async
def update_password(user, details, access_token):
    
    try:
        account = BaseUser.objects.get(account_id=user)

        hashed_authorization_otp = cache.get(account.email + 'authorization_otp')
        if not hashed_authorization_otp:
            return {"denied": "OTP expired.. taking you back to password verification.."}
    
        if not verify_user_otp(details.get('authorization_otp'), hashed_authorization_otp):
            return {"denied": "incorrect authorization OTP.. action forrbiden"}
    
        validate_password(details.get('new_password'))
        
        account.set_password(details.get('new_password'))
        account.save()
        
        # Decode the token
        token = decode(access_token)
        
        # Calculate the remaining time for the token to expire
        expiration_time = token.payload['exp'] - int(time.time())
        
        if expiration_time > 0:
            cache.set(access_token, 'blacklisted', timeout=expiration_time)
    
        # delete token from database
        AccessToken.objects.filter(token=str(access_token)).delete()
    
        return {"message": "password changed successfully"}
    
    except BaseUser.DoesNotExist:
        return {'error': 'user with the provided credentials does not exist'}
    
    except ValidationError as e:
        return {"error": str(e)}

    except Exception as e:
        return {"error": str(e)}
    

@database_sync_to_async
def update_multi_factor_authentication(user, details):

    try:
        account = BaseUser.objects.get(account_id=user)
        
        if account.email_banned:
            return { "error" : "your email has been banned"}
        
        with transaction.atomic():
            account.multifactor_authentication = details.get('toggle')
            account.save()
        
        return {'message': 'Multifactor authentication {} successfully'.format('enabled' if details['toggle'] else 'disabled')}
    
    except BaseUser.DoesNotExist:
        return {'error': 'an account with the provided credentials does not exist, please check the account details and try again'}
    
    except Exception as e:
        return {'error': str(e)}
    

@database_sync_to_async
def mark_messages_as_read(user, details):
    try:
        # Retrieve the account making the request
        account = BaseUser.objects.get(account_id=user)
        # Retrieve the requested user's account
        requested_user = BaseUser.objects.get(account_id=details.get('account_id'))
        
        # Check if a chat room exists between the two users
        chat_room = ChatRoom.objects.filter(Q(user_one=account, user_two=requested_user) | Q(user_one=requested_user, user_two=account)).first()

        if chat_room:

            # Query for messages that need to be marked as read
            messages_to_update = ChatRoomMessage.objects.filter(chat_room=chat_room, read_receipt=False).exclude(sender=account)

            # Check if there are any messages that match the criteria
            if messages_to_update.exists():

                # Mark the messages as read
                messages_to_update.update(read_receipt=True)
                return {"read": True, 'user': str(requested_user.account_id), 'chat': str(account.account_id)}
            
            else:
                # Handle the case where no messages need to be updated (optional)
                return {"read": True}
        
        return {"error": 'no such chat room exists'}

    except BaseUser.DoesNotExist:
        # Handle case where the user does not exist
        return {'error': 'An account with the provided credentials does not exist. Please check the account details and try again.'}
        
    except ChatRoom.DoesNotExist:
        return {'error': 'Chat room not found.'}

    except Exception as e:
        return {'error': str(e)}

