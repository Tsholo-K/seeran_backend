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
from users.models import BaseUser, Principal, Admin, Teacher, Student, Parent
from schedules.models import Session, Schedule, TeacherSchedule, GroupSchedule
from grades.models import Grade, Term, Subject
from classes.models import Classroom

# serilializers
from users.serializers.admins.admins_serializers import AdminAccountCreationSerializer
from users.serializers.teachers.teachers_serializers import TeacherAccountCreationSerializer
from users.serializers.students.students_serializers import StudentAccountCreationSerializer
from users.serializers.parents.parents_serializers import ParentAccountCreationSerializer
from grades.serializers import GradeCreationSerializer, TermCreationSerializer, SubjectCreationSerializer
from classes.serializers import ClassCreationSerializer
from announcements.serializers import AnnouncementCreationSerializer

# checks
from users.checks import permission_checks


@database_sync_to_async
def create_grade(user, role, details):
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
        if role == 'PRINCIPAL':
            admin = Principal.objects.select_related('school').only('school').get(account_id=user)
        else:
            admin = Admin.objects.select_related('school').only('school').get(account_id=user)

        # Set the school field in the details to the user's school ID
        details['school'] = admin.school.pk

        # Serialize the details for grade creation
        serializer = GradeCreationSerializer(data=details)

        # Validate the serialized data
        if serializer.is_valid():
            # Create the grade within a transaction to ensure atomicity
            with transaction.atomic():
                Grade.objects.create(**serializer.validated_data)
            
            return {"message": f"grade {details.get('grade')} has been successfully created for your school"}
        
        # Return serializer errors if the data is not valid, format it as a string
        return {"error": '; '.join([f"{key}: {', '.join(value)}" for key, value in serializer.errors.items()])}
               
    except Principal.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'a principal account with the provided credentials does not exist, please check the account details and try again'}
                   
    except Admin.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'an admin account with the provided credentials does not exist, please check the account details and try again'}
    
    except ValidationError as e:
        # Handle validation errors separately with meaningful messages
        return {"error": e.messages[0].lower() if isinstance(e.messages, list) and e.messages else str(e).lower()}
    
    except Exception as e:
        # Handle any unexpected errors with a general error message
        return {'error': str(e)}


@database_sync_to_async
def create_subject(user, role, details):

    try:
        # Retrieve the user and related school in a single query using select_related
        if role == 'PRINCIPAL':
            admin = Principal.objects.select_related('school').only('school').get(account_id=user)
        else:
            admin = Admin.objects.select_related('school').only('school').get(account_id=user)

        grade = Grade.objects.get(grade_id=details.get('grade'), school=admin.school)

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
        
        # Return serializer errors if the data is not valid, format it as a string
        return {"error": '; '.join([f"{key}: {', '.join(value)}" for key, value in serializer.errors.items()])}
               
    except Principal.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'a principal account with the provided credentials does not exist, please check the account details and try again'}
                   
    except Admin.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'an admin account with the provided credentials does not exist, please check the account details and try again'}
               
    except Grade.DoesNotExist:
        return { 'error': 'a grade in your school with the provided credentials does not exist' }
    
    except ValidationError as e:
        # Handle validation errors separately with meaningful messages
        return {"error": e.messages[0].lower() if isinstance(e.messages, list) and e.messages else str(e).lower()}

    except Exception as e:
        # Handle any unexpected errors with a general error message
        return {'error': str(e)}
    

