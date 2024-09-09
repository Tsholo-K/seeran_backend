# python 
import time

# httpx

# channels
from channels.db import database_sync_to_async

# django
from django.utils import timezone
from django.db import  transaction
from django.core.cache import cache
from django.utils.translation import gettext as _
from django.core.exceptions import ValidationError

# simple jwt
from rest_framework_simplejwt.tokens import AccessToken as decode, TokenError
from rest_framework_simplejwt.exceptions import TokenError

# models 
from access_tokens.models import AccessToken
from users.models import BaseUser, Principal, Admin, Teacher, Student, Parent
from schools.models import School
from grades.models import Grade
from classes.models import Classroom
from assessments.models import Assessment
from transcripts.models import Transcript
from assessments.models import Topic
from activities.models import Activity
from attendances.models import Attendance
from chats.models import ChatRoom, ChatRoomMessage

# serializers
from users.serializers.general_serializers import BareAccountDetailsSerializer
from chats.serializers import ChatRoomMessageSerializer
from activities.serializers import ActivityCreationSerializer
from assessments.serializers import AssessmentCreationSerializer

# checks
from users.checks import permission_checks

# mappings
from users.maps import role_specific_maps

# queries
from users.complex_queries import queries

# utlity functions
from users.utils import get_account_and_its_school
from permissions.utils import has_permission
from audit_logs.utils import log_audit


@database_sync_to_async
def delete_school_account(user, role, details):
    try:
        if role not in ['FOUNDER', 'PRINCIPAL']:
            return {"error": 'could not proccess your request.. your account either has insufficient permissions or is invalid for the action you are trying to perform'}
        
        elif details.get('school') == 'requesting my own school':
            # Retrieve the user and related school in a single query using select_related
            admin = get_account_and_its_school(user, role)
            school = admin.school

        else:
            # Retrieve the School instance by school_id from the provided details
            school = School.objects.get(school_id=details.get('school'))

        with transaction.atomic():
            # Perform bulk delete operations without triggering signals
            Principal.objects.filter(school=school).delete()
            Admin.objects.filter(school=school).delete()
            Teacher.objects.filter(school=school).delete()
            Student.objects.filter(school=school).delete()
            Classroom.objects.filter(school=school).delete()
            Grade.objects.filter(school=school).delete()

            # Delete the School instance
            school.delete()

        # Return a success message
        return {"message": "school account deleted successfully"}
                   
    except Principal.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'a principal account with the provided credentials does not exist, please check the account details and try again'}

    except School.DoesNotExist:
        # Handle the case where the School does not exist
        return {"error": "a school with the provided credentials does not exist"}
    
    except Exception as e:
        # Handle any unexpected errors with a general error message
        return {'error': str(e).lower()}


