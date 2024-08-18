# python 

# httpx

# channels
from channels.db import database_sync_to_async

# django
from django.db.models import Q
from django.db import transaction
from django.utils.dateparse import parse_time
from django.core.exceptions import ValidationError

# simple jwt

# models 
from users.models import CustomUser
from timetables.models import Session, Schedule, TeacherSchedule, GroupSchedule
from grades.models import Grade, Subject
from classes.models import Classroom

# serilializers
from users.serializers import AccountUpdateSerializer, AccountIDSerializer, AccountSerializer, AccountCreationSerializer, StudentAccountCreationSerializer, ParentAccountCreationSerializer
from grades.serializers import GradeCreationSerializer, GradesSerializer, GradeSerializer, SubjectCreationSerializer, SubjectDetailSerializer, ClassesSerializer
from classes.serializers import ClassCreationSerializer,ClassUpdateSerializer
from announcements.serializers import AnnouncementCreationSerializer

# utility functions 
from authentication.utils import validate_user_email
    
    
@database_sync_to_async
def create_account(user, details):

    try:
        if not validate_user_email(details.get('email')):
            return {'error': 'Invalid email format'}
    
        if CustomUser.objects.filter(email=details.get('email')).exists():
            return {"error": "an account with the provided email address already exists"}

        if details.get('role') not in ['ADMIN', 'TEACHER']:
            return {"error": "invalid account role"}
        
        account = CustomUser.objects.get(account_id=user)
        details['school'] = account.school.pk
        
        serializer = AccountCreationSerializer(data=details)
        
        if serializer.is_valid():
            
            with transaction.atomic():
                created_user = CustomUser.objects.create_user(**serializer.validated_data)
            
            return {'user' : created_user}
            
        return {"error" : serializer.errors}
           
    except CustomUser.DoesNotExist:
        return { 'error': 'account with the provided credentials does not exist' }
    
    except Exception as e:
        return { 'error': str(e) }


@database_sync_to_async
def create_student_account(user, details):

    try:
        if details.get('citizen') not in ['yes', 'no']:
            return {"error": "invalid citizen value"}

        if details.get('email'):
            if not validate_user_email(details.get('email')):
                return {'error': 'Invalid email format'}
            
            if CustomUser.objects.filter(email=details.get('email')).exists():
                return {"error": "an account with the provided email address already exists"}

        if details.get('citizen') == 'yes':
            if not details.get('id_number'):
                return {"error": "ID number needed for all student accounts who are citizens"}
            
            if CustomUser.objects.filter(id_number=details.get('id_number')).exists():
                return {"error": "an account with this ID number already exists"}

        if details.get('citizen') == 'no':
            if not details.get('passport_number'):
                return {"error": "Passport number needed for all student accounts who are not citizens"}
            
            if CustomUser.objects.filter(passport_number=details.get('passport_number')).exists():
                return {"error": "an account with this Passport Number already exists"}

        account = CustomUser.objects.get(account_id=user)
        grade = Grade.objects.get(grade_id=details.get('grade_id'), school=account.school)

        details['school'] = account.school.pk
        details['grade'] = grade.pk
        details['role'] = 'STUDENT'

        serializer = StudentAccountCreationSerializer(data=details)
        
        if serializer.is_valid():
            
            with transaction.atomic():
                user = CustomUser.objects.create_user(**serializer.validated_data)
            
            if details.get('email') != (None or ''):
                return {'user' : user }
            
            else:
                return {'message' : 'student account successfully created.. you can now link a parent, add to classes and much more'}
            
        return {"error" : serializer.errors}
           
    except CustomUser.DoesNotExist:
        return { 'error': 'account with the provided credentials does not exist' }
    
    except Grade.DoesNotExist:
        return { 'error': 'grade with the provided credentials does not exist' }

    except Exception as e:
        return { 'error': str(e) }


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
       
        account = CustomUser.objects.get(account_id=user)
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
        return { 'error': 'account with the provided credentials does not exist' }
    
    except Exception as e:
        return { 'error': str(e) }


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
def delete_account(user, details):

    try:
        account = CustomUser.objects.get(account_id=user)
        requested_user  = CustomUser.objects.get(account_id=details.get('account_id'))

        if requested_user.role == 'FOUNDER' or (requested_user.role in ['PRINCIPAL', 'ADMIN'] and account.role != 'PRINCIPAL') or (requested_user.role != 'PARENT' and account.school != requested_user.school) or (requested_user.role == 'PARENT' and not requested_user.children.filter(school=account.school).exists()):
            return { "error" : 'unauthorized action.. permission denied' }
        
        if requested_user.role == 'PARENT' and requested_user.children.exists():
            return { "error" : 'the parent account is still linked to a student account.. permission denied' }

        requested_user.delete()
                            
        return {"message" : 'account successfully deleted'}
        
    except CustomUser.DoesNotExist:
        return {'error': 'an account with the provided credentials does not exist, please check the account details and try again'}
    
    except Exception as e:
        return { 'error': str(e) }


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
        account = CustomUser.objects.get(account_id=user)

        # Fetch the student account using the provided child ID
        child = CustomUser.objects.get(account_id=details.get('child_id'))

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
def search_accounts(user, details):

    try:
        if details.get('role') not in ['ADMIN', 'TEACHER']:
            return { "error" : 'invalid role request' }
        
        account = CustomUser.objects.get(account_id=user)

        if details.get('role') == 'ADMIN':
            accounts = CustomUser.objects.filter( Q(role='ADMIN') | Q(role='PRINCIPAL'), school=account.school).exclude(account_id=user)
    
        if details.get('role') == 'TEACHER':
            accounts = CustomUser.objects.filter(role=details.get('role'), school=account.school)

        serializer = AccountSerializer(accounts, many=True)
        return { "users" : serializer.data }
        
    except CustomUser.DoesNotExist:
        return { 'error': 'account with the provided credentials does not exist' }
    
    except Exception as e:
        return { 'error': str(e) }


