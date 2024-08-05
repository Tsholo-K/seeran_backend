# python 

# httpx

# channels
from channels.db import database_sync_to_async

# django
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.db import IntegrityError, transaction
from django.utils.dateparse import parse_time

# simple jwt

# models 
from users.models import CustomUser
from timetables.models import Session, Schedule, TeacherSchedule, GroupSchedule
from grades.models import Grade, Subject
from classes.models import Classroom
from attendances.models import Absent

# serilializers
from users.serializers import AccountUpdateSerializer, AccountIDSerializer, AccountSerializer, AccountCreationSerializer, StudentAccountCreationSerializer, ParentAccountCreationSerializer
from grades.serializers import GradesSerializer, GradeSerializer, SubjectDetailSerializer, ClassesSerializer
from classes.serializers import ClassSerializer, ClassUpdateSerializer, TeacherClassesSerializer

# utility functions 
from authentication.utils import generate_otp, verify_user_otp, validate_user_email
from attendances.utility_functions import get_month_dates
    
    
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


SCHOOL_GRADES_CHOICES = [('000', 'Grade 000'), ('00', 'Grade 00'), ('R', 'Grade R'), ('1', 'Grade 1'), ('2', 'Grade 2'), ('3', 'Grade 3'), ('4', 'Grade 4'), ('5', 'Grade 5'), ('6', 'Grade 6'), ('7', 'Grade 7'), ('8', 'Grade 8'), ('9', 'Grade 9'), ('10', 'Grade 10'), ('11', 'Grade 11'), ('12', 'Grade 12')]

@database_sync_to_async
def create_grade(user, details):

    try:
        account = CustomUser.objects.get(account_id=user)

        if Grade.objects.filter(grade=details.get('grade'), school=account.school).exists():
            return {"error": f"grade {details.get('grade')} already exists for the school, duplicate grades is not allowed"}
        
        # Calculate the grade order
        grade_order = [choice[0] for choice in SCHOOL_GRADES_CHOICES].index(details.get('grade'))

        with transaction.atomic():
            # Include the grade_order when creating the Grade instance
            grad = Grade.objects.create(grade=details.get('grade'), grade_order=grade_order, school=account.school)
            grad.save()

            if details.get('subjects'):
                subject_list = details.get('subjects').split(', ')
                for sub in subject_list:
                    ject = Subject.objects.create(subject=sub, grade=grad)
                    ject.save()
            
        return { 'message': 'you can now add student accounts, subjects, classes and much more..' }
               
    except CustomUser.DoesNotExist:
        return { 'error': 'account with the provided credentials does not exist' }
    
    except Exception as e:
        return { 'error': str(e) }


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
        grades = Grade.objects.filter(school=account.school.pk)

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
def create_subjects(user, details):

    try:
        account = CustomUser.objects.get(account_id=user)
        grade = Grade.objects.get(grade_id=details.get('grade_id'), school=account.school)

        if details.get('subjects') == '':
            return { 'error': f'invalid request.. no subjects were provided' }
        
        subject_list = details.get('subjects').split(', ')
        
        existing_subjects = []
        for sub in subject_list:
            if Subject.objects.filter(subject=sub, grade=grade).exists():
                existing_subjects.append(sub.title())
        
        if existing_subjects:
            return {'error' : f'the following subjects have already been created for the current grade: {", ".join(existing_subjects)}.. duplicate subjects is not allowed'}
    
        with transaction.atomic():
            for sub in subject_list:
                ject = Subject.objects.create(subject=sub, grade=grade)
                ject.save()

        # Determine the correct word to use based on the number of subjects
        subject_word = "subject" if len(subject_list) == 1 else "subjects"

        return { 'message': f'{subject_word} for grade created successfully. you can now add classes, set assessments.. etc' }
               
    except Grade.DoesNotExist:
        return { 'error': 'grade with the provided credentials does not exist' }
    
    except CustomUser.DoesNotExist:
        return { 'error': 'account with the provided credentials does not exist' }
    
    except Exception as e:
        return { 'error': str(e) }
    

