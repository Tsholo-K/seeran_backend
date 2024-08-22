# python 

# httpx

# channels
from channels.db import database_sync_to_async

# django

# simple jwt

# models 
from users.models import CustomUser
from timetables.models import GroupSchedule
from grades.models import Subject
from classes.models import Classroom

# serilializers
from users.serializers import AccountSerializer

# utility functions 


@database_sync_to_async
def form_data_for_creating_class(user, details):
    """
    Retrieves a list of teachers available for class creation based on the type of class being created.

    Args:
        user (str): The unique identifier (account_id) of the user making the request.
        details (dict): A dictionary containing details required for retrieving teacher information. It should include:
            - 'reason' (str): The reason for retrieving teachers, which determines the type of class being created. Possible values are:
                - 'subject class': Retrieves all teachers in the same school.
                - 'register class': Retrieves teachers who are not currently teaching any register class.

    Returns:
        dict: A dictionary containing:
            - 'teachers': A serialized list of available teachers based on the class type.
            - 'error': An error message if an exception occurs.
    """
    try:
        # Retrieve the user account
        account = CustomUser.objects.select_related('school').get(account_id=user)

        # Determine the query based on the reason for retrieving teachers
        if details.get('reason') == 'subject class':
            # Retrieve the subject and validate it against the grade
            subject = Subject.objects.get(subject_id=details.get('subject'))

            # Retrieve all teachers in the user's school who are not teaching the specified subject
            teachers = CustomUser.objects.filter(role='TEACHER', school=account.school).exclude(taught_classes__subject=subject).only('account_id', 'name', 'surname', 'email')

        elif details.get('reason') == 'register class':
            # Retrieve teachers not currently teaching a register class
            teachers = CustomUser.objects.filter(role='TEACHER', school=account.school).exclude(taught_classes__register_class=True).only('account_id', 'name', 'surname', 'email')

        else:
            return {"error": "Invalid reason provided. Expected 'subject class' or 'register class'."}

        # Serialize the list of teachers
        serializer = AccountSerializer(teachers.order_by('name', 'surname', 'account_id'), many=True)

        return {"teachers": serializer.data}
        
    except CustomUser.DoesNotExist:
        # Handle case where the user account does not exist
        return {'error': 'An account with the provided credentials does not exist. Please check the account details and try again.'}
        
    except Subject.DoesNotExist:
        return {'error': 'subject with the provided credentials does not exist'}

    except Exception as e:
        # Handle any other unexpected errors
        return {'error': str(e)}


@database_sync_to_async
def form_data_for_updating_class(user, details):
    """
    Retrieves data required for updating a classroom, including available teachers and current teacher details.

    Args:
        user (str): The unique identifier (account_id) of the user making the request.
        details (dict): A dictionary containing details required for retrieving classroom information. It should include:
            - 'class_id' (str): The ID of the classroom to be updated.

    Returns:
        dict: A dictionary containing:
            - 'teacher': Serialized data of the current teacher assigned to the classroom (or `None` if no teacher is assigned).
            - 'teachers': A serialized list of other teachers available in the same school.
            - 'group': The group associated with the classroom.
            - 'classroom_identifier': The identifier of the classroom.
            - 'error': An error message if an exception occurs.
    """
    try:
        # Retrieve the user account and classroom in one go using select_related to minimize queries
        account = CustomUser.objects.select_related('school').get(account_id=user)
        classroom = Classroom.objects.select_related('school', 'teacher').get(class_id=details.get('class_id'))

        # Check if the user has permission to update the classroom
        if account.school != classroom.school:
            return {"error": "Permission denied. The provided classroom is not from your school. You can only update details of classes from your own school."}

        # Determine the query based on the classroom type
        if classroom.subject:
            teachers = CustomUser.objects.filter(role='TEACHER', school=account.school).exclude(taught_classes__subject=classroom.subject).only('account_id', 'name', 'surname', 'email')
            if classroom.teacher:
                teachers = teachers.exclude(account_id=classroom.teacher.account_id)

        elif classroom.register_class:
            teachers = CustomUser.objects.filter(role='TEACHER', school=account.school).exclude(taught_classes__register_class=True).only('account_id', 'name', 'surname', 'email')
            if classroom.teacher:
                teachers = teachers.exclude(account_id=classroom.teacher.account_id)

        else:
            return {"error": "invalid classroom provided. the classroom in neither a register class or linked to a subject"}
        
        # Fetch teachers and serialize them
        teachers = AccountSerializer(teachers, many=True).data

        # Prepare the response data
        response_data = {'teacher': AccountSerializer(classroom.teacher).data if classroom.teacher else None, "teachers": teachers, 'group': classroom.group, 'classroom_identifier': classroom.classroom_number}

        return response_data

    except CustomUser.DoesNotExist:
        # Handle case where the user account does not exist
        return {'error': 'An account with the provided credentials does not exist. Please check the account details and try again.'}
    
    except Classroom.DoesNotExist:
        # Handle case where the classroom does not exist
        return {'error': 'A classroom with the provided credentials does not exist. Please check the classroom details and try again.'}
    
    except Exception as e:
        # Handle any other unexpected errors
        return {'error': str(e)}