@database_sync_to_async
def search_subscribed_students(user, details):
    """
    Searches and retrieves students subscribed to a specific group schedule.

    Args:
        user (str): The account ID of the user making the request.
        details (dict): A dictionary containing the group_schedule_id to identify the group schedule.

    Returns:
        dict: A dictionary containing the list of subscribed students or an error message.

    Raises:
        CustomUser.DoesNotExist: If the user with the provided account ID does not exist.
        GroupSchedule.DoesNotExist: If the group schedule with the provided ID does not exist.
        Exception: For any other unexpected errors.
    """
    try:
        # Retrieve the account making the request
        account = CustomUser.objects.get(account_id=user)
        
        # Retrieve the group schedule
        group_schedule = GroupSchedule.objects.get(group_schedule_id=details.get('group_schedule_id'))

        # Check if the user has permission to view the group schedule
        if account.school != group_schedule.grade.school:
            return {"error": 'permission denied. you can only view details about group schedules from your own school.'}

        # Get all students subscribed to this group schedule
        students = group_schedule.students.all()

        # Serialize the students
        serializer = AccountSerializer(students, many=True)

        return {"students": serializer.data}

    except CustomUser.DoesNotExist:
        return {'error': 'an account with the provided credentials does not exist. Please check the account details and try again.'}
                
    except GroupSchedule.DoesNotExist:
        return {'error': 'a group schedule with the provided credentials does not exist. Please check the group schedule details and try again.'}

    except Exception as e:
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
        account = CustomUser.objects.select_related('school').get(account_id=user)

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
        return {"error": str(e)}


@database_sync_to_async
def fetch_grades(user):

    try:
        account = CustomUser.objects.get(account_id=user)
        grades = Grade.objects.filter(school=account.school.pk)
        
        serializer = GradesSerializer(grades, many=True)

        return { 'grades': serializer.data }
        
    except CustomUser.DoesNotExist:
        return { 'error': 'account with the provided credentials does not exist' }
    
    except Exception as e:
        return { 'error': str(e) }


@database_sync_to_async
def fetch_grades_with_student_count(user):

    try:
        account = CustomUser.objects.get(account_id=user)
        grades = Grade.objects.filter(school=account.school)

        serializer = GradesSerializer(grades, many=True)
        student_count = CustomUser.objects.filter(role='STUDENT', school=account.school).count()

        return { 'grades': serializer.data, 'student_count' : student_count }
        
    except CustomUser.DoesNotExist:
        return { 'error': 'account with the provided credentials does not exist' }
    
    except Exception as e:
        return { 'error': str(e) }
    

@database_sync_to_async
def search_grade(user, details):

    try:
        account = CustomUser.objects.get(account_id=user)
        
        grade  = Grade.objects.get(school=account.school, grade_id=details.get('grade_id'))
        serializer = GradeSerializer(instance=grade)

        return { 'grade' : serializer.data}
    
    except Grade.DoesNotExist:
        return { 'error': 'grade with the provided credentials does not exist' }

    except CustomUser.DoesNotExist:
        return { 'error': 'account with the provided credentials does not exist' }
    
    except Exception as e:
        return { 'error': str(e) }


