# python 

# httpx

# channels
from channels.db import database_sync_to_async

# django
from django.db import transaction
from django.utils.dateparse import parse_time
from django.core.exceptions import ValidationError

# simple jwt

# models 
from users.models import CustomUser
from timetables.models import Session, Schedule, TeacherSchedule, GroupSchedule
from grades.models import Grade, Term, Subject
from classes.models import Classroom

# serilializers
from users.serializers import AccountCreationSerializer, StudentAccountCreationSerializer, ParentAccountCreationSerializer
from grades.serializers import GradeCreationSerializer, TermCreationSerializer, SubjectCreationSerializer
from classes.serializers import ClassCreationSerializer
from announcements.serializers import AnnouncementCreationSerializer

# utility functions 
from authentication.utils import validate_user_email


@database_sync_to_async
def create_term(user, details):
    """
    Asynchronously creates a new school term associated with the provided user's school and grade.

    This function fetches the school associated with the user and attempts to create a new term
    using the provided details. The process is wrapped in a database transaction for safety.
    It handles various exceptions such as non-existent users, validation errors, and unexpected exceptions.

    Args:
        user (str): The account ID of the user.
        details (dict): A dictionary containing the details required to create a new term.

    Returns:
        dict: A dictionary containing either a success message or an error message.
    """
    try:
        # Use select_related and only to fetch the school reference efficiently
        account = CustomUser.objects.select_related('school').only('school').get(account_id=user)
        grade = Grade.objects.only('pk').get(grade_id=details.get('grade'), school=account.school)

        # Add the school ID to the term details
        details['school'] = account.school.pk
        details['grade'] = grade.pk

        # Initialize the serializer with the incoming data
        serializer = TermCreationSerializer(data=details)
        
        if serializer.is_valid():
            return {'message': {**serializer.validated_data}}
            # Using atomic transaction to ensure data integrity
            with transaction.atomic():
                # Create the new term using the validated data
                term = Term.objects.create(**serializer.validated_data)
            
            return {'message': f"term {term.term} has been successfully created for your schools grade {term.grade.grade}"}
            
        # Return serializer errors if the data is not valid, format it as a string
        return {"error": '; '.join([f"{key}: {', '.join(value)}" for key, value in serializer.errors.items()])}
       
    except CustomUser.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'An account with the provided credentials does not exist, please check the account details and try again'}
            
    except Grade.DoesNotExist:
        return { 'error': 'grade with the provided credentials does not exist' }

    except ValidationError as e:
        # Handle validation errors separately with meaningful messages
        return {"error": e.messages[0].lower() if isinstance(e.messages, list) and e.messages else str(e).lower()}
    
    except Exception as e:
        # Handle any unexpected errors with a general error message
        return {'error': str(e).lower()}
    
    
@database_sync_to_async
def create_account(user, details):

    try:
        if details.get('role') not in ['ADMIN', 'TEACHER']:
            return {"error": "invalid account role"}
        
        account = CustomUser.objects.select_related('school').only('school').get(account_id=user)
        details['school'] = account.school.pk
        
        serializer = AccountCreationSerializer(data=details)
        
        if serializer.is_valid():
            with transaction.atomic():
                user = CustomUser.objects.create_user(**serializer.validated_data)
            
            return {'user' : user } # return user to be used by email sending functions
                
        return {"error" : serializer.errors}
    
    except CustomUser.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'An account with the provided credentials does not exist, please check the account details and try again'}

    except Exception as e:
        # Handle any unexpected errors with a general error message
        return {'error': str(e)}


@database_sync_to_async
def create_student_account(user, details):

    try:
        account = CustomUser.objects.select_related('school').only('school').get(account_id=user)
        grade = Grade.objects.get(grade_id=details.get('grade'), school=account.school)

        details['school'] = account.school.pk
        details['grade'] = grade.pk
        details['role'] = 'STUDENT'

        serializer = StudentAccountCreationSerializer(data=details)
        
        if serializer.is_valid():
            with transaction.atomic():
                user = CustomUser.objects.create_user(**serializer.validated_data)
            
            if details.get('email'):
                return {'user' : user }
            
            else:
                return {'message' : 'student account successfully created.. you can now link a parent, add to classes and much more'}
            
        return {"error" : serializer.errors}
    
    except CustomUser.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'An account with the provided credentials does not exist, please check the account details and try again'}
    
    except Grade.DoesNotExist:
        return { 'error': 'grade with the provided credentials does not exist' }

    except Exception as e:
        # Handle any unexpected errors with a general error message
        return {'error': str(e)}