@database_sync_to_async
def create_term(user, role, details):
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
        # Retrieve the user and related school in a single query using select_related
        if role == 'PRINCIPAL':
            admin = Principal.objects.select_related('school').only('school').get(account_id=user)
        else:
            admin = Admin.objects.select_related('school').only('school').get(account_id=user)

        grade = Grade.objects.get(grade_id=details.get('grade'), school=admin.school)

        # Add the school ID to the term details
        details['school'] = admin.school.pk
        details['grade'] = grade.pk

        # Initialize the serializer with the incoming data
        serializer = TermCreationSerializer(data=details)
        
        if serializer.is_valid():
            # Using atomic transaction to ensure data integrity
            with transaction.atomic():
                # Create the new term using the validated data
                Term.objects.create(**serializer.validated_data)
            
            return {'message': f"{details.get('subject')} has been successfully created for your schools grade {grade.grade}"}
            
        # Return serializer errors if the data is not valid, format it as a string
        return {"error": '; '.join([f"{key}: {', '.join(value)}" for key, value in serializer.errors.items()])}
               
    except Principal.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'a principal account with the provided credentials does not exist, please check the account details and try again'}
                   
    except Admin.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'an admin account with the provided credentials does not exist, please check the account details and try again'}
        return {'error': 'an account with the provided credentials does not exist, please check the account details and try again'}
            
    except Grade.DoesNotExist:
        return { 'error': 'a grade in your school with the provided credentials does not exist' }

    except ValidationError as e:
        # Handle validation errors separately with meaningful messages
        return {"error": e.messages[0].lower() if isinstance(e.messages, list) and e.messages else str(e).lower()}
    
    except Exception as e:
        # Handle any unexpected errors with a general error message
        return {'error': str(e).lower()}
    

@database_sync_to_async
def create_class(user, role, details):
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
        # Retrieve the user and related school in a single query using select_related
        if role == 'PRINCIPAL':
            admin = Principal.objects.select_related('school').only('school').get(account_id=user)
        else:
            admin = Admin.objects.select_related('school').only('school').get(account_id=user)

        # Retrieve the grade and validate school ownership
        grade = Grade.objects.select_related('school').get(grade_id=details.get('grade'), school=admin.school)

        if details.get('register_class'):
            details['subject'] = None

            response = {'message': f'register class for grade {grade.grade} created successfully. you can now add students and track attendance.'}
        
        elif details.get('subject'):
            # Retrieve the subject and validate it against the grade
            subject = Subject.objects.get(subject_id=details.get('subject'), grade=grade)
            
            details['subject'] = subject.pk
            details['register_class'] = False

            response = {'message': f'class for grade {grade.grade} {subject.subject} created successfully.. you can now add students and track performance.'.lower()}
        
        else:
            return {"error": "invalid classroom creation details. please provide all required information and try again."}

        # Set the school and grade fields
        details.update({'school': admin.school.pk, 'grade': grade.pk})

        # If a teacher is specified, update the teacher for the class
        if details.get('teacher'):
            details['teacher'] = Teacher.objects.get(account_id=details['teacher'], school=admin.school).pk

        # Serialize and validate the data
        serializer = ClassCreationSerializer(data=details)
        if serializer.is_valid():
            # Create the class within a transaction
            with transaction.atomic():
                Classroom.objects.create(**serializer.validated_data)
            
            return response
        
        # Return serializer errors if the data is not valid, format it as a string
        return {"error": '; '.join([f"{key}: {', '.join(value)}" for key, value in serializer.errors.items()])}
               
    except Principal.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'a principal account with the provided credentials does not exist, please check the account details and try again'}
                   
    except Admin.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'an admin account with the provided credentials does not exist, please check the account details and try again'}
               
    except Teacher.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'a teacher account with the provided credentials does not exist, please check the account details and try again'}
    
    except Grade.DoesNotExist:
        return {'error': 'a grade in your school with the provided credentials does not exist. please check the grade details and try again.'}
    
    except Subject.DoesNotExist:
        return {'error': 'a subject in your school with the provided credentials does not exist. please check the subject details and try again.'}
    
    except ValidationError as e:
        # Handle validation errors separately with meaningful messages
        return {"error": e.messages[0].lower() if isinstance(e.messages, list) and e.messages else str(e).lower()}
    
    except Exception as e:
        # Handle any unexpected errors with a general error message
        return {'error': str(e)}
    