@database_sync_to_async
def create_subject(user, details):

    try:
        if not details.get('subject'):
            return {"error": "could not process request.. no subject was provided"}
           
        # Retrieve the user and related school in a single query using select_related
        account = CustomUser.objects.select_related('school').get(account_id=user)
        grade = Grade.objects.select_related('school').get(grade_id=details.get('grade'))

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
        return { 'error': 'account with the provided credentials does not exist' }
    
    except Exception as e:
        return { 'error': str(e) }
    

@database_sync_to_async
def search_subject(user, details):
    """
    Asynchronous function to search for and retrieve subject details.

    This function checks if the requesting user is authorized to access or update 
    the subject information. If the subject is found and the user has the correct 
    permissions, the function returns the serialized subject data.

    Args:
        user (str): The account_id of the user making the request.
        details (dict): A dictionary containing the details of the subject being searched, specifically the 'subject_id'.

    Returns:
        dict: A dictionary containing the serialized subject data if found and accessible, 
            or an error message if the subject or user account is not found, or if there is 
            a permission issue.
    """
    try:
        # Retrieve user account
        account = CustomUser.objects.get(account_id=user)

        # Retrieve the subject and its related grade
        subject = Subject.objects.select_related('grade').get(subject_id=details.get('subject_id'))

        # Verify that the subject belongs to the same school as the user
        if account.school != subject.grade.school:
            return {"error": "permission denied. you can only access or update details about subjects from your own school."}

        # Serialize the subject data
        serializer = SubjectDetailSerializer(subject)
        return {"subject": serializer.data}

    except CustomUser.DoesNotExist:
        # Handle case where the user account does not exist
        return {'error': 'an account with the provided credentials does not exist.'}
    
    except Subject.DoesNotExist:
        # Handle case where the subject does not exist
        return {'error': 'a subject with the provided credentials does not exist.'}
    
    except Exception as e:
        # Handle any other exceptions
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

        # Retrieve the grade
        grade = Grade.objects.select_related('school').get(grade_id=details.get('grade_id'))

        if account.school != grade.school:
            return { "error" : 'you do not have permission to perform this action because the specified grade does not belong to your school. please ensure you are attempting to create a group schedule in a grade within your own school' }

        if details.get('register'):
            # Check if a register class with the same group already exists in the same grade
            if Classroom.objects.filter(group=details.get('group'), grade=grade, school=account.school, register_class=True).exists():
                return {"error": "a register class with the provided group in the same grade already exists.. a class group should be unique in the same grade and subject(if applicable)"}
                
            response = {'message': f'register class for grade {grade.grade} created successfully. you can now add students and track attendance in the register classes page'}

        elif details.get('subject_id'):
            # Retrieve the subject
            subject = Subject.objects.select_related('grade').get(subject_id=details.get('subject_id'))

            # Check if the grade is from the same school as the user making the request
            if subject.grade != grade:
                return { "error" : 'you do not have permission to perform this action because the specified subject does not belong to the specified grade. please ensure you are attempting to create a classroom in a subject within a correctly specified grade' }

            # Check if a class with the same group already exists in the same subject and grade
            if Classroom.objects.filter(group=details.get('group'), grade=grade, school=account.school, subject=subject).exists():
                return {"error": "a class with the provided group in the same subject and grade already exists.. a class group should be unique in the same grade and subject"}
            
            details['subject'] = subject.pk

            response = {'message': f'class for grade {grade.grade} {subject.subject} created successfully. you can now add students, set assessments and track performance in the subject classes page'.lower()}

        else:
            return {"error": "the provided classroom creation information is invalid. please make sure you have provided all required information and try again"}
      
        # Set the school and grade fields
        details['school'] = account.school.pk
        details['grade'] = grade.pk

        # Serialize the details for class creation
        serializer = ClassCreationSerializer(data=details)

        # Validate the serialized data
        if serializer.is_valid():
            # Create the class within a transaction to ensure atomicity
            with transaction.atomic():
                classroom = Classroom.objects.create(**serializer.validated_data)

                # Retrieve the teacher if specified
                if details.get('classroom_teacher'):
                    classroom.update_teacher(teacher=CustomUser.objects.get(account_id=details.get('classroom_teacher'), school=account.school))
           
            return response
        
        # Return errors if the serializer validation fails
        return {"error": serializer.errors}
               
    except CustomUser.DoesNotExist:
        # Handle case where the user or teacher account does not exist
        return {'error': 'an account with the provided credentials does not exist'}
    
    except Grade.DoesNotExist:
        # Handle case where the grade does not exist
        return {'error': 'grade with the provided credentials does not exist'}
    
    except Subject.DoesNotExist:
        # Handle case where the grade does not exist
        return {'error': 'subject with the provided credentials does not exist'}

    except Exception as e:
        # Handle any other unexpected errors
        return {'error': str(e)}