@database_sync_to_async
def set_assessment(user, role, details):
    try:
        if role not in ['PRINCIPAL', 'ADMIN', 'TEACHER']:
            return {"error": 'could not proccess your request.. your account either has insufficient permissions or is invalid for the action you are trying to perform'}

        assessment = None  # Initialize assessment as None to prevent issues in error handling

        # Retrieve the user and related school in a single query using select_related
        requesting_account = get_account_and_its_school(user, role)

        # Check if the user has permission to create an assessment
        if role != 'PRINCIPAL' and not has_permission(requesting_account, 'CREATE', 'ASSESSMENT'):
            response = f'could not proccess your request, you do not have the necessary permissions to create assessments.'

            log_audit(
                actor=requesting_account,
                action='CREATE',
                target_model='ASSESSMENT',
                outcome='DENIED',
                response=response,
                school=requesting_account.school
            )

            return {'error': response}

        if details.get('classroom'):
            if role == 'TEACHER':
                classroom = requesting_account.taught_classes.select_related('grade', 'subject').prefetch_related('grade__terms').filter(classroom_id=details.get('classroom')).first()
            
            else:
                classroom = requesting_account.school.classes.select_related('grade', 'subject').prefetch_related('grade__terms').filter(classroom_id=details.get('classroom')).first()
            
            if not classroom:
                response = "the provided classroom is either not assigned to you or does not exist. please check the classroom details and try again"

                log_audit(
                    actor=requesting_account,
                    action='CREATE',
                    target_model='ASSESSMENT',
                    outcome='ERROR',
                    response=response,
                    school=requesting_account.school
                )

                return {'error': response}

            term = classroom.grade.terms.filter(term_id=details.get('term')).first()
            subject = classroom.subject.pk

            details['classroom'] = classroom.pk
            details['grade'] = classroom.grade.pk
 
        elif details.get('grade') and details.get('subject'):
            if role not in ['PRINCIPAL', 'ADMIN']:
                response = "could not proccess your request, you do not have the necessary permissions to create grade wide assessments."

                log_audit(
                    actor=requesting_account,
                    action='CREATE',
                    target_model='ASSESSMENT',
                    outcome='DENIED',
                    response=response,
                    school=requesting_account.school
                )

                return {'error': response}
            
            grade = requesting_account.school.grades.prefetch_related('terms', 'subjects').filter(grade_id=details.get('grade')).first()

            if not grade:
                response = "the provided grade is either not from your school or does not exist. please check the grade details and try again"

                log_audit(
                    actor=requesting_account,
                    action='CREATE',
                    target_model='ASSESSMENT',
                    outcome='DENIED',
                    response=response,
                    school=requesting_account.school
                )

                return {'error': response}
            
            term = grade.terms.filter(term_id=details.get('term')).first()
            subject = grade.subjects.filter(subject_id=details.get('subject')).first()
            
            details['grade'] = grade.pk

        else:
            response = "could not proccess your request, invalid assessment creation details. please provide all required information and try again."

            log_audit(
                actor=requesting_account,
                action='CREATE',
                target_model='ASSESSMENT',
                outcome='ERROR',
                response=response,
                school=requesting_account.school
            )

            return {'error': response}
        
        if not term:
            response = "a term for your school with the provided credentials does not exist. please check the term details and try again"

            log_audit(
                actor=requesting_account,
                action='CREATE',
                target_model='ASSESSMENT',
                outcome='ERROR',
                response=response,
                school=requesting_account.school
            )

            return {'error': response}
        
        if not subject:
            response = "a subject for your school with the provided credentials does not exist. please check the subject details and try again"

            log_audit(
                actor=requesting_account,
                action='CREATE',
                target_model='ASSESSMENT',
                outcome='ERROR',
                response=response,
                school=requesting_account.school
            )

            return {'error': response}

        # Set the school field in the details to the user's school ID
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
            action='CREATE',
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

    except ValidationError as e:
        error_message = e.messages[0].lower() if isinstance(e.messages, list) and e.messages else str(e).lower()

        log_audit(
            actor=requesting_account,
            action='CREATE',
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
            action='CREATE',
            target_model='ASSESSMENT',
            target_object_id=str(assessment.assessment_id) if assessment else 'N/A',
            outcome='ERROR',
            response=error_message,
            school=requesting_account.school
        )

        return {'error': error_message}


@database_sync_to_async
def delete_assessment(user, role, details):
    try:
        if role not in ['PRINCIPAL', 'ADMIN', 'TEACHER']:
            return {"error": 'could not proccess your request.. your account either has insufficient permissions or is invalid for the action you are trying to perform'}

        assessment = None  # Initialize assessment as None to prevent issues in error handling

        # Retrieve the user and related school in a single query using select_related
        requesting_account = get_account_and_its_school(user, role)

        # Check if the user has permission to create an assessment
        if role != 'PRINCIPAL' and not has_permission(requesting_account, 'DELETE', 'ASSESSMENT'):
            response = f'could not proccess your request, you do not have the necessary permissions to delete assessments.'

            log_audit(
                actor=requesting_account,
                action='DELETE',
                target_model='ASSESSMENT',
                outcome='DENIED',
                response=response,
                school=requesting_account.school
            )

            return {'error': response}

        assessment = Assessment.objects.select_related('assessor').get(assessment_id=details.get('assessment'), school=requesting_account.school)

        # Ensure only authorized users can delete
        if role == 'TEACHER' and assessment.assessor != requesting_account:
            response = f'could not proccess your request, you do not have the necessary permissions to delete assessments that are not assessed by you.'

            log_audit(
                actor=requesting_account,
                action='DELETE',
                target_model='ASSESSMENT',
                outcome='DENIED',
                response=response,
                school=requesting_account.school
            )

            return {'error': response}

        with transaction.atomic():
            response = f"assessment with assessment ID {assessment.assessment_id} has been successfully deleted, along with it's associated data"

            log_audit(
                actor=requesting_account,
                action='DELETE',
                target_model='ASSESSMENT',
                target_object_id=str(assessment.assessment_id),
                outcome='DELETED',
                response=response,
                school=requesting_account.school
            )

            assessment.delete()

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

    except ValidationError as e:
        error_message = e.messages[0].lower() if isinstance(e.messages, list) and e.messages else str(e).lower()

        log_audit(
            actor=requesting_account,
            action='DELETE',
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
            action='DELETE',
            target_model='ASSESSMENT',
            target_object_id=str(assessment.assessment_id) if assessment else 'N/A',
            outcome='ERROR',
            response=error_message,
            school=requesting_account.school
        )

        return {'error': error_message}