@database_sync_to_async
def delete_class(user, role, details):
    try:
        # Retrieve the user and related school in a single query using select_related
        if role == 'PRINCIPAL':
            admin = Principal.objects.select_related('school').only('school').get(account_id=user)
        else:
            admin = Admin.objects.select_related('school').only('school').get(account_id=user)

        # Retrieve the grade
        classroom = Classroom.objects.select_related('grade').get(class_id=details.get('class'), school=admin.school)

        response = {'message': f'grade {classroom.grade.grade} classroom deleted successfully, the classroom will no longer be accessible or available in your schools data'}
        
        with transaction.atomic():
            classroom.delete()

        return response
               
    except Principal.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'a principal account with the provided credentials does not exist, please check the account details and try again'}
                   
    except Admin.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'an admin account with the provided credentials does not exist, please check the account details and try again'}

    except Classroom.DoesNotExist:
        # Handle case where the grade does not exist
        return {'error': 'classroom with the provided credentials does not exist'}
    
    except ValidationError as e:
        # Handle validation errors separately with meaningful messages
        return {"error": e.messages[0].lower() if isinstance(e.messages, list) and e.messages else str(e).lower()}

    except Exception as e:
        # Handle any other unexpected errors
        return {'error': str(e).lower()}    


@database_sync_to_async
def create_admin_account(user, role, details):

    try:
        # Retrieve the user and related school in a single query using select_related
        if role == 'PRINCIPAL':
            admin = Principal.objects.select_related('school').only('school').get(account_id=user)
        else:
            admin = Admin.objects.select_related('school').only('school').get(account_id=user)

        details['school'] = admin.school.pk
        details['role'] = 'ADMIN'

        serializer = AdminAccountCreationSerializer(data=details)
        
        if serializer.is_valid():
            with transaction.atomic():
                user = Admin.objects.create(**serializer.validated_data)
            
            return {'user' : user}
            
        # Return serializer errors if the data is not valid, format it as a string
        return {"error": '; '.join([f"{key}: {', '.join(value)}" for key, value in serializer.errors.items()])}
               
    except Principal.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'a principal account with the provided credentials does not exist, please check the account details and try again'}
                   
    except Admin.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'an admin account with the provided credentials does not exist, please check the account details and try again'}
    
    except ValidationError as e:
        # Handle validation errors separately with meaningful messages
        return {"error": e.messages[0].lower() if isinstance(e.messages, list) and e.messages else str(e).lower()}

    except Exception as e:
        # Handle any unexpected errors with a general error message
        return {'error': str(e)}


@database_sync_to_async
def create_teacher_account(user, role, details):

    try:
        # Retrieve the user and related school in a single query using select_related
        if role == 'PRINCIPAL':
            admin = Principal.objects.select_related('school').only('school').get(account_id=user)
        else:
            admin = Admin.objects.select_related('school').only('school').get(account_id=user)

        details['school'] = admin.school.pk
        details['role'] = 'TEACHER'

        serializer = TeacherAccountCreationSerializer(data=details)
        if serializer.is_valid():
            with transaction.atomic():
                user = Teacher.objects.create(**serializer.validated_data)
            
            return {'user' : user}
            
        # Return serializer errors if the data is not valid, format it as a string
        return {"error": '; '.join([f"{key}: {', '.join(value)}" for key, value in serializer.errors.items()])}
               
    except Principal.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'a principal account with the provided credentials does not exist, please check the account details and try again'}
                   
    except Admin.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'an admin account with the provided credentials does not exist, please check the account details and try again'}
    
    except ValidationError as e:
        # Handle validation errors separately with meaningful messages
        return {"error": e.messages[0].lower() if isinstance(e.messages, list) and e.messages else str(e).lower()}

    except Exception as e:
        # Handle any unexpected errors with a general error message
        return {'error': str(e)}


@database_sync_to_async
def create_student_account(user, role, details):

    try:
        # Retrieve the user and related school in a single query using select_related
        if role == 'PRINCIPAL':
            admin = Principal.objects.select_related('school').only('school').get(account_id=user)
        else:
            admin = Admin.objects.select_related('school').only('school').get(account_id=user)

        grade = Grade.objects.get(grade_id=details.get('grade'), school=admin.school)

        details['school'] = admin.school.pk
        details['grade'] = grade.pk
        details['role'] = 'STUDENT'

        serializer = StudentAccountCreationSerializer(data=details)
        
        if serializer.is_valid():
            with transaction.atomic():
                user = Student.objects.create(**serializer.validated_data)
            
            if details.get('email'):
                return {'user' : user }
            
            else:
                return {'message' : 'student account successfully created.. you can now link a parent, add to classes, track performance and much more'}
            
        # Return serializer errors if the data is not valid, format it as a string
        return {"error": '; '.join([f"{key}: {', '.join(value)}" for key, value in serializer.errors.items()])}
               
    except Principal.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'a principal account with the provided credentials does not exist, please check the account details and try again'}
                   
    except Admin.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'an admin account with the provided credentials does not exist, please check the account details and try again'}
    
    except Grade.DoesNotExist:
        return { 'error': 'a grade in your school with the provided credentials does not exist' }
    
    except ValidationError as e:
        # Handle validation errors separately with meaningful messages
        return {"error": e.messages[0].lower() if isinstance(e.messages, list) and e.messages else str(e).lower()}

    except Exception as e:
        # Handle any unexpected errors with a general error message
        return {'error': str(e)}