@database_sync_to_async
def search_subject(user, details):

    try:
        account = CustomUser.objects.get(account_id=user)
        grade  = Grade.objects.get(school=account.school, grade_id=details.get('grade_id'))

        subject = Subject.objects.get(subject_id=details.get('subject_id'), grade=grade)

        serializer = SubjectDetailSerializer(subject)

        return {"subject": serializer.data}
    
    except CustomUser.DoesNotExist:
        return { 'error': 'account with the provided credentials does not exist' }
           
    except Grade.DoesNotExist:
        return { 'error': 'grade with the provided credentials does not exist' }
        
    except Subject.DoesNotExist:
        return { 'error': 'grade with the provided credentials does not exist' }
    
    except Exception as e:
        return { 'error': str(e) }


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
        account = CustomUser.objects.get(account_id=user)

        # Retrieve the teacher if specified
        if details.get('classroom_teacher'):
            teacher = CustomUser.objects.get(account_id=details.get('classroom_teacher'), school=account.school)
        else:
            teacher = None

        # Retrieve the grade
        grade = Grade.objects.get(grade_id=details.get('grade_id'))

        if account.school != grade.school:
            return { "error" : 'you do not have permission to perform this action because the specified grade does not belong to your school. please ensure you are attempting to create a group schedule in a grade within your own school' }

        if details.get('register'):
            # Check if a register class with the same group already exists in the same grade
            if Classroom.objects.filter(group=details.get('group'), grade=grade, school=account.school, register_class=True).exists():
                return {"error": "a register class with the provided group in the same grade already exists.. a class group should be unique in the same grade and subject(if applicable)"}

            # Create the register class
            with transaction.atomic():
                new_class = Classroom.objects.create(classroom_identifier=details.get('classroom'), group=details.get('group'), grade=grade, teacher=teacher, school=account.school, register_class=True)
                new_class.save()
                
            return {'message': f'register class for grade {grade.grade} created successfully. you can now add students and track attendance in the register classes page'}

        if details.get('subject_id'):
            # Retrieve the subject
            subject = Subject.objects.get(subject_id=details.get('subject_id'), grade=grade)

            # Check if a class with the same group already exists in the same subject and grade
            if Classroom.objects.filter(group=details.get('group'), grade=grade, school=account.school, subject=subject).exists():
                return {"error": "a class with the provided group in the same subject and grade already exists.. a class group should be unique in the same grade and subject"}

            # Create the subject class
            with transaction.atomic():
                new_class = Classroom.objects.create(classroom_identifier=details.get('classroom'), group=details.get('group'), grade=grade, teacher=teacher, school=account.school, subject=subject)
                new_class.save()
                
            return {'message': f'class for grade {grade.grade} {subject.subject.lower()} created successfully. you can now add students, set assessments and track performance in the subject classes page'}
               
    except CustomUser.DoesNotExist:
        # Handle case where the user or teacher account does not exist
        return {'error': 'account with the provided credentials does not exist'}
    
    except Grade.DoesNotExist:
        # Handle case where the grade does not exist
        return {'error': 'grade with the provided credentials does not exist'}

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

        if updates.get('teacher') != (None or ''):
            new_teacher = updates.get('teacher')
            if new_teacher == 'remove teacher':
                updates['teacher'] = None  # remove the teacher
            else:
                teacher = CustomUser.objects.get(account_id=new_teacher, school=account.school)
                updates['teacher'] = teacher.pk

        serializer = ClassUpdateSerializer(instance=classroom, data=updates)

        if serializer.is_valid():
            with transaction.atomic():
                serializer.save()

                return { "message" : 'class details successfully updated' }
            
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
def search_class(user, details):

    try:
        account = CustomUser.objects.get(account_id=user)
        classroom = Classroom.objects.get(class_id=details.get('class_id'), school=account.school)

        serializer = ClassSerializer(classroom)

        return {"class": serializer.data}

    except CustomUser.DoesNotExist:
        # Handle case where the user account does not exist
        return {'error': 'an account with the provided credentials does not exist. please check the account details and try again.'}
    
    except Classroom.DoesNotExist:
        # Handle case where the classroom does not exist
        return {'error': 'a classroom with the provided credentials does not exist. please check the classroom details and try again.'}
    
    except Exception as e:
        return { 'error': str(e) }


