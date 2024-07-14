# python 
from decouple import config
import base64
import time

# httpx
import httpx

# channels
from channels.db import database_sync_to_async

# django
from django.core.cache import cache
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.contrib.auth.hashers import check_password
from django.db.models import Q
from django.db import IntegrityError, transaction
from django.utils.dateparse import parse_time

# simple jwt
from rest_framework_simplejwt.tokens import AccessToken as decode, TokenError
from rest_framework_simplejwt.exceptions import TokenError

# models 
from users.models import CustomUser
from schools.models import School
from balances.models import Balance
from auth_tokens.models import AccessToken
from email_bans.models import EmailBan
from timetables.models import Session, Schedule, TeacherSchedule
from grades.models import Grade, Subject

# serilializers
from users.serializers import SecurityInfoSerializer, PrincipalCreationSerializer, AccountUpdateSerializer, IDSerializer, ProfileSerializer, UsersSerializer, AccountCreationSerializer, ProfilePictureSerializer
from timetables.serializers import SchedulesSerializer, SessoinsSerializer
from grades.serializers import GradesSerializer

# utility functions 
from authentication.utils import generate_otp, verify_user_otp, validate_user_email, is_valid_human_name
from email_bans.serializers import EmailBansSerializer, EmailBanSerializer


@database_sync_to_async
def fetch_grades(user):

    try:
        account = CustomUser.objects.get(account_id=user)
        grades = Grade.objects.filter(school=account.school)
        serializer = GradesSerializer(grades, many=True)

        return { 'grades': serializer.data }
        
    except CustomUser.DoesNotExist:
        return { 'error': 'account with the provided credentials does not exist' }
    
    except Exception as e:
        return { 'error': str(e) }
    

@database_sync_to_async
def search_accounts(user, role):

    try:
        if role not in ['ADMIN', 'TEACHER']:
            return { "error" : 'invalid role request' }
        
        account = CustomUser.objects.get(account_id=user)

        # Get the school admin users
        if role == 'ADMIN':
            accounts = CustomUser.objects.filter( Q(role='ADMIN') | Q(role='PRINCIPAL'), school=account.school).exclude(account_id=user)
    
        if role == 'TEACHER':
            accounts = CustomUser.objects.filter(role=role, school=account.school)

        serializer = UsersSerializer(accounts, many=True)
        return { "users" : serializer.data }
        
    except CustomUser.DoesNotExist:
        return { 'error': 'account with the provided credentials does not exist' }
    
    except Exception as e:
        return { 'error': str(e) }