@database_sync_to_async
def delete_class(user, details):
    try:
        # Retrieve the account making the request
        account = CustomUser.objects.get(account_id=user)

        # Retrieve the grade
        classroom = Classroom.objects.get(grade_id=details.get('class_id'))

        if account.school != classroom.school:
            return { "error" : 'you do not have permission to perform this action because the specified classroom does not belong to your school. please ensure you are attempting to create a group schedule in a grade within your own school' }

        classroom.delete()
        return {'message': f'class for grade created successfully. you can now add students, set assessments and track performance in the subject classes page'}
               
    except CustomUser.DoesNotExist:
        # Handle case where the user or teacher account does not exist
        return {'error': 'account with the provided credentials does not exist'}
    
    except Classroom.DoesNotExist:
        # Handle case where the grade does not exist
        return {'error': 'classroom with the provided credentials does not exist'}

    except Exception as e:
        # Handle any other unexpected errors
        return {'error': str(e)}


@database_sync_to_async
def search_grade_register_classes(user, details):

    try:
        account = CustomUser.objects.get(account_id=user)
        grade  = Grade.objects.get(grade_id=details.get('grade_id'), school=account.school)

        classes = grade.grade_classes.filter(register_class=True)

        serializer = ClassesSerializer(classes, many=True)

        return {"classes": serializer.data}
    
    except CustomUser.DoesNotExist:
        return { 'error': 'account with the provided credentials does not exist' }
           
    except Grade.DoesNotExist:
        return { 'error': 'grade with the provided credentials does not exist' }
    
    except Exception as e:
        return { 'error': str(e) }


@database_sync_to_async
def update_class(user, details):

    try:
        updates = details.get('updates')

        account = CustomUser.objects.get(account_id=user)
        classroom = Classroom.objects.get(class_id=details.get('class_id'), school=account.school)

        new_teacher = updates.get('teacher')
        if new_teacher:
            if new_teacher == 'remove teacher':
                updates['teacher'] = None  # remove the teacher

            else:
                teacher = CustomUser.objects.get(account_id=new_teacher, school=account.school)
                updates['teacher'] = teacher.pk

        serializer = ClassUpdateSerializer(instance=classroom, data=updates)

        if serializer.is_valid():
            with transaction.atomic():
                serializer.save()

                return {"message" : 'class details have been successfully updated'}
            
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
def search_students(user, details):

    try:
        account = CustomUser.objects.get(account_id=user)
        students = Grade.objects.get(grade_id=details.get('grade_id'), school=account.school.pk).students.all()

        serializer = AccountSerializer(students, many=True)

        return {"students": serializer.data}
    
    except CustomUser.DoesNotExist:
        return { 'error': 'account with the provided credentials does not exist' }
           
    except Grade.DoesNotExist:
        return { 'error': 'grade with the provided credentials does not exist' }
    
    except Exception as e:
        return { 'error': str(e) }