@database_sync_to_async
def search_teacher_classes(user, details):

    try:
        account = CustomUser.objects.get(account_id=user)
        classes = CustomUser.objects.get(account_id=details.get('teacher_id'), school=account.school).taught_classes.all()

        serializer = TeacherClassesSerializer(classes, many=True)

        return {"classes": serializer.data}

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
def create_schedule(user, details):
    """
    Creates a schedule for a teacher or a group based on the provided details.

    Parameters:
    user (str): The account ID of the user creating the schedule.
    details (dict): A dictionary containing the schedule details. It should include:
        - 'day' (str): The day of the week for the schedule.
        - 'for_group' (bool): Flag indicating whether the schedule is for a group.
        - 'group_schedule_id' (str): The ID of the group schedule (if for_group is True).
        - 'account_id' (str): The account ID of the teacher (if for_group is False).
        - 'sessions' (list): A list of session details. Each session should include:
            - 'class' (str): The type of class for the session.
            - 'classroom' (str, optional): The classroom for the session.
            - 'startTime' (dict): A dictionary with 'hour', 'minute', and 'second' for the start time.
            - 'endTime' (dict): A dictionary with 'hour', 'minute', and 'second' for the end time.

    Returns:
    dict: A dictionary with a 'message' key if the schedule was successfully created, 
          or an 'error' key if there was an error.
    """
    try:
        # Validate the day
        if details.get('day').upper() not in ['MONDAY', 'TUESDAY', 'WEDNESDAY', 'THURSDAY', 'FRIDAY', 'SATURDAY', 'SUNDAY']:
            return {"error": 'The provided day for the schedule is invalid, please check that the day falls under any day in the Gregorian calendar'}

        # Fetch the user account
        account = CustomUser.objects.get(account_id=user)

        for_group_schedule = details.get('for_group')
        if for_group_schedule:
            # Fetch the group schedule and validate school association
            group_schedule = GroupSchedule.objects.get(group_schedule_id=details.get('group_schedule_id'))
            if group_schedule.grade.school != account.school:
                return {"error": 'the specified group schedule does not belong to your school. please ensure you are attempting to create schedules for a group schedule from your school'}
        else:
            # Fetch the teacher account and validate school and role
            teacher = CustomUser.objects.get(account_id=details.get('account_id'))
            if teacher.school != account.school or teacher.role != 'TEACHER':
                return {"error": 'the specified teacher account is either not a teacher or does not belong to your school. please ensure you are attempting to create schedules for a teacher enrolled in your school'}

        # Begin database transaction
        with transaction.atomic():
            # Create and save the schedule
            schedule = Schedule(day=details.get('day').upper(), day_order=Schedule.DAY_OF_THE_WEEK_ORDER[details.get('day').upper()])
            schedule.save()  # Save to generate a unique schedule_id

            # Iterate over the sessions in the provided data
            for session_info in details.get('sessions'):
                # Convert the start and end times to Time objects
                start_time = parse_time(f"{session_info['startTime']['hour']}:{session_info['startTime']['minute']}:{session_info['startTime']['second']}")
                end_time = parse_time(f"{session_info['endTime']['hour']}:{session_info['endTime']['minute']}:{session_info['endTime']['second']}")

                # Create a new Session object and save it
                session = Session(type=session_info['class'], classroom=session_info.get('classroom'), session_from=start_time, session_till=end_time)
                session.save()

                # Add the session to the schedule's sessions
                schedule.sessions.add(session)

            # Save the schedule again to commit the added sessions
            schedule.save()

            if for_group_schedule:
                # Remove the specific schedules for that day from the group schedule
                group_schedule.schedules.filter(day=details.get('day').upper()).delete()

                # Add the new schedule to the group's schedules and save
                group_schedule.schedules.add(schedule)
                group_schedule.save()

                # Return a success response
                return {'message': 'a new schedule has been added to the group\'s weekly schedules. all subscribed students should be able to view all the sessions concerning the schedule when they visit their schedules again.'}

            else:
                # Get or create the TeacherSchedule object for the teacher
                teacher_schedule, created = TeacherSchedule.objects.get_or_create(teacher=teacher)
                
                if not created:
                    # Remove the specific schedules for that day from the teacher's existing schedules
                    teacher_schedule.schedules.filter(day=details.get('day').upper()).delete()

                # Add the new schedule to the teacher's schedules and save
                teacher_schedule.schedules.add(schedule)
                teacher_schedule.save()

                # Return a success response
                return {'message': 'a new schedule has been added to the teacher\'s weekly schedules. they should be able to view all the sessions concerning the schedule when they visit their schedules again.'}

    except CustomUser.DoesNotExist:
        # Handle case where user account does not exist
        return {'error': 'an account with the provided credentials does not exist, please check the account details and try again'}

    except GroupSchedule.DoesNotExist:
        # Handle case where group schedule does not exist
        return {'error': 'a group schedule with the provided credentials does not exist, please check the group details and try again'}

    except Exception as e:
        # Handle any other exceptions
        return {'error': str(e)}