@database_sync_to_async
def link_parent(user, role, details):

    try:    
        # Check if an account with the provided email already exists
        existing_parent = BaseUser.objects.filter(email=details.get('email')).first()
        if existing_parent:
            if existing_parent.role != 'PARENT':
                return {"error": "an account with the provided email address already exists, but the accounts role is not parent"}
            return {'alert': 'There is already a parent account created with the provided email address', 'parent': existing_parent.account_id}
       
        # Retrieve the user and related school in a single query using select_related
        if role == 'PRINCIPAL':
            admin = Principal.objects.select_related('school').only('school').get(account_id=user)
        else:
            admin = Admin.objects.select_related('school').only('school').get(account_id=user)

        child = Student.objects.get(account_id=details.get('child'), school=admin.school)

        # Check if the child already has two or more parents linked
        student_parent_count = Parent.objects.filter(children=child).count()
        if student_parent_count >= 2:
            return {"error": "the provided student account has reached the maximum number of linked parents. please unlink one of the existing parents to link a new one"}

        details['role'] = 'PARENT'
        
        serializer = ParentAccountCreationSerializer(data=details)
        
        if serializer.is_valid():
            
            with transaction.atomic():
                parent = Parent.objects.create(**serializer.validated_data)
                parent.children.add(child)

            return {'user' : parent}
            
        # Return serializer errors if the data is not valid, format it as a string
        return {"error": '; '.join([f"{key}: {', '.join(value)}" for key, value in serializer.errors.items()])}
               
    except Principal.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'a principal account with the provided credentials does not exist, please check the account details and try again'}
                   
    except Admin.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'an admin account with the provided credentials does not exist, please check the account details and try again'}
    
    except ValidationError as e:
        # Handle validation errors separately with meaningful messages
        return {"error": e.messages[0].lower() if isinstance(e.messages, list) and e.messages else str(e).lower()}

    except Exception as e:
        # Handle any unexpected errors with a general error message
        return {'error': str(e)}
        
    
@database_sync_to_async
def delete_account(user, role, details):

    try:
        child_model_mapping = {
            'ADMIN': (Admin, 'school', None),
            'TEACHER': (Teacher, 'school', None),
            'STUDENT': (Student, 'school', None),
        }

        # Retrieve the user and related school in a single query using select_related
        if role == 'PRINCIPAL':
            requesting_account = Principal.objects.select_related('school').only('school').get(account_id=user)
        else:
            if details.get('role') == 'ADMIN':
                return {"error": 'could not proccess your request, your accounts role does not have enough permissions to perform this action'}
            requesting_account = Admin.objects.select_related('school').only('school').get(account_id=user)

        if details.get('role') in child_model_mapping:
            # Get the model, select_related, and prefetch_related fields based on the requested user's role.
            Model, select_related, prefetch_related = child_model_mapping[details['role']]

            # Initialize the queryset for the requested user's role model.
            queryset = Model.objects
            
            # Apply select_related and prefetch_related as needed for the requested user's account.
            if select_related:
                queryset = queryset.select_related(select_related)
            if prefetch_related:
                queryset = queryset.prefetch_related(*prefetch_related.split(', '))

            # Retrieve the requested user's account from the database.
            requested_account = queryset.get(account_id=details.get('account'))
            
            # Check if the requesting user has permission to view the requested user's profile.
            permission_error = permission_checks.check_update_details_permissions(requesting_account, requested_account)
            if permission_error:
                return permission_error

            with transaction.atomic():
                requested_account.delete()

                if details['role'] == 'ADMIN':
                    requesting_account.school.admin_count = requesting_account.school.principal.count() + requesting_account.school.admins.count()
                elif details['role'] == 'STUDENT':
                    requesting_account.school.student_count = requesting_account.school.students.count()
                elif details['role'] == 'TEACHER':
                    requesting_account.school.teacher_count = requesting_account.school.teachers.count()

                requesting_account.school.save()

            return {"message" : 'account successfully deleted'}
        
        return {"error": 'could not proccess your request, the provided account role is invalid'}
               
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

    except ValidationError as e:
        # Handle validation errors separately with meaningful messages
        return {"error": e.messages[0].lower() if isinstance(e.messages, list) and e.messages else str(e).lower()}

    except Exception as e:
        # Handle any unexpected errors with a general error message
        return {'error': str(e)}


