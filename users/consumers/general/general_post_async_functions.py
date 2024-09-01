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
from access_tokens.models import AccessToken
from users.models import BaseUser, Principal, Admin, Teacher, Student, Parent
from schools.models import School
from grades.models import Grade
from terms.models import Term
from subjects.models import Subject
from classes.models import Classroom
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
def submit_attendance(user, role, details):
    try:
        if role not in ['PRINCIPAL', 'ADMIN', 'TEACHER']:
            return {"error": 'could not proccess your request.. your account either has insufficient permissions or is invalid for the action you are trying to perform'}

        # Get the appropriate model for the requesting user's role from the mapping.
        Model = role_specific_maps.account_access_control_mapping[role]

        requesting_user = BaseUser.objects.get(account_id=user)

        if details.get('class') == 'submitting my own classes data' and role == 'TEACHER':
            # Build the queryset for the requesting account with the necessary related fields.
            requesting_account = Teacher.objects.prefetch_related('taught_classes').get(account_id=user)
          
            classroom = requesting_account.taught_classes.prefetch_related('attendances').filter(register_class=True).first()
            if not classroom:
                return {"error": _("could not proccess your request. the account making the request has no register class assigned to it")}

        elif details.get('class') and role in ['PRINCIPAL', 'ADMIN']:
            # Build the queryset for the requesting account with the necessary related fields.
            requesting_account = Model.objects.select_related('school').only('school').get(account_id=user)

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
            # Get the appropriate model for the requesting user's role from the mapping.
            Model = role_specific_maps.account_access_control_mapping[role]

            requesting_account = Model.objects.select_related('school').get(account_id=user)
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
    