@database_sync_to_async
def create_teacher_schedule(user, details):

    try:
        sessions = details['sessions']
        day_of_week = details['day'].upper()
        account_id = details['account_id']

        if not sessions or not day_of_week or not account_id:
            return { "error" : 'missing information' }

        if day_of_week not in [ 'MONDAY', 'TUESDAY', 'WEDNESDAY', 'THURSDAY', 'FRIDAY', 'SATURDAY', 'SUNDAY']:
            return { "error" : 'invalid schedule day' }

        admin = CustomUser.objects.get(account_id=user)
        account = CustomUser.objects.get(account_id=account_id, role='TEACHER')

        if account.school != admin.school:
            return { "error" : 'unauthorized access.. permission denied' }

        with transaction.atomic():
            
            schedule = Schedule(day=day_of_week)
            schedule.save()  # Save to generate a unique schedule_id
            
            # Iterate over the sessions in the provided data
            for session_info in sessions:
                
                # Convert the start and end times to Time objects
                start_time = parse_time(f"{session_info['startTime']['hour']}:{session_info['startTime']['minute']}:{session_info['startTime']['second']}")
                end_time = parse_time(f"{session_info['endTime']['hour']}:{session_info['endTime']['minute']}:{session_info['endTime']['second']}")
                
                # Create a new Session object
                session = Session(
                    type=session_info['class'],
                    classroom=session_info.get('classroom'),  # Using .get() in case 'classroom' is not provided
                    session_from=start_time,
                    session_till=end_time
                )
                session.save()
                
                # Add the session to the schedule's sessions
                schedule.sessions.add(session)
            
            # Save the schedule again to commit the added sessions
            schedule.save()

            # Check if the teacher already has a schedule for the provided day
            existing_teacher_schedule = TeacherSchedule.objects.filter(teacher=account, schedules__day=day_of_week)

            for schedules in existing_teacher_schedule:
                # Remove the specific schedules for that day
                schedules.schedules.filter(day=day_of_week).delete()

            # Check if the teacher already has a TeacherSchedule object
            teacher_schedule, created = TeacherSchedule.objects.get_or_create(teacher=account)

            # If the object was created, a new unique teacher_schedule_id will be generated
            if created:
                teacher_schedule.save()

            # Add the new schedule to the teacher's schedules
            teacher_schedule.schedules.add(schedule)

            # Save the TeacherSchedule object to commit any changes
            teacher_schedule.save()

        # Return a success response
        return {'message': 'teacher schedule successfully created'}
        
    except ValidationError as e:
        # Handle specific known validation errors
        return {'error': str(e)}
    
    except CustomUser.DoesNotExist:
        return { 'error': 'account with the provided credentials does not exist' }
    
    except Exception as e:
        return { 'error': str(e) }


@database_sync_to_async
def delete_teacher_schedule(user, schedule_id):

    try:
        admin = CustomUser.objects.get(account_id=user)
        
        # Retrieve the schedule object
        schedule = Schedule.objects.get(schedule_id=schedule_id)

        # Retrieve the TeacherSchedule object linked to this schedule
        teacher_schedule = schedule.teacher_linked_to.first()

        # Check if the user has permission to delete the schedule
        if admin.school != teacher_schedule.teacher.school:
            return {"error": 'permission denied'}

        # Delete the schedule
        schedule.delete()
        
        # Return a success response
        return {'message': 'Schedule deleted successfully'}
        
    except CustomUser.DoesNotExist:
        return { 'error': 'account with the provided credentials does not exist' }
    
    except Exception as e:
        return { 'error': str(e) }
    

@database_sync_to_async
def search_teacher_schedules(user, account_id):

    try:
        admin = CustomUser.objects.get(account_id=user)
        account  = CustomUser.objects.get(account_id=account_id)

        if account.role != 'TEACHER' or  admin.school != account.school:
            return { "error" : 'unauthorized access.. permission denied' }
        
        if hasattr(account, 'teacher_schedule'):
        
            teacher_schedule = account.teacher_schedule
            schedules = teacher_schedule.schedules.all().order_by('day')
            serializer = SchedulesSerializer(schedules, many=True)
            schedules_data = serializer.data
        
            # Return the serialized data
            return {"schedules": schedules_data}
        
        else:
            # If there is no associated TeacherSchedule, return an empty list
            return {"schedules": []}
        
    except CustomUser.DoesNotExist:
        return { 'error': 'account with the provided credentials does not exist' }
    
    except Exception as e:
        return { 'error': str(e) }
    

@database_sync_to_async
def search_account_profile(user, account_id):

    try:
        admin = CustomUser.objects.get(account_id=user)
        account  = CustomUser.objects.get(account_id=account_id)

        if account.role == 'FOUNDER' or (account.role != 'PARENT' and admin.school != account.school) or (account.role == 'PARENT' and not account.children.filter(school=admin.school).exists()):
            return { "error" : 'unauthorized access.. permission denied' }

        # return the users profile
        serializer = ProfileSerializer(instance=account)
        return { "user" : serializer.data }
        
    except CustomUser.DoesNotExist:
        return { 'error': 'account with the provided credentials does not exist' }
    
    except Exception as e:
        return { 'error': str(e) }
    
    
