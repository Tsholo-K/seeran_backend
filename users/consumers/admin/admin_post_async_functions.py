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

# mappings
from users.maps import role_specific_maps

# queries
from users.complex_queries import queries


@database_sync_to_async
def create_grade(user, role, details):
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
    try:
        # Get the appropriate model and related fields (select_related and prefetch_related)
        # for the requesting user's role from the mapping.
        Model = role_specific_maps.account_access_control_mapping[role]

        # Retrieve the user and related school in a single query using select_related
        requesting_account = Model.objects.select_related('school').only('school').get(account_id=user)

        grade = Grade.objects.get(grade_id=details.get('grade'), school=requesting_account.school)

        # Add the school ID to the term details
        details['school'] = requesting_account.school.pk
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
        classroom = Classroom.objects.select_related('grade').only('grade__grade').get(class_id=details.get('class'), school=admin.school)

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
def create_account(user, role, details):

    try:
        if details.get('role') not in ['ADMIN', 'TEACHER', 'STUDENT']:
            return {"error": 'could not proccess your request, the provided account role is invalid'}

        if details['role'] == 'ADMIN' and role != 'PRINCIPAL':
            return {"error": 'could not proccess your request, your accounts role does not have sufficient permission to perform this action'}
        
        # Get the appropriate model and related fields (select_related and prefetch_related)
        # for the requesting user's role from the mapping.
        Model = role_specific_maps.account_access_control_mapping[role]

        # Retrieve the user and related school in a single query using select_related
        requesting_account = Model.objects.select_related('school').only('school').get(account_id=user)

        details['school'] = requesting_account.school.pk

        if details['role'] == 'STUDENT':
            grade = Grade.objects.get(grade_id=details.get('grade'), school=requesting_account.school)
            details['grade'] = grade.pk

        # Get the appropriate model and related fields (select_related and prefetch_related)
        # for the requesting user's role from the mapping.
        Model, Serializer = role_specific_maps.account_creation_model_and_serializer_mapping[details['role']]

        serializer = Serializer(data=details)
        if serializer.is_valid():
            with transaction.atomic():
                user = Model.objects.create(**serializer.validated_data)

            if details['role'] == 'STUDENT' and not details.get('email'):
                return {'message' : 'the students account has been successfully created, accounts with no email addresses can not '}
            
            return {'user' : user}
            
        # Return serializer errors if the data is not valid, format it as a string
        return {"error": '; '.join([f"{key}: {', '.join(value)}" for key, value in serializer.errors.items()])}
               
    except Principal.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'a principal account with the provided credentials does not exist, please check the account details and try again'}
                   
    except Admin.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'an admin account with the provided credentials does not exist, please check the account details and try again'}
        
    except Grade.DoesNotExist:
        # Handle the case where the provided grade ID does not exist
        return {'error': 'a grade in your school with the provided credentials does not exist. please check the grade details and try again.'}

    except ValidationError as e:
        # Handle validation errors separately with meaningful messages
        return {"error": e.messages[0].lower() if isinstance(e.messages, list) and e.messages else str(e).lower()}

    except Exception as e:
        # Handle any unexpected errors with a general error message
        return {'error': str(e)}


@database_sync_to_async
def link_parent(user, role, details):
    try:    
        # Get the appropriate model and related fields (select_related and prefetch_related)
        # for the requesting user's role from the mapping.
        Model = role_specific_maps.account_access_control_mapping[role]

        # Retrieve the user and related school in a single query using select_related
        requesting_account = Model.objects.select_related('school').only('school').get(account_id=user)

        student = Student.objects.prefetch_related('parents').get(account_id=details.get('student'), school=requesting_account.school)

        # Check if the child already has two or more parents linked
        student_parent_count = student.parents.count()
        if student_parent_count >= 2:
            return {"error": "the provided student account has reached the maximum number of linked parents. please unlink one of the existing parents to link a new one"}
        
        # Check if an account with the provided email already exists
        existing_parent = Parent.objects.filter(email=details.get('email')).first()
        if existing_parent:
            return {'alert': {'name': existing_parent.name.title(), 'surname': existing_parent.surname.title()}}

        details['role'] = 'PARENT'
        
        serializer = ParentAccountCreationSerializer(data=details)
        if serializer.is_valid():
            with transaction.atomic():
                parent = Parent.objects.create(**serializer.validated_data)
                parent.save()
                
                parent.children.add(student)

            return {'user' : parent}
            
        # Return serializer errors if the data is not valid, format it as a string
        return {"error": '; '.join([f"{key}: {', '.join(value)}" for key, value in serializer.errors.items()])}
               
    except Principal.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'a principal account with the provided credentials does not exist, please check the account details and try again'}
                   
    except Admin.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'an admin account with the provided credentials does not exist, please check the account details and try again'}
                                      
    except Student.DoesNotExist:
        # Handle the case where the requested student account does not exist.
        return {'error': 'A student account with the provided credentials does not exist, please check the account details and try again'}

    except Parent.DoesNotExist:
        # Handle the case where the requested parent account does not exist.
        return {'error': 'A parent account with the provided credentials does not exist, please check the account details and try again'}

    except ValidationError as e:
        # Handle validation errors separately with meaningful messages
        return {"error": e.messages[0].lower() if isinstance(e.messages, list) and e.messages else str(e).lower()}

    except Exception as e:
        # Handle any unexpected errors with a general error message
        return {'error': str(e)}
        
    
@database_sync_to_async
def delete_account(user, role, details):
    try:
        if details.get('role') not in ['ADMIN', 'TEACHER', 'STUDENT']:
            return {"error": 'could not proccess your request, the provided account role is invalid'}

        if details['role'] == 'ADMIN' and role != 'PRINCIPAL':
            return {"error": 'could not proccess your request, your accounts role does not have sufficient permission to perform this action'}

        # Get the appropriate model for the requesting user's role from the mapping.
        Model, select_related, prefetch_related = role_specific_maps.account_model_and_attr_mapping[role]

        # Build the queryset for the requesting account with the necessary related fields.
        requesting_account = queries.account_and_its_attr_query_build(Model, select_related, prefetch_related).get(account_id=user)

        if details['role'] in ['ADMIN', 'TEACHER', 'STUDENT']:
            # Get the appropriate model for the requested user's role from the mapping.
            Model, select_related, prefetch_related = role_specific_maps.account_model_and_attr_mapping[details['role']]

            # Build the queryset for the requested account with the necessary related fields.
            requested_account = queries.account_and_its_attr_query_build(Model, select_related, prefetch_related).get(account_id=details.get('account'))

            # Check if the requesting user has permission to update the requested user's account.
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
    try:
        # Get the appropriate model and related fields (select_related and prefetch_related)
        # for the requesting user's role from the mapping.
        Model = role_specific_maps.account_access_control_mapping[role]

        # Retrieve the user and related school in a single query using select_related
        requesting_account = Model.objects.select_related('school').only('school').get(account_id=user)

        if details.get('group schedule'):
            group_schedule = GroupSchedule.objects.get(group_schedule_id=details['group schedule'], grade__school=requesting_account.school)
        
        elif details.get('teacher'):
            teacher = Teacher.objects.get(account_id=details['teacher'], school=requesting_account.school)

        else:
            return {"error": 'could not proccess your request, invalid information provided'}

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
            
            if details.get('group schedule'):
                group_schedule.schedules.filter(day=day).delete()
                group_schedule.schedules.add(schedule)
                
                response = {'message': 'a new schedule has been added to the group\'s weekly schedules. all subscribed students should be able to view all the sessions concerning the schedule when they visit their schedules again.'}

            elif details.get('teacher'):
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
    