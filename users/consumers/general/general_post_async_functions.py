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

# simple jwt
from rest_framework_simplejwt.tokens import AccessToken as decode, TokenError
from rest_framework_simplejwt.exceptions import TokenError

# models 
from auth_tokens.models import AccessToken
from users.models import BaseUser, Principal
from schools.models import School
from classes.models import Classroom
from attendances.models import Absent, Late
from grades.models import Grade, Term, Subject
from chats.models import ChatRoom, ChatRoomMessage
from assessments.models import Topic

# serializers
from users.serializers.general_serializers import BareAccountDetailsSerializer
from chats.serializers import ChatRoomMessageSerializer
from activities.serializers import ActivityCreationSerializer
from assessments.serializers import AssessmentCreationSerializer

# utility functions 

# checks
from users.checks import permission_checks


@database_sync_to_async
def delete_school_account(user, role, details):
    try:
        if role not in ['FOUNDER', 'PRINCIPAL']:
            return {"error": 'could not proccess your request.. your account either has insufficient permissions or is invalid for the action you are trying to perform'}
        
        elif details.get('school') == 'requesting my own school':
            # Retrieve the user and related school in a single query using select_related
            admin = Principal.objects.select_related('school').only('school').get(account_id=user)
            school = admin.school

        else:
            # Retrieve the School instance by school_id from the provided details
            school = School.objects.get(school_id=details.get('school'))

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
def submit_absentes(user, details):

    try:
        account = BaseUser.objects.get(account_id=user)

        if details.get('class_id') == 'requesting_my_own_class':
            classroom = Classroom.objects.select_related('school').get(teacher=account, register_class=True)

            if account.role != 'TEACHER' or classroom.school != account.school:
                return {"error": "unauthorized access. the account making the request has an invalid role or the classroom you are trying to access is not from your school"}

        else:
            if account.role not in ['ADMIN', 'PRINCIPAL']:
                return { "error" : 'unauthorized request.. only the class teacher or school admin can view the attendance records for a class' }

            classroom = Classroom.objects.get(class_id=details.get('class_id'), school=account.school, register_class=True)

        today = timezone.localdate()

        if Absent.objects.filter(date__date=today, classroom=classroom).exists():
            return {'error': 'attendance register for this class has already been subimitted today.. can not resubmit'}

        with transaction.atomic():
            register = Absent.objects.create(submitted_by=account, classroom=classroom)
            if details.get('students'):
                register.absentes = True
                for student in details.get('students').split(', '):
                    register.absent_students.add(BaseUser.objects.get(account_id=student))

            register.save()
        
        return { 'message': 'attendance register successfully taken for today'}

    except BaseUser.DoesNotExist:
        # Handle case where the user or teacher account does not exist
        return {'error': 'The account with the provided credentials does not exist. Please check the account details and try again.'}
    
    except Classroom.DoesNotExist:
        return { 'error': 'class with the provided credentials does not exist' }

    except Exception as e:
        return { 'error': str(e) }


@database_sync_to_async
def submit_late_arrivals(user, details):

    try:
        if not details.get('students'):
            return {"error" : 'invalid request.. no students provided.. at least one student is needed to be marked as late'}

        account = BaseUser.objects.get(account_id=user)

        if details.get('class_id') == 'requesting_my_own_class':
            classroom = Classroom.objects.select_related('school').get(teacher=account, register_class=True)

            if account.role != 'TEACHER' or classroom.school != account.school:
                return {"error": "unauthorized access. the account making the request has an invalid role or the classroom you are trying to access is not from your school"}

        else:
            if account.role not in ['ADMIN', 'PRINCIPAL']:
                return { "error" : 'unauthorized request.. only the class teacher or school admin can view the attendance records for a class' }

            classroom = Classroom.objects.get(class_id=details.get('class_id'), school=account.school, register_class=True)

        today = timezone.localdate()

        absentes = Absent.objects.filter(date__date=today, classroom=classroom).first()
        if not absentes:
            return {'error': 'attendance register for this class has not been submitted today.. can not submit late arrivals before the attendance register'}

        if absentes and not absentes.absent_students.exists():
            return {'error': 'attendance register for this class has all students present or marked as late for today.. can not submit late arrivals when all students are accounted for'}

        register = Late.objects.filter(date__date=today, classroom=classroom).first()
        
        with transaction.atomic():
            if not register:
                register = Late.objects.create(submitted_by=account, classroom=classroom)
                
            for student in details.get('students').split(', '):
                student = BaseUser.objects.get(account_id=student)
                absentes.absent_students.remove(student)
                register.late_students.add(student)

            absentes.save()
            register.save()

        return { 'message': 'students marked as late, attendance register successfully updated'}
               
    except BaseUser.DoesNotExist:
        return { 'error': 'account with the provided credentials does not exist' }
    
    except Classroom.DoesNotExist:
        return { 'error': 'class with the provided credentials does not exist' }

    except Exception as e:
        return { 'error': str(e) }


