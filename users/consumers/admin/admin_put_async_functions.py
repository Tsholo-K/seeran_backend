# python 

# httpx

# channels
from channels.db import database_sync_to_async

# django
from django.db import transaction

# simple jwt

# models 
from users.models import CustomUser
from timetables.models import GroupSchedule
from classes.models import Classroom

# serilializers
from users.serializers import AccountUpdateSerializer, AccountIDSerializer, AccountSerializer
from classes.serializers import ClassUpdateSerializer

# utility functions 
from authentication.utils import validate_user_email


@database_sync_to_async
def update_account(user, details):

    try:
        updates = details.get('updates')

        if updates.get('email'):
            if not validate_user_email(updates.get('email')):
                return {'error': 'Invalid email format'}

            if CustomUser.objects.filter(email=updates.get('email')).exists():
                return {"error": "an account with the provided email address already exists"}

        account = CustomUser.objects.get(account_id=user)
        requested_user  = CustomUser.objects.get(account_id=details.get('account_id'))

        if requested_user.role == 'FOUNDER' or (requested_user.role in ['PRINCIPAL', 'ADMIN'] and account.role != 'PRINCIPAL') or (requested_user.role != 'PARENT' and account.school != requested_user.school) or (requested_user.role == 'PARENT' and not requested_user.children.filter(school=account.school).exists()):
            return { "error" : 'unauthorized access.. permission denied' }
        
        serializer = AccountUpdateSerializer(instance=requested_user, data=updates)
        
        if serializer.is_valid():
            
            with transaction.atomic():
                serializer.save()
                requested_user.refresh_from_db()  # Refresh the user instance from the database
            
            serializer = AccountIDSerializer(instance=requested_user)
            return { "user" : serializer.data }
            
        return {"error" : serializer.errors}
    
    except CustomUser.DoesNotExist:
        return { 'error': 'account with the provided credentials does not exist' }
    
    except Exception as e:
        return { 'error': str(e) }


@database_sync_to_async
def update_class(user, details):

    try:
        updates = details.get('updates')

        account = CustomUser.objects.get(account_id=user)
        classroom = Classroom.objects.get(class_id=details.get('class_id'), school=account.school)

        serializer = ClassUpdateSerializer(instance=classroom, data=updates)

        if serializer.is_valid():
            with transaction.atomic():
                serializer.save()

                if updates.get('teacher'):
                    if updates.get('teacher') == 'remove teacher':
                        classroom.update_teacher(teacher=None)
                    else:
                        classroom.update_teacher(teacher=updates['teacher'])

            return {"message" : 'classroom details have been successfully updated'}
            
        return {"error" : serializer.errors}

    except CustomUser.DoesNotExist:
        # Handle case where the user account does not exist
        return {'error': 'an account with the provided credentials does not exist. please check the account details and try again.'}
    
    except Classroom.DoesNotExist:
        # Handle case where the classroom does not exist
        return {'error': 'a classroom with the provided credentials does not exist. please check the classroom details and try again.'}

    except Exception as e:
        return { 'error': str(e) }


@database_sync_to_async
def update_class_students(user, details):
    """
    Adds or removes students to/from a specified classroom.

    Args:
        user (str): The unique identifier (account_id) of the user making the request.
        details (dict): A dictionary containing class and student details.
            - 'class_id' (str): The ID of the classroom.
            - 'students' (str): A comma-separated string of student account IDs to be added.
            - 'register' (bool): Indicates if the classroom is a register class.

    Returns:
        dict: A dictionary containing a success message or an error message.
    """
    try:
        # Retrieve the user account and classroom with related fields
        account = CustomUser.objects.select_related('school').get(account_id=user)
        classroom = Classroom.objects.select_related('school', 'grade', 'subject').get(class_id=details.get('class'))

        # Check permissions 
        if account.school != classroom.school:
            return {"error": "Permission denied. The provided classroom is not from your school"}

        students_list = details.get('students', '').split(', ')
        if not students_list or students_list == ['']:
            return {'error': 'your request could not be proccessed.. no students were provided'}
        
        with transaction.atomic():
            # Check for validation errors and perform student updates
            error_message = classroom.update_students(students_list=students_list, remove=details.get('remove'))
            
        if error_message:
            return {'error': error_message}

        return {'message': f'Students successfully {"removed from" if details.get("remove") else "added to"} the grade {classroom.grade.grade}, group {classroom.group} {"register" if classroom.register_class else classroom.subject.subject} class'.lower()}

    except CustomUser.DoesNotExist:
        # Handle case where the user account does not exist
        return {'error': 'an account with the provided credentials does not exist. please check the account details and try again.'}
    
    except Classroom.DoesNotExist:
        # Handle case where the classroom does not exist
        return {'error': 'a classroom with the provided credentials does not exist. please check the classroom details and try again.'}

    except Exception as e:
        return {'error': str(e)}


