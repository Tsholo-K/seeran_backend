# python 

# httpx

# channels
from channels.db import database_sync_to_async

# django
from django.db import transaction
from django.core.exceptions import ValidationError

# simple jwt

# models 
from users.models import Principal, Admin, Teacher, Student, Parent
from student_group_timetables.models import StudentGroupTimetable
from classes.models import Classroom
from grades.models import Grade
from terms.models import Term
from subjects.models import Subject

# serilializers
from grades.serializers import UpdateGradeSerializer, UpdateTermSerializer, GradeDetailsSerializer, TermSerializer, UpdateSubjectSerializer, SubjectDetailsSerializer
from classes.serializers import UpdateClassSerializer

# checks
from users.checks import permission_checks

# mappings
from users.maps import role_specific_maps

# queries
from users.complex_queries import queries


@database_sync_to_async
def update_grade_details(user, role, details):
    try:
        # Get the appropriate model for the requesting user's role
        Model = role_specific_maps.account_access_control_mapping[role]

        # Retrieve the user and related school in a single query using select_related
        requesting_account = Model.objects.select_related('school').only('school').get(account_id=user)

        grade = Grade.objects.get(grade_id=details.get('grade'), school=requesting_account.school)

        # Initialize the serializer with the existing school instance and incoming data
        serializer = UpdateGradeSerializer(instance=grade, data=details)
        if serializer.is_valid():
            with transaction.atomic():
                serializer.save()
            
            # Serialize the grade
            serialized_grade = GradeDetailsSerializer(grade).data
            
            # Return the serialized grade in a dictionary
            return {'grade': serialized_grade, "message": "grade details have been successfully updated"}
        
        # Return serializer errors if the data is not valid, format it as a string
        return {"error": '; '.join([f"{key}: {', '.join(value)}" for key, value in serializer.errors.items()])}
               
    except Principal.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'a principal account with the provided credentials does not exist, please check the account details and try again'}
                   
    except Admin.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'an admin account with the provided credentials does not exist, please check the account details and try again'}
                       
    except Grade.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'an grade for your school with the provided credentials does not exist, please check the grade details and try again'}

    except ValidationError as e:
        # Handle validation errors separately with meaningful messages
        return {"error": e.messages[0].lower() if isinstance(e.messages, list) and e.messages else str(e).lower()}

    except Exception as e:
        # Handle any unexpected errors with a general error message
        return {'error': str(e)}
    

@database_sync_to_async
def update_term_details(user, role, details):
    try:
        # Get the appropriate model for the requesting user's role
        Model = role_specific_maps.account_access_control_mapping[role]

        # Retrieve the user and related school in a single query using select_related
        requesting_account = Model.objects.select_related('school').only('school').get(account_id=user)

        term = Term.objects.get(term_id=details.get('term'), school=requesting_account.school)

        # Initialize the serializer with the existing school instance and incoming data
        serializer = UpdateTermSerializer(instance=term, data=details)
        # Validate the incoming data
        if serializer.is_valid():
            # Use an atomic transaction to ensure the database is updated safely
            with transaction.atomic():
                serializer.save()
                    
            # Serialize the school terms
            serialized_term = TermSerializer(term).data

            return {'term': serialized_term, "message": "school term details have been successfully updated" }
        
        # Return serializer errors if the data is not valid, format it as a string
        return {"error": '; '.join([f"{key}: {', '.join(value)}" for key, value in serializer.errors.items()])}
               
    except Principal.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'a principal account with the provided credentials does not exist, please check the account details and try again'}
                   
    except Admin.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'an admin account with the provided credentials does not exist, please check the account details and try again'}
                       
    except Term.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'a term for your school with the provided credentials does not exist, please check the term details and try again'}

    except ValidationError as e:
        # Handle validation errors separately with meaningful messages
        return {"error": e.messages[0].lower() if isinstance(e.messages, list) and e.messages else str(e).lower()}

    except Exception as e:
        # Handle any unexpected errors with a general error message
        return {'error': str(e)}