@database_sync_to_async
def grade_student(user, role, details):
    try:
        if role not in ['PRINCIPAL', 'ADMIN', 'TEACHER']:
            return {"error": 'could not proccess your request.. your account either has insufficient permissions or is invalid for the action you are trying to perform'}

        assessment = None  # Initialize assessment as None to prevent issues in error handling

        # Retrieve the user and related school in a single query using select_related
        requesting_account = get_account_and_its_school(user, role)

        # Check if the user has permission to create an assessment
        if role != 'PRINCIPAL' and not has_permission(requesting_account, 'GRADE', 'ASSESSMENT'):
            response = f'could not proccess your request, you do not have the necessary permissions to grade assessments.'

            log_audit(
                actor=requesting_account,
                action='GRADE',
                target_model='ASSESSMENT',
                outcome='DENIED',
                response=response,
                school=requesting_account.school
            )

            return {'error': response}

        assessment = Assessment.objects.select_related('assessor').get(assessment_id=details.get('assessment'), school=requesting_account.school)

        # Ensure only authorized users can delete
        if role == 'TEACHER' and assessment.assessor != requesting_account:
            response = f'could not proccess your request, you do not have the necessary permissions to grade assessments that are not assessed by you.'

            log_audit(
                actor=requesting_account,
                action='GRADE',
                target_model='ASSESSMENT',
                outcome='DENIED',
                response=response,
                school=requesting_account.school
            )

            return {'error': response}
        
        student = Student.objects.get(student_id=details.get('student'))
        
        with transaction.atomic():
            transcript = Transcript.objects.create(student=student, score=details.get('student'), assessment=assessment)
            response = f"student graded for assessment {assessment.unique_identifier}."

            log_audit(
                actor=user,
                action='GRADE',
                target_model='ASSESSMENT',
                target_object_id=str(transcript.transcript_id),
                outcome='GRADED',
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

    except Student.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'a student account with the provided credentials does not exist, please check the accounts details and try again'}

    except Assessment.DoesNotExist:
        # Handle the case where the provided assessment ID does not exist
        return {'error': 'an assessment in your school with the provided credentials does not exist, please check the assessment details and try again'}
    
    except ValidationError as e:
        error_message = e.messages[0].lower() if isinstance(e.messages, list) and e.messages else str(e).lower()

        log_audit(
            actor=requesting_account,
            action='GRADE',
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
            action='GRADE',
            target_model='ASSESSMENT',
            target_object_id=str(assessment.assessment_id) if assessment else 'N/A',
            outcome='ERROR',
            response=error_message,
            school=requesting_account.school
        )

        return {'error': error_message}
    