@database_sync_to_async
def add_students_to_group_schedule(user, details):
    """
    Adds students to a specified group schedule.

    Args:
        user (str): The unique identifier (account_id) of the user making the request.
        details (dict): A dictionary containing the group schedule and students' details.
            - 'group_schedule_id' (str): The ID of the group schedule.
            - 'students' (str): A comma-separated string of student account IDs to be added.

    Returns:
        dict: A dictionary containing:
            - 'message': A success message if the addition is successful.
            - 'error': An error message if an exception occurs.
    """
    try:
        # Retrieve the user account
        account = CustomUser.objects.select_related('school').get(account_id=user)
        
        # Retrieve the group schedule object with related grade and school for permission check
        group_schedule = GroupSchedule.objects.select_related('grade__school').get(group_schedule_id=details.get('group_schedule_id'))

        # Check if the user has permission to modify the group schedule
        if account.school != group_schedule.grade.school:
            return {"error": 'Permission denied. You can only modify group schedules from your own school.'}
        
        # Get the list of student IDs from the details
        students_list = details.get('students').split(', ')
        
        # Retrieve the existing students in the group schedule
        existing_students = group_schedule.students.filter(account_id__in=students_list).values_list('account_id', flat=True)
        
        if existing_students:
            existing_students_str = ', '.join(existing_students)
            return {'error': f'Invalid request. The following students are already in this class: {existing_students_str}. Please review the list of students and try again.'}
        
        students_to_add = CustomUser.objects.filter(account_id__in=students_list, school=account.school, grade=group_schedule.grade)        
        
        # Add students to the group schedule within a transaction
        with transaction.atomic():
            group_schedule.students.add(*students_to_add)
        
        return {'message': 'Students successfully added to group schedule.'}
        
    except CustomUser.DoesNotExist:
        return {'error': 'An account with the provided credentials does not exist. Please check the account details and try again.'}
            
    except GroupSchedule.DoesNotExist:
        return {'error': 'A group schedule with the provided credentials does not exist. Please check the group schedule details and try again.'}

    except Exception as e:
        return {'error': str(e)}


@database_sync_to_async
def remove_students_from_group_schedule(user, details):
    """
    Removes students from a specified group schedule.

    Args:
        user (str): The unique identifier (account_id) of the user making the request.
        details (dict): A dictionary containing the group schedule and students' details.
            - 'group_schedule_id' (str): The ID of the group schedule.
            - 'students' (str): A comma-separated string of student account IDs to be removed.

    Returns:
        dict: A dictionary containing:
            - 'students': A serialized list of remaining students in the group schedule.
            - 'message': A success message if the removal is successful.
            - 'error': An error message if an exception occurs.
    """
    try:
        # Retrieve the user account
        account = CustomUser.objects.select_related('school').get(account_id=user)
        
        # Retrieve the group schedule object with related grade and school for permission check
        group_schedule = GroupSchedule.objects.select_related('grade__school').get(group_schedule_id=details.get('group_schedule_id'))

        # Check if the user has permission to modify the group schedule
        if account.school != group_schedule.grade.school:
            return {"error": 'Permission denied. You can only modify group schedules from your own school.'}
        
        # Get the list of student IDs from the details
        students_list = details.get('students').split(', ')

        # Retrieve the students that need to be removed in a single query for efficiency
        students_to_remove = CustomUser.objects.filter(account_id__in=students_list, school=account.school, grade=group_schedule.grade)

        # Remove students from the group schedule within a transaction
        with transaction.atomic():
            group_schedule.students.remove(*students_to_remove)
        
        # Serialize the remaining students
        serializer = AccountSerializer(group_schedule.students.all(), many=True)

        return {"students": serializer.data, 'message': 'Students successfully removed from group schedule.'}
        
    except CustomUser.DoesNotExist:
        return {'error': 'An account with the provided credentials does not exist. Please check the account details and try again.'}
            
    except GroupSchedule.DoesNotExist:
        return {'error': 'A group schedule with the provided credentials does not exist. Please check the group schedule details and try again.'}

    except Exception as e:
        return {'error': str(e)}