@database_sync_to_async
def add_students_to_class(user, details):
    """
    Adds students to a specified classroom.

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
        classroom = Classroom.objects.select_related('school', 'grade', 'subject').get(class_id=details.get('class_id'))

        # Check permissions based on whether it's a register or subject class
        if details.get('register'):
            if account.school != classroom.school or not classroom.register_class:
                return {"error": "Permission denied. The provided classroom is either not from your school or is not a register class."}
        else:
            if account.school != classroom.school or not classroom.subject:
                return {"error": "Permission denied. The provided classroom is either not from your school or has no subject linked to it."}

        students_list = details.get('students', '').split(', ')
        if not students_list or students_list == ['']:
            return {'error': 'Invalid request. No students were provided.'}
        
        # Retrieve students already in the class to prevent duplication
        existing_students = classroom.students.filter(account_id__in=students_list).values_list('account_id', flat=True)
        if existing_students:
            return {'error': f'The following students are already in this class: {", ".join(existing_students)}'}

        # Retrieve and add students to the class in a single transaction
        students_to_add = CustomUser.objects.filter(account_id__in=students_list, school=account.school, grade=classroom.grade)
        with transaction.atomic():
            classroom.students.add(*students_to_add)
        
        message = f'Students successfully added to the grade {classroom.grade.grade}, group {classroom.group.title()} {"register" if details.get("register") else classroom.subject.subject.lower()} class.'
        return {'message': message}

    except CustomUser.DoesNotExist:
        return {'error': 'An account with the provided credentials does not exist. Please check the account details and try again.'}
    
    except Classroom.DoesNotExist:
        return {'error': 'A classroom with the provided credentials does not exist. Please check the classroom details and try again.'}

    except Exception as e:
        return {'error': str(e)}


@database_sync_to_async
def remove_student_from_class(user, details):
    """
    Removes a single student from a specified classroom.

    Args:
        user (str): The unique identifier (account_id) of the user making the request.
        details (dict): A dictionary containing class and student details.
            - 'class_id' (str): The ID of the classroom.
            - 'account_id' (str): The ID of the student to be removed.

    Returns:
        dict: A dictionary containing a success message or an error message.
    """
    try:
        # Retrieve the user account and classroom with related fields
        account = CustomUser.objects.select_related('school').get(account_id=user)
        classroom = Classroom.objects.select_related('school', 'grade').get(class_id=details.get('class_id'))

        # Check permission to remove a student from the class
        if account.school != classroom.school:
            return {"error": "Permission denied. The provided classroom is not from your school."}

        # Check if the student is part of the classroom
        student_to_remove = classroom.students.filter(account_id=details.get('account_id')).first()
        if student_to_remove:
            # Remove the student within a transaction
            with transaction.atomic():
                classroom.students.remove(student_to_remove)
            
            return {'message': 'The student has been successfully removed from the class.'}
        
        return {'error': 'Cannot remove student. The student with the provided credentials is not part of the class.'}

    except CustomUser.DoesNotExist:
        return {'error': 'An account with the provided credentials does not exist.'}
    
    except Classroom.DoesNotExist:
        return {'error': 'A classroom with the provided credentials does not exist.'}

    except Exception as e:
        return {'error': str(e)}


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
        return {'error': 'Invalid account credentials. Please verify and try again.'}

    except Schedule.DoesNotExist:
        return {'error': 'Specified schedule not found. Please verify the details and try again.'}

    except Exception as e:
        return {'error': f'An unexpected error occurred: {str(e)}'}


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
        return {'error': 'An account with the provided credentials does not exist. Please check the account details and try again.'}

    except Exception as e:
        return {'error': str(e)}


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
            # Retrieve all teachers in the user's school
            teachers = CustomUser.objects.filter(role='TEACHER', school=account.school).only('account_id', 'name', 'surname', 'email')

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

        # Retrieve other teachers in the same school, excluding the current teacher if one is assigned
        teachers = CustomUser.objects.filter(role='TEACHER', school=account.school).only('account_id', 'name', 'surname', 'email')
        if classroom.teacher:
            teachers = teachers.exclude(account_id=classroom.teacher.account_id)
        
        # Fetch teachers and serialize them
        teachers = AccountSerializer(teachers.order_by('name', 'surname', 'account_id'), many=True).data

        # Prepare the response data
        response_data = {'teacher': AccountSerializer(classroom.teacher).data if classroom.teacher else None, "teachers": teachers, 'group': classroom.group, 'classroom_identifier': classroom.classroom_identifier}

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
def form_data_add_students_to_group_schedule(user, details):
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
        reason = details.get('reason')
        if reason == 'subject class':
            # Check if the classroom has a subject linked to it
            if not classroom.subject:
                return {"error": "Permission denied. The provided classroom has no subject linked to it."}

            # Get all students in the same grade as the classroom
            students_in_grade = CustomUser.objects.filter(grade=classroom.grade).only('account_id', 'name', 'surname', 'id_number', 'passport_number', 'email')

            # Exclude students who are already enrolled in any class with the same subject as the classroom
            students = students_in_grade.exclude(enrolled_classes__subject=classroom.subject)

        elif reason == 'register class':
            # Check if the classroom is a register class
            if not classroom.register_class:
                return {"error": "Permission denied. The provided classroom is not a register class."}

            # Get all students in the same grade as the classroom
            students_in_grade = CustomUser.objects.filter(grade=classroom.grade).only('account_id', 'name', 'surname', 'id_number', 'passport_number', 'email')

            # Exclude students who are already enrolled in a register class in the same grade
            students = students_in_grade.exclude(enrolled_classes__register_class=True)

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


    