@database_sync_to_async
def unlink_parent(user, role, details):
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
        # Retrieve the user and related school in a single query using select_related
        if role == 'PRINCIPAL':
            admin = Principal.objects.select_related('school').only('school').get(account_id=user)
        else:
            admin = Admin.objects.select_related('school').only('school').get(account_id=user)

        # Fetch the student account using the provided child ID
        student = Student.objects.get(account_id=details.get('child_id'), school=admin.school)

        # Fetch the parent account using the provided parent ID
        parent = Parent.objects.prefetch_related('children').get(account_id=details.get('parent_id'))

        if student not in parent.children.all():
            return {"error": "unauthorized action, the specified student account is not a child of the provided parent account. please ensure you are attempting to unlink a parent from a student"}

        # Remove the child from the parent's list of children
        with transaction.atomic():
            parent.children.remove(student)

        return {"message": "the parent account has been successfully unlinked. the account will no longer be associated with the student or have access to the student's information"}
               
    except Principal.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'a principal account with the provided credentials does not exist, please check the account details and try again'}
                   
    except Admin.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'an admin account with the provided credentials does not exist, please check the account details and try again'}
                   
    except Student.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'a student account in your school with the provided credentials does not exist, please check the account details and try again'}
                   
    except Parent.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'a parent account with the provided credentials does not exist, please check the account details and try again'}
    
    except ValidationError as e:
        # Handle validation errors separately with meaningful messages
        return {"error": e.messages[0].lower() if isinstance(e.messages, list) and e.messages else str(e).lower()}

    except Exception as e:
        # Handle any unexpected errors
        return {'error': str(e)}


@database_sync_to_async
def create_schedule(user, role, details):
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
        # Retrieve the user and related school in a single query using select_related
        if role == 'PRINCIPAL':
            admin = Principal.objects.select_related('school').only('school').get(account_id=user)
        else:
            admin = Admin.objects.select_related('school').only('school').get(account_id=user)

        if details.get('for_group'):
            group_schedule = GroupSchedule.objects.get(group_schedule_id=details.get('group_schedule_id'), grade__school=admin.school)
        
        if details.get('for_teacher'):
            teacher = Teacher.objects.get(account_id=details.get('account_id'), school=admin.school)

        else:
            return {"error": ''}

        # Validate the day
        day = details.get('day', '').upper()
        if day not in Schedule.DAY_OF_THE_WEEK_ORDER:
            return {"error": 'The provided day for the schedule is invalid, please check that the day falls under any day in the Gregorian calendar'}

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
                
                response = {'message': 'a new schedule has been added to the group\'s weekly schedules. all subscribed students should be able to view all the sessions concerning the schedule when they visit their schedules again.'}

            if details.get('for_teacher'):
                teacher_schedule, created = TeacherSchedule.objects.get_or_create(teacher=teacher)
                if not created:
                    teacher_schedule.schedules.filter(day=day).delete()
                teacher_schedule.schedules.add(schedule)

                response = {'message': 'a new schedule has been added to the teacher\'s weekly schedules. they should be able to view all the sessions concerning the schedule when they visit their schedules again.'}
        
        return response
    
    except Principal.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'a principal account with the provided credentials does not exist, please check the account details and try again'}
                   
    except Admin.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'an admin account with the provided credentials does not exist, please check the account details and try again'}
                   
    except Teacher.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'a teacher account in your school with the provided credentials does not exist, please check the account details and try again'}

    except GroupSchedule.DoesNotExist:
        # Handle case where group schedule does not exist
        return {'error': 'a group schedule in your school with the provided credentials does not exist, please check the group details and try again'}
    
    except ValidationError as e:
        # Handle validation errors separately with meaningful messages
        return {"error": e.messages[0].lower() if isinstance(e.messages, list) and e.messages else str(e).lower()}

    except Exception as e:
        return {'error': f'An unexpected error occurred: {str(e)}'}