@database_sync_to_async
def submit_attendance(user, role, details):
    try:
        if role not in ['PRINCIPAL', 'ADMIN', 'TEACHER']:
            return {"error": 'could not proccess your request.. your account either has insufficient permissions or is invalid for the action you are trying to perform'}

        requesting_user = BaseUser.objects.get(account_id=user)

        if details.get('class') == 'submitting my own classes data' and role == 'TEACHER':
            # Build the queryset for the requesting account with the necessary related fields.
            requesting_account = Teacher.objects.prefetch_related('taught_classes').get(account_id=user)
          
            classroom = requesting_account.taught_classes.prefetch_related('attendances').filter(register_class=True).first()
            if not classroom:
                return {"error": _("could not proccess your request. the account making the request has no register class assigned to it")}

        elif details.get('class') and role in ['PRINCIPAL', 'ADMIN']:
            # Build the queryset for the requesting account with the necessary related fields.
            requesting_account = get_account_and_its_school(user, role)

            classroom = Classroom.objects.prefetch_related('attendances').get(class_id=details.get('class'), school=requesting_account.school, register_class=True)
        
        today = timezone.localdate()

        if details.get('absent'):
            if classroom.attendances.filter(date__date=today).exists():
                return {'error': 'attendance register for this class has already been subimitted today.. can not resubmit'}

            with transaction.atomic():
                register = Attendance.objects.create(submitted_by=requesting_user, classroom=classroom)

                if details.get('students'):
                    register.absentes = True
                    for student in details['students'].split(', '):
                        register.absent_students.add(Student.objects.get(account_id=student))

                register.save()
            
            response =  {'message': 'attendance register successfully taken for today'}

        if details.get('late'):
            if not details.get('students'):
                return {"error" : 'invalid request.. no students were provided.. at least one student is needed to be marked as late'}

            absentes = classroom.attendances.prefetch_related('absent_students').filter(date__date=today).first()
            if not absentes:
                return {'error': 'attendance register for this class has not been submitted today.. can not submit late arrivals before the attendance register'}

            if not absentes.absent_students.exists():
                return {'error': 'todays attendance register for this class has all students accounted for'}

            register = Attendance.objects.filter(date__date=today, classroom=classroom).first()
            
            with transaction.atomic():
                if not register:
                    register = Attendance.objects.create(submitted_by=requesting_user, classroom=classroom)
                    
                for student in details['students'].split(', '):
                    student = Student.objects.get(account_id=student)
                    absentes.absent_students.remove(student)
                    register.late_students.add(student)

                absentes.save()
                register.save()

            response =  {'message': 'students marked as late, attendance register successfully updated'}

        return response

    except BaseUser.DoesNotExist:
        # Handle case where the user or teacher account does not exist
        return {'error': 'The account with the provided credentials does not exist. Please check the account details and try again.'}
    
    except Classroom.DoesNotExist:
        return { 'error': 'class with the provided credentials does not exist' }

    except Exception as e:
        return { 'error': str(e) }


@database_sync_to_async
def log_activity(user, role, details):
    try:
        # Ensure the account has a valid role to log activities
        if role not in ['PRINCIPAL', 'ADMIN', 'TEACHER']:
            return {"error": "could not proccess your request. you do not have sufficient permissions to log activities."}

        requesting_user = BaseUser.objects.get(account_id=user)
        
        # If the account is a teacher, ensure they are teaching the student and the teacher of the class
        if role == 'TEACHER':
            requesting_account = Teacher.objects.select_related('school').prefetch_related('taught_classes').get(account_id=user)
                    
            # Determine the classroom based on the request details
            if details.get('class') == 'submitting my own classes data':
                # Fetch the classroom where the user is the teacher and it is a register class
                classroom = requesting_account.taught_classes.filter(register_class=True).first()
                if not classroom:
                    return {"error": _("could not proccess your request. the account making the request has no register class assigned to it")}

            else:
                # Fetch the specific classroom based on class_id and school
                classroom = Classroom.objects.get(class_id=details.get('class'), school=requesting_account.school)

            if classroom.teacher != requesting_account or not requesting_account.taught_classes.filter(students=requested_account).exists():
                return {"error": "unauthorized access. you can only log activities for classrooms and students you teach."}
  
            details['classroom'] = classroom.pk
        
        else:
            # Retrieve the user account and the student account using select_related to minimize database hits
            requesting_account = get_account_and_its_school(user, role)
            requested_account = Student.objects.select_related('school').get(account_id=details.get('recipient'), school=requesting_account.school)

        # Prepare the data for serialization
        details['recipient'] = requested_account.pk
        details['logger'] = requesting_user.pk
        details['school'] = requesting_account.school.pk

        # Initialize the serializer with the prepared data
        serializer = ActivityCreationSerializer(data=details)
        if serializer.is_valid():
            with transaction.atomic():
                Activity.objects.create(**serializer.validated_data)

            return {'message': 'activity successfully logged. the activity is now available to everyone with access to the student\'s data.'}

        # Return validation errors if the serializer is not valid
        return {"error": serializer.errors}

    except BaseUser.DoesNotExist:
        # Handle case where the user or student account does not exist
        return {'error': 'an account with the provided credentials does not exist. Please check the account details and try again.'}

    except Principal.DoesNotExist:
        # Handle the case where the requested principal account does not exist.
        return {'error': 'a principal account with the provided credentials does not exist, please check the account details and try again'}

    except Admin.DoesNotExist:
        # Handle the case where the requested admin account does not exist.
        return {'error': 'an admin account with the provided credentials does not exist, please check the account details and try again'}

    except Teacher.DoesNotExist:
        # Handle the case where the requested teacher account does not exist.
        return {'error': 'a teacher account with the provided credentials does not exist, please check the account details and try again'}

    except Exception as e:
        # Handle any other unexpected exceptions
        return {'error': str(e)}

    