@database_sync_to_async
def update_subject_details(user, role, details):
    try:
        # Get the appropriate model for the requesting user's role
        Model = role_specific_maps.account_access_control_mapping[role]

        # Retrieve the user and related school in a single query using select_related
        requesting_account = Model.objects.select_related('school').only('school').get(account_id=user)

        subject = Subject.objects.get(subject_id=details.get('subject'), grade__school=requesting_account.school)

        # Initialize the serializer with the existing school instance and incoming data
        serializer = UpdateSubjectSerializer(instance=subject, data=details)
        # Validate the incoming data
        if serializer.is_valid():
            # Use an atomic transaction to ensure the database is updated safely
            with transaction.atomic():
                serializer.save()
            
            # Serialize the subject
            serialized_subject = SubjectDetailsSerializer(subject).data
            
            # Return the serialized grade in a dictionary
            return {'subject': serialized_subject, "message": "subject details have been successfully updated"}
        
        # Return serializer errors if the data is not valid, format it as a string
        return {"error": '; '.join([f"{key}: {', '.join(value)}" for key, value in serializer.errors.items()])}
               
    except Principal.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'a principal account with the provided credentials does not exist, please check the account details and try again'}
                   
    except Admin.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'an admin account with the provided credentials does not exist, please check the account details and try again'}
        
    except Subject.DoesNotExist:
        # Handle case where the subject does not exist
        return {'error': 'a subject in your school with the provided credentials does not exist.'}

    except ValidationError as e:
        # Handle validation errors separately with meaningful messages
        return {"error": e.messages[0].lower() if isinstance(e.messages, list) and e.messages else str(e).lower()}

    except Exception as e:
        # Handle any unexpected errors with a general error message
        return {'error': str(e)}
    

@database_sync_to_async
def update_account(user, role, details):
    try:
        if details.get('role') not in ['ADMIN', 'TEACHER', 'STUDENT', 'PARENT']:
            return {"error": 'could not proccess your request, the provided account role is invalid'}

        if details['role'] == 'ADMIN' and role == 'ADMIN':
            return {"error": 'could not proccess your request, your accounts role does not have enough permissions to perform this action'}

        # Get the model, select_related, and prefetch_related fields based on the requesting user's role.
        Model, select_related, prefetch_related = role_specific_maps.account_model_and_attr_mapping[role]

        # Retrieve the user and related school in a single query using select_related
        requesting_account = queries.account_and_its_attr_query_build(Model, select_related, prefetch_related).get(account_id=user)

        # Get the model, select_related, and prefetch_related fields based on the requested user's role.
        Model, select_related, prefetch_related = role_specific_maps.account_model_and_attr_mapping[details['role']]

        # Retrieve the requested user's account from the database.
        requested_account = queries.account_and_its_attr_query_build(Model, select_related, prefetch_related).get(account_id=details.get('account'))
        
        # Check if the requesting user has permission to view the requested user's profile.
        permission_error = permission_checks.check_update_details_permissions(requesting_account, requested_account)
        if permission_error:
            return permission_error
        
        # Get the appropriate serializer
        Serializer = role_specific_maps.account_update_serializer_mapping[details['role']]

        # Serialize the requested user's profile for returning in the response.
        serializer = Serializer(instance=requested_account, data=details['updates'])
        if serializer.is_valid():
            with transaction.atomic():
                serializer.save()
            
            # Get the appropriate serializer
            Serializer = role_specific_maps.account_details_serializer_mapping[details['role']]

            # Serialize the requested user's profile for returning in the response.
            serialized_user = Serializer(instance=requested_account).data

            return {"user" : serialized_user}
            
        # Return serializer errors if the data is not valid, format it as a string
        return {"error": '; '.join([f"{key}: {', '.join(value)}, okay it must be the serializer" for key, value in serializer.errors.items()])}
               
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
def update_class(user, role, details):
    try:
        # Get the appropriate model for the requesting user's role
        Model = role_specific_maps.account_access_control_mapping[role]

        # Retrieve the user and related school in a single query using select_related
        requesting_account = Model.objects.select_related('school').only('school').get(account_id=user)

        classroom = Classroom.objects.get(class_id=details.get('class'), school=requesting_account.school)

        serializer = UpdateClassSerializer(instance=classroom, data=details.get('updates'))
        if serializer.is_valid():
            with transaction.atomic():
                serializer.save()

                if details['updates']['teacher']:
                    if details['updates']['teacher'] == 'remove teacher':
                        classroom.update_teacher(teacher=None)
                    else:
                        classroom.update_teacher(teacher=details['updates']['teacher'])

            return {"message" : 'classroom details have been successfully updated'}
            
        # Return serializer errors if the data is not valid, format it as a string
        return {"error": '; '.join([f"{key}: {', '.join(value)}" for key, value in serializer.errors.items()])}
               
    except Principal.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'a principal account with the provided credentials does not exist, please check the account details and try again'}
                   
    except Admin.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'an admin account with the provided credentials does not exist, please check the account details and try again'}
    
    except Classroom.DoesNotExist:
        # Handle case where the classroom does not exist
        return {'error': 'a classroom in your school with the provided credentials does not exist. please check the classroom details and try again.'}

    except Exception as e:
        return { 'error': str(e) }