@database_sync_to_async
def create_group_schedule(user, details):

    try:
        account = CustomUser.objects.get(account_id=user)
        grade = Grade.objects.get(grade_id=details.get('grade_id'))

        if account.school != grade.school:
            return { "error" : 'you do not have permission to perform this action because the specified grade does not belong to your school. please ensure you are attempting to create a group schedule in a grade within your own school' }

        with transaction.atomic():
            group_schedule = GroupSchedule.objects.create(group_name=details.get('group_name'), grade=grade)
            group_schedule.save()

        # Return a success response
        return {'message': 'you can now add individual daily schedules and subscribe students in the grade to the group schedule for a shared weekly schedule'}
    
    except CustomUser.DoesNotExist:
        return {'error': 'the account with the provided credentials does not exist, please check the account details and try again'}
        
    except Grade.DoesNotExist:
        return {'error': 'a grade with the provided credentials does not exist, please check your details and try again'}

    except Exception as e:
        return { 'error': str(e) }
    

@database_sync_to_async
def delete_schedule(user, details):
    """
    Deletes a specific schedule for a teacher or group.

    Parameters:
    user (str): The account ID of the user requesting the deletion.
    details (dict): A dictionary containing the schedule details. It should include:
        - 'schedule_id' (str): The ID of the schedule to be deleted.
        - 'for_group' (bool): Flag indicating whether the schedule is for a group.

    Returns:
    dict: A dictionary with a 'message' key if the schedule was successfully deleted,
          or an 'error' key if there was an error.
    """
    try:
        # Fetch the user account making the request
        account = CustomUser.objects.get(account_id=user)
        
        # Retrieve the schedule object
        schedule = Schedule.objects.get(schedule_id=details.get('schedule_id'))

        for_group = details.get('for_group')
        if for_group:
            # Retrieve the GroupSchedule object linked to this schedule
            group_schedule = schedule.group_linked_to.first()

            # Check if the user has permission to delete the schedule
            if not group_schedule or account.school != group_schedule.grade.school:
                return {"error": 'permission denied. you can only delete schedules from your own school.'}
        else:
            # Retrieve the TeacherSchedule object linked to this schedule
            teacher_schedule = schedule.teacher_linked_to.first()

            # Check if the user has permission to delete the schedule
            if not teacher_schedule or account.school != teacher_schedule.teacher.school:
                return {"error": 'permission denied. you can only delete schedules from your own school'}

        # Delete the schedule
        schedule.delete()
        
        if for_group:
            return {'message': 'the schedule has been successfully deleted from the group schedule and will be removed from schedules of all students subscribed to the group schedule'}
        
        else:
            return {'message': 'the schedule has been successfully deleted from the teachers schedule and will no longer be available to the teacher'}
        
    except CustomUser.DoesNotExist:
        return {'error': 'an account with the provided credentials does not exist. Please check the account details and try again.'}
    
    except Schedule.DoesNotExist:
        return {'error': 'a schedule with the provided ID does not exist. Please check the schedule details and try again.'}

    except Exception as e:
        return {'error': str(e)}


