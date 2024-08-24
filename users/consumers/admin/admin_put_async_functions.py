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
from timetables.models import GroupSchedule
from classes.models import Classroom
from grades.models import Grade, Term, Subject

# serilializers
from users.serializers import AccountUpdateSerializer, AccountIDSerializer
from grades.serializers import UpdateGradeSerializer, UpdateTermSerializer, GradeDetailsSerializer, TermSerializer, UpdateSubjectSerializer, SubjectDetailsSerializer
from classes.serializers import ClassUpdateSerializer
from schools.serializers import UpdateSchoolAccountSerializer, SchoolIDSerializer

# utility functions 


@database_sync_to_async
def update_school_details(user, role, details):
    """
    Update the school account details associated with the provided user.

    Parameters:
    user (str): The account ID of the user requesting the update.
    details (dict): A dictionary containing the updated school account details.

    Returns:
    dict: A dictionary containing either a success message or an error message.

    - If the update is successful, returns:
        { "message": "School account details have been successfully updated" }

    - If the account does not exist, returns:
        { "error": "An account with the provided credentials does not exist, please check the account details and try again" }

    - If there is any validation error or unexpected error, returns:
        { "error": "Error message describing the issue" }
    """
    try:
        # Retrieve the user and related school in a single query using select_related
        if role == 'PRINCIPAL':
            admin = Principal.objects.select_related('school').only('school').get(account_id=user)
        else:
            admin = Admin.objects.select_related('school').only('school').get(account_id=user)

        # Initialize the serializer with the existing school instance and incoming data
        serializer = UpdateSchoolAccountSerializer(instance=admin.school, data=details)
        # Validate the incoming data
        if serializer.is_valid():
            # Use an atomic transaction to ensure the database is updated safely
            with transaction.atomic():
                serializer.save()
                        
            # Serialize the grade
            serialized_school = SchoolIDSerializer(admin.school).data

            return {'school': serialized_school, "message": "school account details have been successfully updated" }
        
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
def update_grade_details(user, role, details):
    try:
        # Retrieve the user and related school in a single query using select_related
        if role == 'PRINCIPAL':
            admin = Principal.objects.select_related('school').only('school').get(account_id=user)
        else:
            admin = Admin.objects.select_related('school').only('school').get(account_id=user)

        grade = Grade.objects.get(grade_id=details.get('grade'), school=admin.school)

        # Initialize the serializer with the existing school instance and incoming data
        serializer = UpdateGradeSerializer(instance=grade, data=details)
        # Validate the incoming data
        if serializer.is_valid():
            # Use an atomic transaction to ensure the database is updated safely
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
        # Retrieve the user and related school in a single query using select_related
        if role == 'PRINCIPAL':
            admin = Principal.objects.select_related('school').only('school').get(account_id=user)
        else:
            admin = Admin.objects.select_related('school').only('school').get(account_id=user)

        term = Term.objects.get(term_id=details.get('term'), school=admin.school)

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
        # Retrieve the user and related school in a single query using select_related
        if role == 'PRINCIPAL':
            admin = Principal.objects.select_related('school').only('school').get(account_id=user)
        else:
            admin = Admin.objects.select_related('school').only('school').get(account_id=user)

        subject = Subject.objects.get(subject_id=details.get('subject'), grade__school=admin.school)

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
def update_admin_account(user, role, details):

    try:
        # Retrieve the user and related school in a single query using select_related
        if not role == 'PRINCIPAL':
            return { "error" : 'unauthorized access.. permission denied' }
        
        principal = Principal.objects.select_related('school').only('school').get(account_id=user)

        admin  = Admin.objects.get(account_id=details.get('account_id'), school=principal.school)
        
        serializer = AccountUpdateSerializer(instance=admin, data=details.get('updates'))
        if serializer.is_valid():
            
            with transaction.atomic():
                serializer.save()
            
            serialized_admin = AccountIDSerializer(instance=admin).data

            return {"admin" : serialized_admin}
            
        # Return serializer errors if the data is not valid, format it as a string
        return {"error": '; '.join([f"{key}: {', '.join(value)}" for key, value in serializer.errors.items()])}
               
    except Principal.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'a principal account with the provided credentials does not exist, please check the account details and try again'}
                   
    except Admin.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'an admin account for your school with the provided credentials does not exist, please check the account details and try again'}

    except Exception as e:
        # Handle any unexpected errors with a general error message
        return {'error': str(e)}


@database_sync_to_async
def update_teacher_account(user, role, details):

    try:
        # Retrieve the user and related school in a single query using select_related
        if role == 'PRINCIPAL':
            admin = Principal.objects.select_related('school').only('school').get(account_id=user)
        else:
            admin = Admin.objects.select_related('school').only('school').get(account_id=user)

        teacher  = Teacher.objects.get(account_id=details.get('account_id'), school=admin.school)
        
        serializer = AccountUpdateSerializer(instance=teacher, data=details.get('updates'))
        if serializer.is_valid():
            
            with transaction.atomic():
                serializer.save()
            
            serialized_teacher = AccountIDSerializer(instance=teacher).data

            return {"teacher" : serialized_teacher}
            
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
        return {'error': 'a teacher account in your school with the provided credentials does not exist, please check the account details and try again'}

    except Exception as e:
        # Handle any unexpected errors with a general error message
        return {'error': str(e)}