@database_sync_to_async
def link_parent(user, details):

    try:
        if not validate_user_email(details.get('email')):
            return {'error': 'Invalid email format'}
    
        # Check if an account with the provided email already exists
        existing_parent = CustomUser.objects.filter(email=details.get('email')).first()
        if existing_parent:
            if existing_parent.role != 'PARENT':
                return {"error": "an account with the provided email address already exists, but the accounts role is not parent"}
            return {'alert': 'There is already a parent account created with the provided email address', 'parent': existing_parent.account_id}
       
        account = CustomUser.objects.select_related('school').only('school').get(account_id=user)
        child = CustomUser.objects.get(account_id=details.get('child'), school=account.school, role='STUDENT')

        # Check if the child already has two or more parents linked
        parent_count = CustomUser.objects.filter(children=child, role='PARENT').count()
        if parent_count >= 2:
            return {"error": "maximum number of linked parents reached for the provided student account"}

        details['role'] = 'PARENT'
        
        serializer = ParentAccountCreationSerializer(data=details)
        
        if serializer.is_valid():
            
            with transaction.atomic():
                parent = CustomUser.objects.create_user(**serializer.validated_data)
                parent.children.add(child)

            return {'user' : parent}
            
        return {"error" : serializer.errors}
    
    except CustomUser.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'An account with the provided credentials does not exist, please check the account details and try again'}

    except Exception as e:
        # Handle any unexpected errors with a general error message
        return {'error': str(e)}
        
    
@database_sync_to_async
def delete_account(user, details):

    try:
        account = CustomUser.objects.select_related('school').only('school').get(account_id=user)
        requested_user  = CustomUser.objects.select_related('school').only('school').get(account_id=details.get('account_id'))

        if requested_user.role == 'FOUNDER' or (requested_user.role in ['PRINCIPAL', 'ADMIN'] and account.role != 'PRINCIPAL') or (requested_user.role != 'PARENT' and account.school != requested_user.school) or (requested_user.role == 'PARENT' and not requested_user.children.filter(school=account.school).exists()):
            return { "error" : 'unauthorized action.. permission denied' }
        
        if requested_user.role == 'PARENT' and requested_user.children.exists():
            return { "error" : 'the parent account is still linked to a student account.. permission denied' }

        requested_user.delete()
                            
        return {"message" : 'account successfully deleted'}
    
    except CustomUser.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'An account with the provided credentials does not exist, please check the account details and try again'}

    except Exception as e:
        # Handle any unexpected errors with a general error message
        return {'error': str(e)}


@database_sync_to_async
def unlink_parent(user, details):
    """
    Unlink a parent account from a student account.

    Args:
        user (str): The account ID of the user making the request.
        details (dict): A dictionary containing the account IDs of the parent and student to be unlinked.

    Returns:
        dict: A dictionary containing either a success message or an error message.
    """
    try:
        # Fetch the account of the user making the request
        account = CustomUser.objects.select_related('school').only('school').get(account_id=user)

        # Fetch the student account using the provided child ID
        child = CustomUser.objects.select_related('school').only('school').get(account_id=details.get('child_id'))

        # Ensure the specified account is a student and belongs to the same school
        if child.role != 'STUDENT' or account.school != child.school:
            return {"error": "the specified student account is either not a student or does not belong to your school. please ensure you are attempting to unlink a parent from a student enrolled in your school"}

        # Fetch the parent account using the provided parent ID
        parent = CustomUser.objects.get(account_id=details.get('parent_id'))

        # Ensure the specified account is a student and belongs to the same school
        if parent.role != 'PARENT':
            return {"error": "unauthorized action, the specified parent account is either not a parent. please ensure you are attempting to unlink a parent from a student"}

        # Remove the child from the parent's list of children
        parent.children.remove(child)

        return {"message": "the parent account has been successfully unlinked. the account will no longer be associated with the student or have access to the student's information"}

    except CustomUser.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'an account with the provided credentials does not exist, please check the account details and try again'}

    except Exception as e:
        # Handle any unexpected errors
        return {'error': str(e)}