@database_sync_to_async
def delete_group_schedule(user, details):
    """
    Deletes a specific group schedule.

    Parameters:
    user (str): The account ID of the user requesting the deletion.
    details (dict): A dictionary containing the group schedule details. It should include:
        - 'group_schedule_id' (str): The ID of the group schedule to be deleted.

    Returns:
    dict: A dictionary with a 'message' key if the group schedule was successfully deleted,
          or an 'error' key if there was an error.
    """
    try:
        # Fetch the user account making the request
        account = CustomUser.objects.get(account_id=user)
        
        # Retrieve the group schedule object
        group_schedule = GroupSchedule.objects.get(group_schedule_id=details.get('group_schedule_id'))

        # Check if the user has permission to delete the group schedule
        if account.school != group_schedule.grade.school:
            return {"error": 'permission denied. you can only delete group schedules from your own school'}

        # Delete the group schedule
        group_schedule.delete()
        
        return {'message': 'The group schedule has been successfully deleted'}
        
    except CustomUser.DoesNotExist:
        return {'error': 'an account with the provided credentials does not exist. please check the account details and try again.'}
    
    except GroupSchedule.DoesNotExist:
        return {'error': 'a group schedule with the provided ID does not exist. please check the group schedule details and try again.'}

    except Exception as e:
        return {'error': str(e)}