@database_sync_to_async
def log_activity(user, details):
    """
    Log an activity for a student by an authorized user (Principal, Admin, Teacher).

    Args:
        user (str): The account ID of the user logging the activity.
        details (dict): A dictionary containing the details of the activity. It should include:
            - 'recipient' (str): The account ID of the student for whom the activity is being logged.
            - Additional fields required by the ActivityCreationSerializer.

    Returns:
        dict: A dictionary containing a success message if the activity was logged successfully,
              or an error message if there was an issue.
    """
    try:
        # Retrieve the user account and the student account using select_related to minimize database hits
        account = BaseUser.objects.select_related('school').get(account_id=user)
        student = BaseUser.objects.select_related('school').get(account_id=details.get('recipient'))

        # Ensure the account has a valid role to log activities
        if account.role not in ['PRINCIPAL', 'ADMIN', 'TEACHER']:
            return {"error": "could not proccess your request. you do not have sufficient permissions to log activities."}

        # Ensure the student belongs to the same school and has the 'STUDENT' role
        if account.school != student.school or student.role != 'STUDENT':
            return {"error": "could not proccess your request. the provided student account is either not a student or does not belong to your school. please check the account details and try again."}

        # If the account is a teacher, ensure they are teaching the student and the teacher of the class
        if account.role == 'TEACHER':
                    
            # Determine the classroom based on the request details
            if details.get('class') == 'requesting_my_own_class':
                # Fetch the classroom where the user is the teacher and it is a register class
                classroom = Classroom.objects.select_related('school').filter(teacher=account, register_class=True).first()
                if not classroom:
                    return {"error": _("could not proccess your request. the account making the request has no register class assigned to it")}

            else:
                # Fetch the specific classroom based on class_id and school
                classroom = Classroom.objects.get(class_id=details.get('class'))

            if classroom.school != account.school:
                return {"error": _("could not proccess your request. you are not permitted to access information about classses outside your own school or those you do not teach")}

            if classroom not in account.taught_classes.all() or not account.taught_classes.filter(students=student).exists():
                return {"error": "unauthorized access. you can only log activities for classrooms and students you teach."}
  
            details['classroom'] = classroom.pk

        # Prepare the data for serialization
        details['recipient'] = student.pk
        details['logger'] = account.pk
        details['school'] = account.school.pk

        # Initialize the serializer with the prepared data
        serializer = ActivityCreationSerializer(data=details)

        # Validate the serializer data and save the activity within an atomic transaction
        if serializer.is_valid():
            with transaction.atomic():
                serializer.save()

            return {'message': 'activity successfully logged. the activity is now available to everyone with access to the student\'s data.'}

        # Return validation errors if the serializer is not valid
        return {"error": serializer.errors}

    except BaseUser.DoesNotExist:
        # Handle case where the user or student account does not exist
        return {'error': 'an account with the provided credentials does not exist. Please check the account details and try again.'}

    except Exception as e:
        # Handle any other unexpected exceptions
        return {'error': str(e)}