@database_sync_to_async
def create_grade(user, details):
    """
    Creates a new grade for a school based on the provided details.

    Args:
        user (str): The account ID of the user attempting to create the grade.
        details (dict): A dictionary containing grade details, including 'grade' and other necessary fields.

    Returns:
        dict: A dictionary containing a success message if the grade is created,
              or an error message if something goes wrong.
    """
    try:
        # Retrieve the user and related school in a single query using select_related
        account = CustomUser.objects.select_related('school').only('school').get(account_id=user)

        # Check if the grade already exists for the school using exists() to avoid fetching unnecessary data
        if Grade.objects.filter(grade=details.get('grade'), school_id=account.school_id).exists():
            return {"error": f"grade {details.get('grade')} already exists for your school. duplicate grades are not permitted."}

        # Set the school field in the details to the user's school ID
        details['school'] = account.school_id

        # Serialize the details for grade creation
        serializer = GradeCreationSerializer(data=details)

        # Validate the serialized data
        if serializer.is_valid():
            # Create the grade within a transaction to ensure atomicity
            with transaction.atomic():
                Grade.objects.create(**serializer.validated_data)
            
            return {"message": f"Grade {details.get('grade')} has been successfully created for your school."}
        
        # Return errors if the serializer validation fails
        return {"error": serializer.errors}

    except CustomUser.DoesNotExist:
        # Handle case where the user account does not exist
        return {'error': 'an account with the provided credentials does not exist. please check the account details and try again.'}
    
    except ValidationError as e:
        if isinstance(e.messages, list) and e.messages:
            return {"error": e.messages[0]}  # Return the first error message
        else:
            return {"error": str(e)}  # Handle as a single error message

    except Exception as e:
        # Handle any unexpected errors with a general error message
        return {'error': str(e)}


@database_sync_to_async
def create_subject(user, details):

    try:
        if not details.get('subject'):
            return {"error": "could not process request.. no subject was provided"}
           
        # Retrieve the user and related school in a single query using select_related
        account = CustomUser.objects.select_related('school').only('school').get(account_id=user)
        grade = Grade.objects.select_related('school').only('school').get(grade_id=details.get('grade'))

        # Check if the grade is from the same school as the user making the request
        if account.school != grade.school:
            return {"error": "permission denied. you can only access or update details about grades from your own school"}

        # Check if the subject already exists for the school using exists() to avoid fetching unnecessary data
        if Subject.objects.filter(subject=details.get('subject'), grade=grade).exists():
            return {"error": f"{details.get('subject')} subject already exists for grade {grade.grade} in your school. duplicate subjects in a grade is not permitted".lower()}

        # Set the school and grade fields
        details['grade'] = grade.pk

        # Serialize the details for grade creation
        serializer = SubjectCreationSerializer(data=details)

        # Validate the serialized data
        if serializer.is_valid():
            # Create the grade within a transaction to ensure atomicity
            with transaction.atomic():
                Subject.objects.create(**serializer.validated_data)
            
            return {"message": f"{details.get('subject')} subject has been successfully created for grade {grade.grade} in your school".lower()}
        
        # Return errors if the serializer validation fails
        return {"error": serializer.errors}
               
    except Grade.DoesNotExist:
        return { 'error': 'grade with the provided credentials does not exist' }
    
    except CustomUser.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'An account with the provided credentials does not exist, please check the account details and try again'}

    except Exception as e:
        # Handle any unexpected errors with a general error message
        return {'error': str(e)}
    