@database_sync_to_async
def add_students_to_group_schedule(user, details):
    """
    Adds students to a specific group schedule.

    Args:
        user (str): The account ID of the user making the request.
        details (dict): A dictionary containing the group_schedule_id and a list of student IDs.

    Returns:
        dict: A dictionary containing a success message or an error message.

    Raises:
        CustomUser.DoesNotExist: If the user with the provided account ID does not exist.
        GroupSchedule.DoesNotExist: If the group schedule with the provided ID does not exist.
        Exception: For any other unexpected errors.
    """
    try:
        # Retrieve the account making the request
        account = CustomUser.objects.get(account_id=user)
        
        # Retrieve the group schedule object
        group_schedule = GroupSchedule.objects.get(group_schedule_id=details.get('group_schedule_id'))

        # Check if the user has permission to modify the group schedule
        if account.school != group_schedule.grade.school:
            return {"error": 'Permission denied. You can only modify group schedules from your own school.'}
        
        # Get the list of student IDs from the details
        students_list = details.get('students').split(', ')
        
        # Check if any of the provided students are already in the group schedule
        existing_students = [student for student in students_list if group_schedule.students.filter(account_id=student).exists()]
        
        if existing_students:
            return {'error': 'Invalid request. The provided list of students includes students that are already in this class. Please review the list of students and submit again.'}
        
        # Add students to the group schedule within a transaction
        with transaction.atomic():
            for student in students_list:
                group_schedule.students.add(CustomUser.objects.get(account_id=student, school=account.school, grade=group_schedule.grade))

            group_schedule.save()
            
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
    Removes students from a specific group schedule.

    Args:
        user (str): The account ID of the user making the request.
        details (dict): A dictionary containing the group_schedule_id and a list of student IDs.

    Returns:
        dict: A dictionary containing a success message or an error message.

    Raises:
        CustomUser.DoesNotExist: If the user with the provided account ID does not exist.
        GroupSchedule.DoesNotExist: If the group schedule with the provided ID does not exist.
        Exception: For any other unexpected errors.
    """
    try:
        # Retrieve the account making the request
        account = CustomUser.objects.get(account_id=user)
        
        # Retrieve the group schedule object
        group_schedule = GroupSchedule.objects.get(group_schedule_id=details.get('group_schedule_id'))

        # Check if the user has permission to modify the group schedule
        if account.school != group_schedule.grade.school:
            return {"error": 'Permission denied. You can only modify group schedules from your own school.'}
        
        # Get the list of student IDs from the details
        students_list = details.get('students').split(', ')
        
        # Remove students from the group schedule within a transaction
        with transaction.atomic():
            for student in students_list:
                group_schedule.students.remove(CustomUser.objects.get(account_id=student, school=account.school, grade=group_schedule.grade))

            group_schedule.save()
        
        
        # Get all students subscribed to this group schedule
        students = group_schedule.students.all()

        # Serialize the students
        serializer = AccountSerializer(students, many=True)

        return {"students": serializer.data, 'message': 'students successfully removed from group schedule'}
        
    except CustomUser.DoesNotExist:
        return {'error': 'An account with the provided credentials does not exist. Please check the account details and try again.'}
            
    except GroupSchedule.DoesNotExist:
        return {'error': 'A group schedule with the provided credentials does not exist. Please check the group schedule details and try again.'}

    except Exception as e:
        return {'error': str(e)}


@database_sync_to_async
def add_students_to_class(user, details):
    """
    Adds students to a specified class, either a register class or a subject class.

    Args:
        user (str): The account ID of the user making the request.
        details (dict): A dictionary containing:
            - class_id (str): The ID of the class.
            - register (bool): Whether the class is a register class.
            - students (str): A comma-separated string of student account IDs.

    Returns:
        dict: A dictionary containing a success message or an error message.

    Raises:
        CustomUser.DoesNotExist: If the user with the provided account ID does not exist.
        Classroom.DoesNotExist: If the classroom with the provided class ID does not exist.
        Exception: For any other unexpected errors.
    """
    try:
        # Retrieve the account making the request
        account = CustomUser.objects.get(account_id=user)
        
        # Retrieve the classroom with the provided class ID
        classroom = Classroom.objects.get(class_id=details.get('class_id'))

        register = details.get('register')
        if register:
            # Check if the user has permission to add students to the register class
            if account.school != classroom.school or classroom.register_class == False:
                return {"error": "permission denied. the provided classroom is either not from your school or is not a register class. you can only manage register classes from your own school."}
        else:
            # Check if the user has permission to add students to the subject class
            if account.school != classroom.school or not classroom.subject:
                return {"error": "permission denied. the provided classroom is either not from your school or has no subject linked to it. you can only manage subject classes from your own school."}

        if details.get('students') == '':
            return {'error': 'invalid request. no students were provided. please provide students to be added to the specified class.'}
        
        # Split the comma-separated string of student account IDs into a list
        students_list = details.get('students').split(', ')
        
        # Check for existing students in the class
        existing_students = []
        for student in students_list:
            if classroom.students.filter(account_id=student).exists():
                existing_students.append(student)
        
        if existing_students:
            return {'error': f'invalid request. the provided list of students includes students that are already in this class. please review the list of students and try again.'}
        
        # Use a transaction to ensure atomicity
        with transaction.atomic():
            for student in students_list:
                # Add each student to the classroom
                classroom.students.add(CustomUser.objects.get(account_id=student, school=account.school, grade=classroom.grade))

            classroom.save()
        
        if register:
            return {'message': f'the provided list of students are now part of the grade {classroom.grade.grade}, group {classroom.group.title()} register class.'}

        else:
            return {'message': f'the provided list of students are now part of the grade {classroom.grade.grade}, group {classroom.group.title()} {classroom.subject.subject.lower()} class.'}

    except CustomUser.DoesNotExist:
        # Handle case where the user account does not exist
        return {'error': 'an account with the provided credentials does not exist. please check the account details and try again.'}
    
    except Classroom.DoesNotExist:
        # Handle case where the classroom does not exist
        return {'error': 'a classroom with the provided credentials does not exist. please check the classroom details and try again.'}

    except Exception as e:
        # Handle any other unexpected errors
        return {'error': str(e)}


@database_sync_to_async
def remove_student_from_class(user, details):
    """
    Removes a student from a specified register class.

    Args:
        user (str): The account ID of the user making the request.
        details (dict): A dictionary containing:
            - class_id (str): The ID of the class.
            - account_id (str): The account ID of the student to be removed.

    Returns:
        dict: A dictionary containing a success message or an error message.

    Raises:
        CustomUser.DoesNotExist: If the user with the provided account ID does not exist.
        Classroom.DoesNotExist: If the classroom with the provided class ID does not exist.
        Exception: For any other unexpected errors.
    """
    try:
        # Retrieve the account making the request
        account = CustomUser.objects.get(account_id=user)
        
        # Retrieve the classroom with the provided class ID and school, ensuring it is a register class
        classroom = Classroom.objects.get(class_id=details.get('class_id'))

        # Check if the user has permission to remove students from the class
        if account.school != classroom.school:
            return {"error": "permission denied. the provided classroom is not from your school. you can only manage classes from your own school."}

        # Check if the student is part of the classroom
        if classroom.students.filter(account_id=details.get('account_id')).exists():
            # Use a transaction to ensure atomicity
            with transaction.atomic():
                # Remove the student from the classroom
                classroom.students.remove(classroom.students.get(account_id=details.get('account_id')))
                classroom.save()
            
            return {'message': f'the student has been successfully removed from the class, and will no longer be associated or have access to data linked to the class'}
        
        return {'error': 'cannot remove student from class.. the student with the provided credentials is not part of the class'}
               
    except CustomUser.DoesNotExist:
        # Handle case where the user account does not exist
        return {'error': 'account with the provided credentials does not exist'}
    
    except Classroom.DoesNotExist:
        # Handle case where the classroom does not exist
        return {'error': 'class with the provided credentials does not exist'}

    except Exception as e:
        # Handle any other unexpected errors
        return {'error': str(e)}

    

@database_sync_to_async
def form_data_for_class_creation(user):

    try:
        account = CustomUser.objects.get(account_id=user)

        accounts = CustomUser.objects.filter(role='TEACHER', school=account.school).order_by('name', 'surname', 'account_id')
        serializer = AccountSerializer(accounts, many=True)

        return { "teachers" : serializer.data }
        
    except CustomUser.DoesNotExist:
        return { 'error': 'account with the provided credentials does not exist' }
    
    except Exception as e:
        return { 'error': str(e) }
    

@database_sync_to_async
def form_data_for_class_update(user, details):
    """
    Retrieves the data needed for updating a classroom's details, including available teachers and current teacher assignment.

    Args:
        user (str): The account ID of the user making the request.
        details (dict): A dictionary containing the class ID to identify the class.

    Returns:
        dict: A dictionary containing the current teacher, list of available teachers, group, and classroom identifier, 
              or an error message.

    Raises:
        CustomUser.DoesNotExist: If the user with the provided account ID does not exist.
        Classroom.DoesNotExist: If the classroom with the provided class ID does not exist.
        Exception: For any other unexpected errors.
    """
    try:
        # Retrieve the account making the request
        account = CustomUser.objects.get(account_id=user)
        
        # Retrieve the classroom with the provided class ID
        classroom = Classroom.objects.get(class_id=details.get('class_id'))
                
        # Check if the user has permission to retrieve this list
        if account.school != classroom.school or classroom.register_class == False:
            return {"error": "permission denied. the provided classroom is not from your school. you can only update details of classes from your own school."}
        
        # Initialize the teacher and teachers list
        if classroom.teacher is not None:
            # Serialize the current teacher
            teacher = AccountSerializer(classroom.teacher).data
            # Retrieve other teachers from the same school, excluding the current teacher
            accounts = CustomUser.objects.filter(role='TEACHER', school=account.school).exclude(account_id=classroom.teacher.account_id).order_by('name', 'surname', 'account_id')
        else:
            # If no teacher is assigned to the classroom
            teacher = None
            # Retrieve all teachers from the same school
            accounts = CustomUser.objects.filter(role='TEACHER', school=account.school).order_by('name', 'surname', 'account_id')
        
        # Serialize the list of available teachers
        teachers = AccountSerializer(accounts, many=True).data
        
        # Return the data
        return { 'teacher': teacher, "teachers": teachers, 'group': classroom.group, 'classroom_identifier': classroom.classroom_identifier }

    except CustomUser.DoesNotExist:
        # Handle case where the user account does not exist
        return {'error': 'an account with the provided credentials does not exist. please check the account details and try again.'}
    
    except Classroom.DoesNotExist:
        # Handle case where the classroom does not exist
        return {'error': 'a classroom with the provided credentials does not exist. please check the classroom details and try again.'}
    
    except Exception as e:
        # Handle any other unexpected errors
        return { 'error': str(e) }

    

@database_sync_to_async
def form_data_add_students_to_group_schedule(user, details):
    """
    return students who are not subscribed to a specified group schedule.

    Args:
        user (str): The account ID of the user making the request.
        details (dict): A dictionary containing the group_schedule_id to identify the group schedule.

    Returns:
        dict: A dictionary containing the list of students who can be added to the group schedule or an error message.

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

        # Check if the user has permission to add students to the group schedule
        if account.school != group_schedule.grade.school:
            return {"error": "permission denied. you can only view details about group schedules from your own school."}

        # Get all students who are in the same grade but not subscribed to this group schedule
        students_in_grade = CustomUser.objects.filter(grade=group_schedule.grade, role='STUDENT').exclude(my_group_schedule=group_schedule)

        # Serialize the students
        serializer = AccountSerializer(students_in_grade, many=True)

        return {"students": serializer.data}

    except CustomUser.DoesNotExist:
        # Handle case where the user account does not exist
        return {'error': 'an account with the provided credentials does not exist. please check the account details and try again.'}
            
    except GroupSchedule.DoesNotExist:
        return {'error': 'a group schedule with the provided credentials does not exist. Please check the group schedule details and try again.'}

    except Exception as e:
        return {'error': str(e)}
    