@database_sync_to_async
def form_data_for_adding_students_to_class(user, details):
    """
    Retrieves a list of students who can be added to a specified class based on the provided details.
    
    This function handles two main scenarios:
    1. `subject class`: Fetches students in the same grade who are not enrolled in any class with the same subject as the provided classroom.
    2. `register class`: Fetches students in the same grade who are not already enrolled in a register class.
    
    Args:
        user (str): The unique identifier (account_id) of the user making the request.
        details (dict): A dictionary containing details required for fetching the students. It should include:
            - 'class_id' (str): The ID of the classroom to which students are to be added.
            - 'reason' (str): The reason for fetching students, which can be 'subject class' or 'register class'.
    
    Returns:
        dict: A dictionary containing:
            - "students": A serialized list of students who meet the criteria.
            - "error": An error message if an exception occurs.
    """
    try:
        # Retrieve the account of the user making the request using `select_related` to optimize query performance
        account = CustomUser.objects.select_related('school').get(account_id=user)

        # Retrieve the classroom with the provided class ID and related data using `select_related`
        classroom = Classroom.objects.select_related('school', 'grade', 'subject').get(class_id=details.get('class_id'))

        # Check if the user is allowed to access the classroom
        if account.school != classroom.school:
            return {"error": "Permission denied. The provided classroom is not from your school. You can only view details about classes from your own school."}

        # Determine the reason for fetching students and apply the appropriate filtering logic
        if details.get('reason') == 'subject class':
            # Check if the classroom has a subject linked to it
            if not classroom.subject:
                return {"error": "could not proccess your request. the provided classroom has no subject linked to it."}

            # Exclude students who are already enrolled in any class with the same subject as the classroom
            students = CustomUser.objects.filter(grade=classroom.grade).exclude(enrolled_classes__subject=classroom.subject).only('account_id', 'name', 'surname', 'id_number', 'passport_number', 'email')

        elif details.get('reason') == 'register class':
            # Check if the classroom is a register class
            if not classroom.register_class:
                return {"error": "could not proccess your request. the provided classroom is not a register class."}

            # Exclude students who are already enrolled in a register class in the same grade
            students = CustomUser.objects.filter(grade=classroom.grade).exclude(enrolled_classes__register_class=True).only('account_id', 'name', 'surname', 'id_number', 'passport_number', 'email')

        else:
            # Return an error if the reason provided is not valid
            return {"error": "Invalid reason provided."}

        # Serialize the list of students to return them in the response
        serializer = AccountSerializer(students, many=True)
        return {"students": serializer.data}

    except CustomUser.DoesNotExist:
        # Handle case where the user account does not exist
        return {'error': 'An account with the provided credentials does not exist. Please check the account details and try again.'}
    
    except Classroom.DoesNotExist:
        # Handle case where the classroom does not exist
        return {'error': 'A classroom with the provided credentials does not exist. Please check the classroom details and try again.'}
    
    except Exception as e:
        # Handle any other unexpected errors
        return {'error': str(e)}


@database_sync_to_async
def form_data_for_adding_students_to_group_schedule(user, details):
    """
    Retrieves a list of students who can be added to a specified group schedule based on the provided details.

    This function fetches all students in the same grade as the specified group schedule who are not already
    subscribed to the group schedule.

    Args:
        user (str): The unique identifier (account_id) of the user making the request.
        details (dict): A dictionary containing details required for fetching the students. It should include:
            - 'group_schedule_id' (str): The ID of the group schedule to which students are to be added.

    Returns:
        dict: A dictionary containing:
            - "students": A serialized list of students who meet the criteria.
            - "error": An error message if an exception occurs.
    """
    try:
        # Retrieve the account of the user making the request
        account = CustomUser.objects.select_related('school').get(account_id=user)
        
        # Retrieve the group schedule with the provided ID and related data
        group_schedule = GroupSchedule.objects.select_related('grade__school').get(group_schedule_id=details.get('group_schedule_id'))

        # Check if the user is allowed to access the group schedule
        if account.school != group_schedule.grade.school:
            return {"error": "Permission denied. You can only view details about group schedules from your own school."}

        # Fetch all students in the same grade who are not already subscribed to the group schedule
        students = CustomUser.objects.filter(grade=group_schedule.grade, role='STUDENT').exclude(my_group_schedule=group_schedule).only('account_id', 'name', 'surname', 'id_number', 'passport_number', 'email')  # Use `only` to select specific fields for efficiency

        # Serialize the list of students to return them in the response
        serializer = AccountSerializer(students, many=True)

        return {"students": serializer.data}

    except CustomUser.DoesNotExist:
        # Handle case where the user account does not exist
        return {'error': 'An account with the provided credentials does not exist. Please check the account details and try again.'}
    
    except GroupSchedule.DoesNotExist:
        # Handle case where the group schedule does not exist
        return {'error': 'A group schedule with the provided credentials does not exist. Please check the group schedule details and try again.'}

    except Exception as e:
        # Handle any other unexpected errors
        return {'error': str(e)}


    