@database_sync_to_async
def search_account_id(user, account_id):

    try:
        admin = CustomUser.objects.get(account_id=user)
        account  = CustomUser.objects.get(account_id=account_id)

        if account.role == 'FOUNDER' or (account.role != 'PARENT' and admin.school != account.school) or (account.role == 'PARENT' and not account.children.filter(school=admin.school).exists()):
            return { "error" : 'unauthorized access.. permission denied' }

        # return the users profile
        serializer = IDSerializer(instance=account)
        return { "user" : serializer.data }
        
    except CustomUser.DoesNotExist:
        return { 'error': 'account with the provided credentials does not exist' }
    
    except Exception as e:
        return { 'error': str(e) }


@database_sync_to_async
def create_grade(user, grade, subjects):

    try:
        account = CustomUser.objects.get(account_id=user)
        
        with transaction.atomic():
            level = Grade.objects.create(grade=grade, school=account.school)
            level.save()

            if subjects:
                for subject in subjects:
                    item = Subject.objects.create(subject=subject, grade=level)
                    item.save()
            
        return { 'message': 'grade successfully created. you can now add student accounts, subjects, classes and so much more..' }
               
    except CustomUser.DoesNotExist:
        return { 'error': 'account with the provided credentials does not exist' }
    
    except Exception as e:
        return { 'error': str(e) }

    
@database_sync_to_async
def create_account(user, details):

    try:
        account = CustomUser.objects.get(account_id=user)

        details['school'] = account.school.id
        
        serializer = AccountCreationSerializer(data=details)
        
        if serializer.is_valid():

            # Extract validated data
            validated_data = serializer.validated_data
            
            with transaction.atomic():
                # Try to create the user using the manager's method
                user = CustomUser.objects.create_user(**validated_data)
            
            return {'user' : user}
            
        return {"error" : serializer.errors}
    
    except IntegrityError as e:
        return {'error': 'account with the provided email address already exists'}
           
    except CustomUser.DoesNotExist:
        return { 'error': 'account with the provided credentials does not exist' }
    
    except Exception as e:
        return { 'error': str(e) }


@database_sync_to_async
def update_account(user, updates, account_id):

    try:        
        admin = CustomUser.objects.get(account_id=user)
        account  = CustomUser.objects.get(account_id=account_id)

        if account.role == 'FOUNDER' or (account.role in ['PRINCIPAL', 'ADMIN'] and admin.role != 'PRINCIPAL') or (account.role != 'PARENT' and admin.school != account.school) or account.role == 'PARENT':
            return { "error" : 'unauthorized access.. permission denied' }
        
        serializer = AccountUpdateSerializer(instance=account, data=updates)
        
        if serializer.is_valid():
            
            with transaction.atomic():
                serializer.save()
                account.refresh_from_db()  # Refresh the user instance from the database
            
            serializer = IDSerializer(instance=account)
            return { "user" : serializer.data }
            
        return {"error" : serializer.errors}
    
    except IntegrityError as e:
        return {'error': 'account with the provided email address already exists'}
    
    except CustomUser.DoesNotExist:
        return { 'error': 'account with the provided credentials does not exist' }
    
    except Exception as e:
        return { 'error': str(e) }
    
    
@database_sync_to_async
def delete_account(user, account_id):

    try:
        admin = CustomUser.objects.get(account_id=user)
        account  = CustomUser.objects.get(account_id=account_id)

        if account.role == 'FOUNDER' or (account.role in ['PRINCIPAL', 'ADMIN'] and admin.role != 'PRINCIPAL') or (account.role != 'PARENT' and admin.school != account.school) or account.role == 'PARENT':
            return { "error" : 'unauthorized access.. permission denied' }
        
        account.delete()
                            
        return {"message" : 'account successfully deleted'}
        
    except CustomUser.DoesNotExist:
        return { 'error': 'account with the provided credentials does not exist' }
    
    except Exception as e:
        return { 'error': str(e) }