@database_sync_to_async
def form_data_for_adding_students_to_register_class(user, details):
    """
    Retrieves a list of students who are in the same grade as the specified class but are not currently enrolled in any register class.

    Args:
        user (str): The account ID of the user making the request.
        details (dict): A dictionary containing the class ID to identify the class.

    Returns:
        dict: A dictionary containing either the list of students or an error message.

    Raises:
        CustomUser.DoesNotExist: If the user with the provided account ID does not exist.
        Classroom.DoesNotExist: If the classroom with the provided class ID does not exist.
        Exception: For any other unexpected errors.
    """
    try:
        # Retrieve the account making the request
        account = CustomUser.objects.get(account_id=user)
        
        # Retrieve the classroom with the provided class ID within the user's school
        classroom = Classroom.objects.get(class_id=details.get('class_id'))
                
        # Check if the user has permission to retrieve this list
        if account.school != classroom.school or classroom.register_class == False:
            return {"error": "permission denied the provided classsroom is either not from your school or is not a register class. you can only view details about register classes from your own school."}

        # Get all students who are in the same grade and already in a register class
        students_in_register_classes = CustomUser.objects.filter(enrolled_classes__grade=classroom.grade, enrolled_classes__register_class=True)
        
        # Exclude these students from the list of students in the current classroom's grade
        students = classroom.grade.students.exclude(id__in=students_in_register_classes)
        
        # Serialize the list of students to return them in the response
        serializer = AccountSerializer(students, many=True)

        return {"students": serializer.data}

    except CustomUser.DoesNotExist:
        # Handle case where the user account does not exist
        return {'error': 'an account with the provided credentials does not exist. please check the account details and try again.'}
    
    except Classroom.DoesNotExist:
        # Handle case where the classroom does not exist
        return {'error': 'a classroom with the provided credentials does not exist. please check the classroom details and try again.'}
    
    except Exception as e:
        # Handle any other unexpected errors
        return {'error': str(e)}

    

