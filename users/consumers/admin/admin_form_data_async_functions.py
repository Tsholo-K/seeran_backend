# python 

# httpx

# channels
from channels.db import database_sync_to_async

# django

# simple jwt

# models 
from users.models import Principal, Admin
from schedules.models import GroupSchedule
from grades.models import Subject
from classes.models import Classroom

# serilializers
from users.serializers.teachers.teachers_serializers import TeacherAccountSerializer
from users.serializers.students.students_serializers import StudentSourceAccountSerializer

# mappings
from users.maps import role_specific_maps

# queries
from users.complex_queries import queries


@database_sync_to_async
def form_data_for_creating_class(user, role, details):
    try:
        # Get the appropriate model for the requesting user's role from the mapping.
        Model = role_specific_maps.account_access_control_mapping[role]

        # Build the queryset for the requesting account with the necessary related fields.
        requesting_account = Model.objects.select_related('school').prefetch_related('school__teachers__taught_classes').get(account_id=user)

        # Determine the query based on the reason for retrieving teachers
        if details.get('reason') == 'subject class':
            # Retrieve the subject and validate it against the grade
            subject = Subject.objects.get(subject_id=details.get('subject'), grade__school=requesting_account.school)

            # Retrieve all teachers in the user's school who are not teaching the specified subject
            teachers = requesting_account.school.teachers.all().exclude(taught_classes__subject=subject)

        elif details.get('reason') == 'register class':
            # Retrieve teachers not currently teaching a register class
            teachers = requesting_account.school.teachers.all().exclude(taught_classes__register_class=True)

        else:
            return {"error": "invalid reason provided. expected 'subject class' or 'register class'."}

        # Serialize the list of teachers
        serialized_teachers = TeacherAccountSerializer(teachers, many=True).data

        return {"teachers": serialized_teachers}
               
    except Principal.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'a principal account with the provided credentials does not exist, please check the account details and try again'}
                   
    except Admin.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'an admin account with the provided credentials does not exist, please check the account details and try again'}
        
    except Subject.DoesNotExist:
        return {'error': 'a subject in your school with the provided credentials does not exist, please check the subject details and try again'}

    except Exception as e:
        # Handle any other unexpected errors
        return {'error': str(e)}


@database_sync_to_async
def form_data_for_updating_class(user, role, details):
    try:
        # Get the appropriate model for the requesting user's role from the mapping.
        Model = role_specific_maps.account_access_control_mapping[role]

        # Build the queryset for the requesting account with the necessary related fields.
        requesting_account = Model.objects.select_related('school').prefetch_related('school__teachers__taught_classes').get(account_id=user)

        classroom = Classroom.objects.select_related('subject', 'teacher').get(class_id=details.get('class'), school=requesting_account.school)

        # Determine the query based on the classroom type
        if classroom.subject:
            teachers = requesting_account.school.teachers.all().exclude(taught_classes__subject=classroom.subject)

        elif classroom.register_class:
            teachers = requesting_account.school.teachers.all().exclude(taught_classes__register_class=True)

        else:
            return {"error": "invalid classroom provided. the classroom in neither a register class or linked to a subject"}
        
        if classroom.teacher:
            teachers = teachers.exclude(account_id=classroom.teacher.account_id)
        
        # serialize them
        serialized_teachers = TeacherAccountSerializer(teachers, many=True).data
        class_teacher = TeacherAccountSerializer(classroom.teacher).data if classroom.teacher else None

        return {'teacher': class_teacher, "teachers": serialized_teachers, 'group': classroom.group, 'classroom_identifier': classroom.classroom_number}
               
    except Principal.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'a principal account with the provided credentials does not exist, please check the account details and try again'}
                   
    except Admin.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'an admin account with the provided credentials does not exist, please check the account details and try again'}
    
    except Classroom.DoesNotExist:
        # Handle case where the classroom does not exist
        return {'error': 'a classroom in your school with the provided credentials does not exist. Please check the classroom details and try again.'}
    
    except Exception as e:
        # Handle any other unexpected errors
        return {'error': str(e)}


@database_sync_to_async
def form_data_for_adding_students_to_class(user, role, details):
    try:
        # Get the appropriate model for the requesting user's role from the mapping.
        Model = role_specific_maps.account_access_control_mapping[role]

        # Build the queryset for the requesting account with the necessary related fields.
        requesting_account = Model.objects.select_related('school').only('school').get(account_id=user)

        # Retrieve the classroom with the provided class ID and related data using `select_related`
        classroom = Classroom.objects.select_related('grade', 'subject').get(class_id=details.get('class'), school=requesting_account.school)

        # Determine the reason for fetching students and apply the appropriate filtering logic
        if details.get('reason') == 'subject class':
            # Check if the classroom has a subject linked to it
            if not classroom.subject:
                return {"error": "could not proccess your request. the provided classroom has no subject linked to it."}

            # Exclude students who are already enrolled in any class with the same subject as the classroom
            students = requesting_account.school.students.all().filter(grade=classroom.grade).exclude(enrolled_classes__subject=classroom.subject)

        elif details.get('reason') == 'register class':
            # Check if the classroom is a register class
            if not classroom.register_class:
                return {"error": "could not proccess your request. the provided classroom is not a register class."}

            # Exclude students who are already enrolled in a register class in the same grade
            students = requesting_account.school.students.all().filter(grade=classroom.grade).exclude(enrolled_classes__register_class=True)

        else:
            # Return an error if the reason provided is not valid
            return {"error": "Invalid reason provided."}

        # Serialize the list of students to return them in the response
        serialized_students = StudentSourceAccountSerializer(students, many=True).data

        return {"students": serialized_students}
               
    except Principal.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'a principal account with the provided credentials does not exist, please check the account details and try again'}
                   
    except Admin.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'an admin account with the provided credentials does not exist, please check the account details and try again'}
    
    except Classroom.DoesNotExist:
        # Handle case where the classroom does not exist
        return {'error': 'a classroom in your school with the provided credentials does not exist. Please check the classroom details and try again.'}
    
    except Exception as e:
        # Handle any other unexpected errors
        return {'error': str(e)}


@database_sync_to_async
def form_data_for_adding_students_to_group_schedule(user, role, details):
    try:
        # Get the appropriate model for the requesting user's role from the mapping.
        Model = role_specific_maps.account_access_control_mapping[role]

        # Build the queryset for the requesting account with the necessary related fields.
        requesting_account = Model.objects.select_related('school').only('school').get(account_id=user)
        
        # Retrieve the group schedule with the provided ID and related data
        group_schedule = GroupSchedule.objects.select_related('grade').get(group_schedule_id=details.get('group_schedule_id'), grade__school=requesting_account.school)

        # Fetch all students in the same grade who are not already subscribed to the group schedule
        students = requesting_account.school.students.all().filter(grade=group_schedule.grade).exclude(my_group_schedule=group_schedule)

        # Serialize the list of students to return them in the response
        serialized_students = StudentSourceAccountSerializer(students, many=True).data

        return {"students": serialized_students}
               
    except Principal.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'a principal account with the provided credentials does not exist, please check the account details and try again'}
                   
    except Admin.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'an admin account with the provided credentials does not exist, please check the account details and try again'}
    
    except GroupSchedule.DoesNotExist:
        # Handle case where the group schedule does not exist
        return {'error': 'a group schedule in your school with the provided credentials does not exist. Please check the group schedule details and try again.'}

    except Exception as e:
        # Handle any other unexpected errors
        return {'error': str(e)}


    