@database_sync_to_async
def log_out(access_token):
         
    try:
        # Decode the token
        token = decode(access_token)
        
        # Calculate the remaining time for the token to expire
        expiration_time = token.payload['exp'] - int(time.time())
        
        if expiration_time > 0:
            cache.set(access_token, 'blacklisted', timeout=expiration_time)
    
        # delete token from database
        AccessToken.objects.filter(token=str(access_token)).delete()
        
        return {"message": "logged you out successful"}
    
    except TokenError as e:
        return {"error": str(e)}

    except Exception as e:
        return {"error": str(e)}


@database_sync_to_async
def text(user, role, details):
    try:
        # Validate users
        if user == details.get('account'):
            return {"error": "validation error. you can not send a text message to yourself, it violates database constraints and is therefore not allowed."}

        # Retrieve the user making the request
        requesting_user = BaseUser.objects.get(account_id=user)
        
        # Get the appropriate model for the requesting user's role from the mapping.
        Model, select_related, prefetch_related = role_specific_maps.account_model_and_attr_mapping[role]

        # Build the queryset for the requesting account with the necessary related fields.
        requesting_account = queries.account_and_its_attr_query_build(Model, select_related, prefetch_related).get(account_id=user)

        # Retrieve the requested user's account
        requested_user = BaseUser.objects.get(account_id=details.get('account'))
        
        # Get the appropriate model for the requesting user's role from the mapping.
        Model, select_related, prefetch_related = role_specific_maps.account_model_and_attr_mapping[requested_user.role]

        # Build the queryset for the requesting account with the necessary related fields.
        requested_account = queries.account_and_its_attr_query_build(Model, select_related, prefetch_related).get(account_id=details.get('account'))

        # Check permissions
        permission_error = permission_checks.check_message_permissions(requesting_account, requested_account)
        if permission_error:
            return {'error': permission_error}

        # Retrieve or create the chat room
        chat_room, created = ChatRoom.objects.get_or_create(user_one=requesting_user if requesting_user.pk < requested_user.pk else requested_user, user_two=requested_user if requesting_user.pk < requested_user.pk else requesting_user, defaults={'user_one': requesting_user, 'user_two': requested_user})

        with transaction.atomic():
            # Retrieve the last message in the chat room
            last_message = ChatRoomMessage.objects.filter(chat_room=chat_room).order_by('-timestamp').first()
            # Update the last message's 'last' field if it's from the same sender
            if last_message and last_message.sender == requesting_user:
                last_message.last = False
                last_message.save()

            # Create the new message
            new_message = ChatRoomMessage.objects.create(sender=requesting_user, content=details.get('message'), chat_room=chat_room)

            # Update the chat room's latest message timestamp
            chat_room.latest_message_timestamp = new_message.timestamp
            chat_room.save()

        # Serialize the new message
        serializer = ChatRoomMessageSerializer(new_message, context={'user': user})
        message_data = serializer.data

        return {'message': message_data, 'sender': BareAccountDetailsSerializer(requesting_user).data, 'reciever':  BareAccountDetailsSerializer(requested_user).data}

    except BaseUser.DoesNotExist:
        return {'error': 'User account not found. Please verify the account details.'}
    
    except Principal.DoesNotExist:
        # Handle the case where the requested principal account does not exist.
        return {'error': 'a principal account with the provided credentials does not exist, please check the account details and try again'}

    except Admin.DoesNotExist:
        # Handle the case where the requested admin account does not exist.
        return {'error': 'an admin account with the provided credentials does not exist, please check the account details and try again'}

    except Teacher.DoesNotExist:
        # Handle the case where the requested teacher account does not exist.
        return {'error': 'a teacher account with the provided credentials does not exist, please check the account details and try again'}

    except Student.DoesNotExist:
        # Handle the case where the requested student account does not exist.
        return {'error': 'a student account with the provided credentials does not exist, please check the account details and try again'}

    except Parent.DoesNotExist:
        # Handle the case where the requested parent account does not exist.
        return {'error': 'a parent account with the provided credentials does not exist, please check the account details and try again'}

    except Exception as e:
        return {'error': str(e)}
    