@database_sync_to_async
def create_group_schedule(user, role, details):
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
        # Retrieve the user and related school in a single query using select_related
        if role == 'PRINCIPAL':
            admin = Principal.objects.select_related('school').only('school').get(account_id=user)
        else:
            admin = Admin.objects.select_related('school').only('school').get(account_id=user)

        grade = Grade.objects.get(grade_id=details.get('grade_id'), school=admin.school)

        with transaction.atomic():
            GroupSchedule.objects.create(group_name=details.get('group_name'), grade=grade)

        return {'message': 'you can now add individual daily schedules and subscribe students in the grade to the group schedule for a shared weekly schedule'}
               
    except Principal.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'a principal account with the provided credentials does not exist, please check the account details and try again'}
                   
    except Admin.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'an admin account with the provided credentials does not exist, please check the account details and try again'}

    except Grade.DoesNotExist:
        # Handle case where group schedule does not exist
        return {'error': 'a grade in your school with the provided credentials does not exist, please check the grade details and try again'}
    
    except ValidationError as e:
        # Handle validation errors separately with meaningful messages
        return {"error": e.messages[0].lower() if isinstance(e.messages, list) and e.messages else str(e).lower()}

    except Exception as e:
        return {'error': f'An unexpected error occurred: {str(e)}'}
    

@database_sync_to_async
def delete_schedule(user, role, details):
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
        # Retrieve the user and related school in a single query using select_related
        if role == 'PRINCIPAL':
            admin = Principal.objects.select_related('school').only('school').get(account_id=user)
        else:
            admin = Admin.objects.select_related('school').only('school').get(account_id=user)

        if details.get('for_group'):
            schedule = Schedule.objects.get(schedule_id=details.get('schedule_id'), group_linked_to__grade__school=admin.school)

            response = {'message': 'the schedule has been successfully deleted from the group schedule and will be removed from schedules of all students subscribed to the group schedule'}
            
        if details.get('for_teacher'):
            schedule = Schedule.objects.get(schedule_id=details.get('schedule_id'), teacher_schedule_linked_to__teacher__school=admin.school)

            response = {'message': 'the schedule has been successfully deleted from the teachers schedule and will no longer be available to the teacher'}
            
        else:
            return {"error": ''}
        
        with transaction.atomic():
            schedule.delete()

        return response
               
    except Principal.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'a principal account with the provided credentials does not exist, please check the account details and try again'}
                   
    except Admin.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'an admin account with the provided credentials does not exist, please check the account details and try again'}

    except Schedule.DoesNotExist:
        # Handle the case where the provided schedule_id does not exist
        return {'error': 'a schedule for your school with the provided credentials does not exist. please verify the details and try again.'}
    
    except ValidationError as e:
        # Handle validation errors separately with meaningful messages
        return {"error": e.messages[0].lower() if isinstance(e.messages, list) and e.messages else str(e).lower()}

    except Exception as e:
        # Handle any unexpected errors with a general error message
        return {'error': str(e)}