@database_sync_to_async
def create_class(user, details):
    """
    Creates a new class, either a register class or a subject class, based on the provided details.

    Args:
        user (str): The account ID of the user making the request.
        details (dict): A dictionary containing:
            - classroom_teacher (str): The account ID of the teacher for the class (optional).
            - grade_id (str): The ID of the grade.
            - register (bool): A boolean indicating if the class is a register class.
            - group (str): The group identifier for the class.
            - classroom (str): The classroom identifier.
            - subject_id (str): The ID of the subject (optional, required if register is False).

    Returns:
        dict: A dictionary containing a success message or an error message.

    Raises:
        CustomUser.DoesNotExist: If the user or teacher with the provided account ID does not exist.
        Grade.DoesNotExist: If the grade with the provided grade ID does not exist.
        Subject.DoesNotExist: If the subject with the provided subject ID does not exist (when creating a subject class).
        Exception: For any other unexpected errors.
    """
    try:
        # Retrieve the account making the request
        account = CustomUser.objects.select_related('school').get(account_id=user)

        # Retrieve the grade and validate school ownership
        grade = Grade.objects.select_related('school').get(grade_id=details.get('grade'))
        if account.school != grade.school:
            return {"error": "permission denied. the specified grade does not belong to your school."}

        if details.get('register_class'):
            details['subject'] = None
            response = {'message': f'register class for grade {grade.grade} created successfully. you can now add students and track attendance.'}
        
        elif details.get('subject'):
            # Retrieve the subject and validate it against the grade
            subject = Subject.objects.select_related('grade').get(subject_id=details.get('subject'))
            
            details['subject'] = subject.pk
            details['register_class'] = False
            response = {'message': f'class for grade {grade.grade} {subject.subject} created successfully.. you can now add students and track performance.'.lower()}
        
        else:
            return {"error": "invalid classroom creation details. please provide all required information and try again."}

        # Set the school and grade fields
        details.update({'school': account.school.pk, 'grade': grade.pk})

        # If a teacher is specified, update the teacher for the class
        if details.get('teacher'):
            details['teacher'] = CustomUser.objects.get(account_id=details['teacher'], school=account.school).pk

        # Serialize and validate the data
        serializer = ClassCreationSerializer(data=details)
        if serializer.is_valid():
            # Create the class within a transaction
            with transaction.atomic():
                Classroom.objects.create(**serializer.validated_data)
            
            return response
        
        return {"error": serializer.errors}

    except CustomUser.DoesNotExist:
        # Handle case where the user account does not exist
        return {'error': 'an account with the provided credentials does not exist. please check the account details and try again.'}
    
    except Grade.DoesNotExist:
        return {'error': 'a grade with the provided credentials does not exist. please check the grade details and try again.'}
    
    except Subject.DoesNotExist:
        return {'error': 'a subject with the provided credentials does not exist. please check the subject details and try again.'}
    
    except ValidationError as e:
        return {"error": e.messages[0].lower() if isinstance(e.messages, list) and e.messages else str(e).lower()}
    
    except Exception as e:
        # Handle any unexpected errors with a general error message
        return {'error': str(e)}
    

@database_sync_to_async
def delete_class(user, details):
    try:
        # Retrieve the account making the request
        account = CustomUser.objects.get(account_id=user)

        # Retrieve the grade
        classroom = Classroom.objects.get(class_id=details.get('class'))

        if account.school != classroom.school:
            return { "error" : 'you do not have permission to perform this action because the specified classroom does not belong to your school. please ensure you are attempting to create a group schedule in a grade within your own school' }

        response = {'message': f'grade {classroom.grade.grade} classroom deleted successfully, the classroom will no longer be accessible or available in your schools data'}
        classroom.delete()

        return response
               
    except CustomUser.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'An account with the provided credentials does not exist, please check the account details and try again'}
    
    except Classroom.DoesNotExist:
        # Handle case where the grade does not exist
        return {'error': 'classroom with the provided credentials does not exist'}

    except Exception as e:
        # Handle any other unexpected errors
        return {'error': str(e).lower()}