@database_sync_to_async
def update_class_students(user, role, details):
    try:
        students_list = details.get('students', '').split(', ')
        if not students_list or students_list == ['']:
            return {'error': 'your request could not be proccessed.. no students were provided'}
        
        # Get the appropriate model for the requesting user's role
        Model = role_specific_maps.account_access_control_mapping[role]

        # Retrieve the user and related school in a single query using select_related
        requesting_account = Model.objects.select_related('school').only('school').get(account_id=user)

        classroom = Classroom.objects.select_related('grade', 'subject').get(class_id=details.get('class'), school=requesting_account.school)

        with transaction.atomic():
            # Check for validation errors and perform student updates
            error_message = classroom.update_students(students_list=students_list, remove=details.get('remove'))
            
        if error_message:
            return {'error': error_message}

        return {'message': f'Students successfully {"removed from" if details.get("remove") else "added to"} the grade {classroom.grade.grade}, group {classroom.group} {"register" if classroom.register_class else classroom.subject.subject} class'.lower()}
               
    except Principal.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'a principal account with the provided credentials does not exist, please check the account details and try again'}
                   
    except Admin.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'an admin account with the provided credentials does not exist, please check the account details and try again'}
    
    except Classroom.DoesNotExist:
        # Handle case where the classroom does not exist
        return {'error': 'a classroom in your school with the provided credentials does not exist. please check the classroom details and try again.'}

    except Exception as e:
        return {'error': str(e)}


@database_sync_to_async
def add_students_to_group_schedule(user, role, details):
    try:
        # Get the list of student IDs from the details
        students_list = details.get('students', '').split(', ')
        if not students_list or students_list == ['']:
            return {'error': 'your request could not be proccessed.. no students were provided'}

        # Get the appropriate model for the requesting user's role
        Model = role_specific_maps.account_access_control_mapping[role]

        # Retrieve the user and related school in a single query using select_related
        requesting_account = Model.objects.select_related('school').only('school').get(account_id=user)

        # Retrieve the group schedule object with related grade and school for permission check
        group_schedule = StudentGroupTimetable.objects.prefetch_related('students').select_related('grade').get(group_schedule_id=details.get('group_schedule_id'), grade__school=requesting_account.school)
        
        # Retrieve the existing students in the group schedule
        existing_students = group_schedule.students.filter(account_id__in=students_list).values_list('account_id', flat=True)
        
        if existing_students:
            existing_students_str = ', '.join(existing_students)
            return {'error': f'Invalid request. The following students are already in this class: {existing_students_str}. Please review the list of students and try again.'}
        
        students_to_add = Student.objects.filter(account_id__in=students_list, school=requesting_account.school, grade=group_schedule.grade)        
        
        # Add students to the group schedule within a transaction
        with transaction.atomic():
            group_schedule.students.add(*students_to_add)
        
        return {'message': 'students successfully added to group schedule.'}
               
    except Principal.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'a principal account with the provided credentials does not exist, please check the account details and try again'}
                   
    except Admin.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'an admin account with the provided credentials does not exist, please check the account details and try again'}
            
    except StudentGroupTimetable.DoesNotExist:
        # Handle the case where the provided group schedule ID does not exist
        return {'error': 'A group schedule in your school with the provided credentials does not exist. Please check the group schedule details and try again.'}

    except Exception as e:
        return {'error': str(e)}


@database_sync_to_async
def remove_students_from_group_schedule(user, role, details):
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
        # Get the list of student IDs from the details
        students_list = details.get('students', '').split(', ')
        if not students_list or students_list == ['']:
            return {'error': 'your request could not be proccessed.. no students were provided'}

        # Retrieve the user and related school in a single query using select_related
        if role == 'PRINCIPAL':
            admin = Principal.objects.select_related('school').only('school').get(account_id=user)
        else:
            admin = Admin.objects.select_related('school').only('school').get(account_id=user)

        # Retrieve the group schedule object with related grade and school for permission check
        group_schedule = StudentGroupTimetable.objects.select_related('grade').get(group_schedule_id=details.get('group_schedule_id'), grade__school=admin.school)

        # Retrieve the students that need to be removed in a single query for efficiency
        students_to_remove = Student.objects.filter(account_id__in=students_list, school=admin.school, grade=group_schedule.grade)

        # Remove students from the group schedule within a transaction
        with transaction.atomic():
            group_schedule.students.remove(*students_to_remove)
        
        return {'message': 'students successfully removed from group schedule.'}
               
    except Principal.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'a principal account with the provided credentials does not exist, please check the account details and try again'}
                   
    except Admin.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'an admin account with the provided credentials does not exist, please check the account details and try again'}
            
    except StudentGroupTimetable.DoesNotExist:
        # Handle the case where the provided group schedule ID does not exist
        return {'error': 'A group schedule in your school with the provided credentials does not exist. Please check the group schedule details and try again.'}

    except Exception as e:
        return {'error': str(e)}