@database_sync_to_async
def delete_group_schedule(user, role, details):
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
        # Retrieve the user and related school in a single query using select_related
        if role == 'PRINCIPAL':
            admin = Principal.objects.select_related('school').only('school').get(account_id=user)
        else:
            admin = Admin.objects.select_related('school').only('school').get(account_id=user)

        group_schedule = GroupSchedule.objects.get(group_schedule_id=details.get('group_schedule_id'), grade__school=admin.school)
        
        with transaction.atomic():
            group_schedule.delete()

        return {'message': 'group schedule deleted successfully.'}
               
    except Principal.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'a principal account with the provided credentials does not exist, please check the account details and try again'}
                   
    except Admin.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'an admin account with the provided credentials does not exist, please check the account details and try again'}

    except GroupSchedule.DoesNotExist:
        # Handle case where group schedule does not exist
        return {'error': 'a group schedule for your school with the provided credentials does not exist, please check the group details and try again'}
    
    except ValidationError as e:
        # Handle validation errors separately with meaningful messages
        return {"error": e.messages[0].lower() if isinstance(e.messages, list) and e.messages else str(e).lower()}

    except Exception as e:
        return {'error': str(e)}


@database_sync_to_async
def announce(user, role, details):
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
        # Retrieve the user and related school in a single query using select_related
        if role == 'PRINCIPAL':
            admin = Principal.objects.select_related('school').only('school').get(account_id=user)
        else:
            admin = Admin.objects.select_related('school').only('school').get(account_id=user)

        # Add user and school information to the announcement details
        details.update({'announce_by': admin.pk, 'school': admin.school.pk})

        # Serialize the announcement data
        serializer = AnnouncementCreationSerializer(data=details)

        # Validate and save the announcement within a transaction
        if serializer.is_valid():
            with transaction.atomic():
                serializer.save()

            return {'message': 'the announcement is now available to all users in the school and the parents linked to them.'}
        
        # Return serializer errors if the data is not valid, format it as a string
        return {"error": '; '.join([f"{key}: {', '.join(value)}" for key, value in serializer.errors.items()])}
               
    except Principal.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'a principal account with the provided credentials does not exist, please check the account details and try again'}
                   
    except Admin.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'an admin account with the provided credentials does not exist, please check the account details and try again'}
    
    except ValidationError as e:
        # Handle validation errors separately with meaningful messages
        return {"error": e.messages[0].lower() if isinstance(e.messages, list) and e.messages else str(e).lower()}

    except Exception as e:
        # Handle any unexpected errors with a general error message
        return {'error': str(e)}



# @database_sync_to_async
# def create_admin(details):

#     serializer = AdminCreationSerializer(data=details)

#     if serializer.is_valid():
#         with transaction.atomic():
#             admin = Admin.objects.create(**serializer.validated_data)
#         return {'user': admin}
#     return {"error": serializer.errors}


# @database_sync_to_async
# def create_teacher(details):

#     serializer = TeacherCreationSerializer(data=details)

#     if serializer.is_valid():
#         with transaction.atomic():
#             teacher = Teacher.objects.create(**serializer.validated_data)
#         return {'user': teacher}
#     return {"error": serializer.errors}


# @database_sync_to_async
# def create_student(details):

#     serializer = StudentCreationSerializer(data=details)

#     if serializer.is_valid():
#         with transaction.atomic():
#             student = Student.objects.create(**serializer.validated_data)
#         return {'user': student}
#     return {"error": serializer.errors}

# # Additional functions for other roles like Parent, Principal, Founder, etc.

# @database_sync_to_async
# def create_account(user, details):

#     try:
#         if details.get('role') not in ['ADMIN', 'TEACHER']:
#             return {"error": "invalid account role"}
        
#         # Retrieve the user and related school in a single query using select_related
#         if role == 'PRINCIPAL':
#             admin = Principal.objects.select_related('school').only('school').get(account_id=user)
#         else:
#             admin = Admin.objects.select_related('school').only('school').get(account_id=user)
#         details['school'] = account.school.pk
        
#         serializer = AccountCreationSerializer(data=details)
        
#         if serializer.is_valid():
#             with transaction.atomic():
#                 user = BaseUser.objects.create_user(**serializer.validated_data)
            
#             return {'user' : user } # return user to be used by email sending functions
                
#         return {"error" : serializer.errors}
    
#     except BaseUser.DoesNotExist:
#         # Handle the case where the provided account ID does not exist
#         return {'error': 'An account with the provided credentials does not exist, please check the account details and try again'}

#     except Exception as e:
#         # Handle any unexpected errors with a general error message
#         return {'error': str(e)}
    