@database_sync_to_async
def create_schedule(user, details):
    """
    Creates a schedule for a teacher or a group based on the provided details.

    Args:
        user (str): The account ID of the user creating the schedule.
        details (dict): A dictionary containing the schedule details.
            - 'day' (str): The day of the week for the schedule.
            - 'for_group' (bool): Indicates whether the schedule is for a group.
            - 'group_schedule_id' (str, optional): The ID of the group schedule (if for_group is True).
            - 'account_id' (str, optional): The account ID of the teacher (if for_group is False).
            - 'sessions' (list): A list of session details, each containing:
                - 'class' (str): The type of class for the session.
                - 'classroom' (str, optional): The classroom for the session.
                - 'startTime' (dict): A dictionary with 'hour', 'minute', and 'second' for the start time.
                - 'endTime' (dict): A dictionary with 'hour', 'minute', and 'second' for the end time.

    Returns:
        dict: A response dictionary with a 'message' key for success or an 'error' key for any issues.
    """
    try:
        # Validate the day
        day = details.get('day', '').upper()
        if day not in Schedule.DAY_OF_THE_WEEK_ORDER:
            return {"error": 'The provided day for the schedule is invalid, please check that the day falls under any day in the Gregorian calendar'}

        account = CustomUser.objects.select_related('school').get(account_id=user)

        if details.get('for_group'):
            # Validate group schedule and access permissions
            group_schedule = GroupSchedule.objects.select_related('grade__school').get(group_schedule_id=details.get('group_schedule_id'))
            if group_schedule.grade.school != account.school:
                return {"error": 'the specified group schedule does not belong to your school. please ensure you are attempting to create schedules for a group schedule from your school'}
        
        else:
            # Validate teacher account and permissions
            teacher = CustomUser.objects.select_related('school').get(account_id=details.get('account_id'))
            if teacher.school != account.school or teacher.role != 'TEACHER':
                return {"error": 'the specified teacher account is either not a teacher or does not belong to your school. please ensure you are attempting to create schedules for a teacher enrolled in your school'}

        with transaction.atomic():
            # Create a new schedule
            schedule = Schedule.objects.create(day=day, day_order=Schedule.DAY_OF_THE_WEEK_ORDER[day])

            sessions = [
                Session(
                    type=session_info['class'],
                    classroom=session_info.get('classroom'),
                    session_from=parse_time(f"{session_info['startTime']['hour']}:{session_info['startTime']['minute']}:{session_info['startTime']['second']}"),
                    session_till=parse_time(f"{session_info['endTime']['hour']}:{session_info['endTime']['minute']}:{session_info['endTime']['second']}")
                ) for session_info in details.get('sessions', [])
            ]
            Session.objects.bulk_create(sessions)
            schedule.sessions.add(*sessions)
            
            if details.get('for_group'):
                group_schedule.schedules.filter(day=day).delete()
                group_schedule.schedules.add(schedule)
                
                return {'message': 'a new schedule has been added to the group\'s weekly schedules. all subscribed students should be able to view all the sessions concerning the schedule when they visit their schedules again.'}

            else:
                teacher_schedule, created = TeacherSchedule.objects.get_or_create(teacher=teacher)
                if not created:
                    teacher_schedule.schedules.filter(day=day).delete()
                teacher_schedule.schedules.add(schedule)

                return {'message': 'a new schedule has been added to the teacher\'s weekly schedules. they should be able to view all the sessions concerning the schedule when they visit their schedules again.'}

    except CustomUser.DoesNotExist:
        # Handle case where user account does not exist
        return {'error': 'an account with the provided credentials does not exist, please check the account details and try again'}

    except GroupSchedule.DoesNotExist:
        # Handle case where group schedule does not exist
        return {'error': 'a group schedule with the provided credentials does not exist, please check the group details and try again'}

    except Exception as e:
        return {'error': f'An unexpected error occurred: {str(e)}'}


@database_sync_to_async
def create_group_schedule(user, details):
    """
    Creates a group schedule for a specified grade.

    Args:
        user (str): The account ID of the user creating the group schedule.
        details (dict): A dictionary containing the group schedule details.
            - 'group_name' (str): The name of the group.
            - 'grade_id' (str): The ID of the grade.

    Returns:
        dict: A response dictionary with a 'message' key for success or an 'error' key for any issues.
    """
    try:
        # Fetch account and grade with related objects in a single query
        account = CustomUser.objects.select_related('school').get(account_id=user)
        grade = Grade.objects.select_related('school').get(grade_id=details.get('grade_id'))

        if account.school != grade.school:
            return { "error" : 'you do not have permission to perform this action because the specified grade does not belong to your school. please ensure you are attempting to create a group schedule in a grade within your own school' }

        with transaction.atomic():
            GroupSchedule.objects.create(group_name=details.get('group_name'), grade=grade)

        return {'message': 'you can now add individual daily schedules and subscribe students in the grade to the group schedule for a shared weekly schedule'}

    except CustomUser.DoesNotExist:
        # Handle case where user account does not exist
        return {'error': 'an account with the provided credentials does not exist, please check the account details and try again'}

    except Grade.DoesNotExist:
        # Handle case where group schedule does not exist
        return {'error': 'a grade with the provided credentials does not exist, please check the grade details and try again'}

    except Exception as e:
        return {'error': f'An unexpected error occurred: {str(e)}'}
    