@database_sync_to_async
def set_assessment(user, details):
    """
    Sets an assessment based on the provided details and user account.

    Args:
        user (str): The account ID of the user setting the assessment.
        details (dict): A dictionary containing all the necessary details to create the assessment.

    Returns:
        dict: A dictionary containing either a success message or an error message.
    """
    try:
        # Retrieve the user's account, including the related school in one query.
        account = BaseUser.objects.select_related('school').get(account_id=user)

        # Ensure the user has the correct role to set an assessment.
        if account.role not in ['PRINCIPAL', 'ADMIN', 'TEACHER']:
            return {"error": "Unauthorized request. You do not have sufficient permissions to set an assessment."}

        # If the user is a teacher, validate their permissions for the specific classroom.
        if account.role == 'TEACHER':
            # Retrieve the classroom and its related grade, subject, and school.
            classroom = Classroom.objects.select_related('grade', 'subject', 'school').get(class_id=details.get('class'))

            # Ensure the teacher is setting the assessment for their own class in their own school.
            if account.school != classroom.school or classroom.teacher != account:
                return {"error": "Unauthorized access. You are not permitted to access or update information about classes outside your own school or those you do not teach."}

            # Update the details dictionary with the related IDs from the classroom.
            details.update({'classroom': classroom.pk, 'grade': classroom.grade.pk, 'subject': classroom.subject.pk})

        else:
            # For non-teacher roles, retrieve and set the grade and subject IDs from the provided details.
            details.update({
                'grade': Grade.objects.values_list('pk', flat=True).get(grade_id=details.get('grade_id')),
                'subject': Subject.objects.values_list('pk', flat=True).get(subject_id=details.get('subject_id')),
            })

        # Update the details dictionary with the user's ID, the term ID, and the school ID.
        details.update({
            'set_by': account.pk,
            'term': Term.objects.values_list('pk', flat=True).get(term=details.get('term'), school=account.school),
            'school': account.school.pk,
        })

        # Initialize the serializer with the prepared data.
        serializer = AssessmentCreationSerializer(data=details)

        # Validate the serializer data and save the assessment within an atomic transaction.
        if serializer.is_valid():
            with transaction.atomic():
                assessment = serializer.save()

                # Retrieve or create topics based on the provided list of topic names.
                topic_names = details.get('topics', '')

                if topic_names:
                    topics_list = [topic.strip() for topic in topic_names.split(',')]
                else:
                    topics_list = []

                existing_topics = Topic.objects.filter(name__in=topics_list)

                # Determine which topics are new and need to be created.
                new_topic_names = set(topics_list) - set(existing_topics.values_list('name', flat=True))
                new_topics = [Topic(name=name) for name in new_topic_names]
                Topic.objects.bulk_create(new_topics)  # Create new topics in bulk.

                # Combine existing and new topics and set them for the assessment.
                all_topics = list(existing_topics) + new_topics
                assessment.topics.set(all_topics)

            return {'message': 'Assessment successfully set. The assessment is now available to everyone affected by its creation.'}

        # Return validation errors if the serializer is not valid.
        return {"error": serializer.errors}

    except BaseUser.DoesNotExist:
        # Handle case where the user or student account does not exist
        return {'error': 'an account with the provided credentials does not exist. Please check the account details and try again.'}

    except Term.DoesNotExist:
        # Handle case where the term does not exist
        return {'error': 'a term with the provided credentials does not exist. Please check the term details and try again.'}

    except Subject.DoesNotExist:
        # Handle case where the subject does not exist
        return {'error': 'a subject with the provided credentials does not exist. Please check the subjects details and try again.'}

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
def text(user, details):
    """
    Handle sending a text message. 
    
    This function performs the following steps:
    1. Retrieves the user making the request and the requested user's account.
    2. Checks if the user has the necessary permissions to send the message.
    3. Retrieves or creates a chat room between the two users.
    4. Checks the last message and updates its 'last' field if necessary.
    5. Creates and saves a new message in the chat room.
    6. Serializes the new message and returns it.
    7. Includes the recipient's account ID in the response for further processing.

    Args:
        user (str): The account ID of the user sending the message.
        details (dict): A dictionary containing the details of the message, including:
            - 'account_id' (str): The account ID of the user to whom the message is sent.
            - 'message' (str): The content of the message.

    Returns:
        dict: A dictionary containing the serialized message data and the recipient's account ID or an error message.
    """
    try:
        # Validate users
        if user == details.get('account_id'):
            return {"error": "validation error. you can not send a text message to yourself, it violates database constraints and is therefore not allowed."}

        # Retrieve the user making the request
        account = BaseUser.objects.get(account_id=user)

        # Retrieve the requested user's account
        requested_user = BaseUser.objects.get(account_id=details.get('account_id'))
        
        # Check permissions
        permission_error = permission_checks.check_message_permissions(account, requested_user)
        if permission_error:
            return {'error': permission_error}

        # Retrieve or create the chat room
        chat_room, created = ChatRoom.objects.get_or_create(user_one=account if account.pk < requested_user.pk else requested_user, user_two=requested_user if account.pk < requested_user.pk else account, defaults={'user_one': account, 'user_two': requested_user})

        with transaction.atomic():
            # Retrieve the last message in the chat room
            last_message = ChatRoomMessage.objects.filter(chat_room=chat_room).order_by('-timestamp').first()
            # Update the last message's 'last' field if it's from the same sender
            if last_message and last_message.sender == account:
                last_message.last = False
                last_message.save()

            # Create the new message
            new_message = ChatRoomMessage.objects.create(sender=account, content=details.get('message'), chat_room=chat_room)

            # Update the chat room's latest message timestamp
            chat_room.latest_message_timestamp = new_message.timestamp
            chat_room.save()

        # Serialize the new message
        serializer = ChatRoomMessageSerializer(new_message, context={'user': user})
        message_data = serializer.data

        return {'message': message_data, 'sender': BareAccountDetailsSerializer(account).data, 'reciever':  BareAccountDetailsSerializer(requested_user).data}

    except BaseUser.DoesNotExist:
        return {'error': 'User account not found. Please verify the account details.'}
    
    except Exception as e:
        return {'error': str(e)}
    