@database_sync_to_async
def update_student_account(user, role, details):

    try:
        # Retrieve the user and related school in a single query using select_related
        if role == 'PRINCIPAL':
            admin = Principal.objects.select_related('school').only('school').get(account_id=user)
        else:
            admin = Admin.objects.select_related('school').only('school').get(account_id=user)

        student  = Student.objects.get(account_id=details.get('account_id'), school=admin.school)
        
        serializer = AccountUpdateSerializer(instance=student, data=details.get('updates'))
        
        if serializer.is_valid():
            
            with transaction.atomic():
                serializer.save()
            
            serialized_student = AccountIDSerializer(instance=student).data

            return {"student" : serialized_student}
            
        # Return serializer errors if the data is not valid, format it as a string
        return {"error": '; '.join([f"{key}: {', '.join(value)}" for key, value in serializer.errors.items()])}
               
    except Principal.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'a principal account with the provided credentials does not exist, please check the account details and try again'}
                   
    except Admin.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'an admin account with the provided credentials does not exist, please check the account details and try again'}
                   
    except Student.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'a student account in your school with the provided credentials does not exist, please check the account details and try again'}

    except Exception as e:
        # Handle any unexpected errors with a general error message
        return {'error': str(e)}


@database_sync_to_async
def update_parent_account(user, role, details):

    try:
        # Retrieve the user and related school in a single query using select_related
        if role == 'PRINCIPAL':
            admin = Principal.objects.select_related('school').only('school').get(account_id=user)
        else:
            admin = Admin.objects.select_related('school').only('school').get(account_id=user)
            
        parent  = Parent.objects.prefetch_related('children__school').get(account_id=details.get('account_id'))

        if not parent.children.filter(school=admin.school).exists():
            return {"error": "could not proccess your request, the specified parent account is not linked to any student in your school. please ensure you are attempting to update a parent that is linked to at least one student in your school"}

        serializer = AccountUpdateSerializer(instance=parent, data=details.get('updates'))
        if serializer.is_valid():
            
            with transaction.atomic():
                serializer.save()
            
            serialized_parent = AccountIDSerializer(instance=parent).data

            return {"student" : serialized_parent}
            
        # Return serializer errors if the data is not valid, format it as a string
        return {"error": '; '.join([f"{key}: {', '.join(value)}" for key, value in serializer.errors.items()])}
               
    except Principal.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'a principal account with the provided credentials does not exist, please check the account details and try again'}
                   
    except Admin.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'an admin account with the provided credentials does not exist, please check the account details and try again'}
                   
    except Parent.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'a parent account with the provided credentials does not exist, please check the account details and try again'}

    except Exception as e:
        # Handle any unexpected errors with a general error message
        return {'error': str(e)}


@database_sync_to_async
def update_class(user, role, details):

    try:
        updates = details.get('updates')

        # Retrieve the user and related school in a single query using select_related
        if role == 'PRINCIPAL':
            admin = Principal.objects.select_related('school').only('school').get(account_id=user)
        else:
            admin = Admin.objects.select_related('school').only('school').get(account_id=user)

        classroom = Classroom.objects.get(class_id=details.get('class_id'), school=admin.school)

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
        students_list = details.get('students', '').split(', ')
        if not students_list or students_list == ['']:
            return {'error': 'your request could not be proccessed.. no students were provided'}
        
        # Retrieve the user and related school in a single query using select_related
        if role == 'PRINCIPAL':
            admin = Principal.objects.select_related('school').only('school').get(account_id=user)
        else:
            admin = Admin.objects.select_related('school').only('school').get(account_id=user)

        classroom = Classroom.objects.select_related('grade', 'subject').get(class_id=details.get('class'), school=admin.school)

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
        group_schedule = GroupSchedule.objects.prefetch_related('students').select_related('grade').get(group_schedule_id=details.get('group_schedule_id'), grade__school=admin.school)
        
        # Retrieve the existing students in the group schedule
        existing_students = group_schedule.students.filter(account_id__in=students_list).values_list('account_id', flat=True)
        
        if existing_students:
            existing_students_str = ', '.join(existing_students)
            return {'error': f'Invalid request. The following students are already in this class: {existing_students_str}. Please review the list of students and try again.'}
        
        students_to_add = Student.objects.filter(account_id__in=students_list, school=admin.school, grade=group_schedule.grade)        
        
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
            
    except GroupSchedule.DoesNotExist:
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
        group_schedule = GroupSchedule.objects.select_related('grade').get(group_schedule_id=details.get('group_schedule_id'), grade__school=admin.school)

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
            
    except GroupSchedule.DoesNotExist:
        # Handle the case where the provided group schedule ID does not exist
        return {'error': 'A group schedule in your school with the provided credentials does not exist. Please check the group schedule details and try again.'}

    except Exception as e:
        return {'error': str(e)}