@database_sync_to_async
def delete_schedule(user, details):
    """
    Deletes a specific schedule for a teacher or group.

    Args:
        user (str): The account ID of the user requesting the deletion.
        details (dict): A dictionary containing the schedule details.
            - 'schedule_id' (str): The ID of the schedule to be deleted.
            - 'for_group' (bool): Indicates whether the schedule is for a group.

    Returns:
        dict: A response dictionary with a 'message' key for success or an 'error' key for any issues.
    """
    try:
        account = CustomUser.objects.select_related('school').get(account_id=user)

        if details.get('for_group'):
            schedule = Schedule.objects.prefetch_related('group_linked_to__grade__school').get(schedule_id=details.get('schedule_id'))

            group_schedule = schedule.group_linked_to.first()
            if not group_schedule or account.school != group_schedule.grade.school:
                return {"error": 'Permission denied. This group schedule belongs to a different school.'}
        else:
            schedule = Schedule.objects.prefetch_related('teacher_linked_to__teacher__school').get(schedule_id=details.get('schedule_id'))
            
            teacher_schedule = schedule.teacher_linked_to.first()
            if not teacher_schedule or account.school_id != teacher_schedule.teacher.school_id:
                return {"error": 'Permission denied. This teacher schedule belongs to a different school.'}

        schedule.delete()

        if details.get('for_group'):
            return {'message': 'the schedule has been successfully deleted from the group schedule and will be removed from schedules of all students subscribed to the group schedule'}
        
        else:
            return {'message': 'the schedule has been successfully deleted from the teachers schedule and will no longer be available to the teacher'}
    
    except CustomUser.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'An account with the provided credentials does not exist, please check the account details and try again'}

    except Schedule.DoesNotExist:
        return {'error': 'Specified schedule not found. Please verify the details and try again.'}

    except Exception as e:
        # Handle any unexpected errors with a general error message
        return {'error': str(e)}


@database_sync_to_async
def delete_group_schedule(user, details):
    """
    Deletes a specific group schedule.

    Args:
        user (str): The account ID of the user requesting the deletion.
        details (dict): A dictionary containing the group schedule details.
            - 'group_schedule_id' (str): The ID of the group schedule to be deleted.

    Returns:
        dict: A response dictionary with a 'message' key for success or an 'error' key for any issues.
    """
    try:
        account = CustomUser.objects.select_related('school').get(account_id=user)
        group_schedule = GroupSchedule.objects.select_related('grade__school').get(group_schedule_id=details.get('group_schedule_id'))

        if account.school != group_schedule.grade.school:
            return {"error": 'Permission denied. This group schedule belongs to a different school.'}

        group_schedule.delete()
        return {'message': 'Group schedule deleted successfully.'}

    except CustomUser.DoesNotExist:
        # Handle case where user account does not exist
        return {'error': 'an account with the provided credentials does not exist, please check the account details and try again'}

    except GroupSchedule.DoesNotExist:
        # Handle case where group schedule does not exist
        return {'error': 'a group schedule with the provided credentials does not exist, please check the group details and try again'}

    except Exception as e:
        return {'error': f'An unexpected error occurred: {str(e)}'}


@database_sync_to_async
def announce(user, details):
    """
    Creates an announcement and associates it with the user and school.

    Args:
        user (str): The unique identifier (account_id) of the user making the request.
        details (dict): A dictionary containing announcement details.

    Returns:
        dict: A dictionary containing a success message or an error message.
    """
    try:
        # Retrieve the user account
        account = CustomUser.objects.select_related('school').get(account_id=user)

        # Add user and school information to the announcement details
        details.update({'announce_by': account.pk, 'school': account.school.pk})

        # Serialize the announcement data
        serializer = AnnouncementCreationSerializer(data=details)

        # Validate and save the announcement within a transaction
        if serializer.is_valid():
            with transaction.atomic():
                serializer.save()
            return {'message': 'The announcement is now available to all users in the school and the parents linked to them.'}
        
        # Return validation errors
        return {"error": serializer.errors}
    
    except CustomUser.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'An account with the provided credentials does not exist, please check the account details and try again'}

    except Exception as e:
        # Handle any unexpected errors with a general error message
        return {'error': str(e)}

    