@database_sync_to_async
def form_data_for_adding_students_to_subject_class(user, details):
    """
    Retrieves a list of students who are in the same grade as the specified class but are not currently enrolled in that class or any other class within the same subject.

    Args:
        user (str): The account ID of the user making the request.
        details (dict): A dictionary containing the class ID to identify the class.

    Returns:
        dict: A dictionary containing either the list of students or an error message.

    Raises:
        CustomUser.DoesNotExist: If the user with the provided account ID does not exist.
        Classroom.DoesNotExist: If the classroom with the provided class ID does not exist.
        Exception: For any other unexpected errors.
    """
    try:
        # Retrieve the account making the request
        account = CustomUser.objects.get(account_id=user)
        
        # Retrieve the classroom with the provided class ID within the user's school
        classroom = Classroom.objects.get(class_id=details.get('class_id'))
        
        # Check if the user has permission to retrieve this list
        if account.school != classroom.school or not classroom.subject:
            return {"error": "permission denied the provided classsroom is either not from your school or has no subject linked to it. you can only view details about subject classes from your own school."}

        # Get all students who are in the same grade as the classroom
        students_in_same_grade = CustomUser.objects.filter(grade=classroom.grade)
        
        # Get all students who are already enrolled in any class within the same subject as the specified classroom
        students_in_subject_classes = CustomUser.objects.filter(enrolled_classes__subject=classroom.subject)

        # Exclude these students from the list of students in the same grade
        students = students_in_same_grade.exclude(id__in=students_in_subject_classes)

        # Serialize the list of students to return them in the response
        serializer = AccountSerializer(students, many=True)

        return {"students": serializer.data}

    except CustomUser.DoesNotExist:
        # Handle case where the user account does not exist
        return {'error': 'an account with the provided credentials does not exist. please check the account details and try again.'}
    
    except Classroom.DoesNotExist:
        # Handle case where the classroom does not exist
        return {'error': 'a classroom with the provided credentials does not exist. please check the classroom details and try again.'}

    except Exception as e:
        # Handle any other unexpected errors
        return {'error': str(e)}



    