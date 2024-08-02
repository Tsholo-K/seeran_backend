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
from timetables.serializers import GroupScheduleSerializer

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
def create_register_class(user, details):

    try:
        account = CustomUser.objects.get(account_id=user)

        if details.get('classroom_teacher'):
            teacher = CustomUser.objects.get(account_id=details.get('classroom_teacher'), school=account.school)
        else:
            teacher = None

        grade = Grade.objects.get(grade_id=details.get('grade_id'), school=account.school)

        if Classroom.objects.filter(group=details.get('group'), grade=grade, school=account.school, register_class=True).exists():
            return {"error": "a register class with the provided group in the same grade already exists.. a class group should be unique in the same grade and subject(if applicable)"}

        with transaction.atomic():
            new_class = Classroom.objects.create(classroom_identifier=details.get('classroom'), group=details.get('group'), grade=grade, teacher=teacher, school=account.school, register_class=True)
            new_class.save()
            
        return { 'message': f'register class for grade {grade.grade} created successfully' }
               
    except CustomUser.DoesNotExist:
        return { 'error': 'account with the provided credentials does not exist' }
    
    except Grade.DoesNotExist:
        return { 'error': 'grade with the provided credentials does not exist' }

    except Exception as e:
        return { 'error': str(e) }


@database_sync_to_async
def create_subject_class(user, details):

    try:
        account = CustomUser.objects.get(account_id=user)

        if details.get('classroom_teacher'):
            teacher = CustomUser.objects.get(account_id=details.get('classroom_teacher'), school=account.school)
        else:
            teacher = None

        grade = Grade.objects.get(grade_id=details.get('grade_id'), school=account.school)
        subject = Subject.objects.get(subject_id=details.get('subject_id'), grade=grade)

        if Classroom.objects.filter(group=details.get('group'), grade=grade, school=account.school, subject=subject).exists():
            return {"error": "a class with the provided group in the same subject and grade already exists.. a class group should be unique in the same grade and subject"}

        with transaction.atomic():
            new_class = Classroom.objects.create(classroom_identifier=details.get('classroom'), group=details.get('group'), grade=grade, teacher=teacher, school=account.school, subject=subject)
            new_class.save()
            
        return { 'message': f'class for grade {grade.grade} {subject.subject.lower()} created successfully' }
               
    except CustomUser.DoesNotExist:
        return { 'error': 'account with the provided credentials does not exist' }
    
    except Grade.DoesNotExist:
        return { 'error': 'grade with the provided credentials does not exist' }
    
    except Subject.DoesNotExist:
        return { 'error': 'subject with the provided credentials does not exist' }

    except Exception as e:
        return { 'error': str(e) }


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
        return { 'error': 'account with the provided credentials does not exist' }
    
    except Classroom.DoesNotExist:
        return { 'error': 'classroom with the provided credentials does not exist' }

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
        return { 'error': 'account with the provided credentials does not exist' }
           
    except Classroom.DoesNotExist:
        return { 'error': 'grade with the provided credentials does not exist' }
    
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
        return { 'error': 'account with the provided credentials does not exist' }
           
    except Classroom.DoesNotExist:
        return { 'error': 'grade with the provided credentials does not exist' }
    
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

    try:
        if details.get('day').upper() not in [ 'MONDAY', 'TUESDAY', 'WEDNESDAY', 'THURSDAY', 'FRIDAY', 'SATURDAY', 'SUNDAY']:
            return { "error" : 'the provided day for the schedule is invalid, please check that the day falls under any day in the Gregorian calendar'}

        account = CustomUser.objects.get(account_id=user)
        teacher = CustomUser.objects.get(account_id=details.get('account_id'))

        if teacher.school != account.school or teacher.role != 'TEACHER':
            return { "error" : 'the specified teacher account is either not a teacher or does not belong to your school. please ensure you are attempting to create schedules for a parent from a teacher enrolled in your school'}

        with transaction.atomic():
            schedule = Schedule(day=details.get('day').upper(), day_order=Schedule.DAY_OF_THE_WEEK_ORDER[details.get('day').upper()])
            schedule.save()  # Save to generate a unique schedule_id
            
            # Iterate over the sessions in the provided data
            for session_info in details.get('sessions'):
                
                # Convert the start and end times to Time objects
                start_time = parse_time(f"{session_info['startTime']['hour']}:{session_info['startTime']['minute']}:{session_info['startTime']['second']}")
                end_time = parse_time(f"{session_info['endTime']['hour']}:{session_info['endTime']['minute']}:{session_info['endTime']['second']}")
                
                # Create a new Session object
                session = Session( type=session_info['class'], classroom=session_info.get('classroom'), session_from=start_time, session_till=end_time )
                session.save()
                
                # Add the session to the schedule's sessions
                schedule.sessions.add(session)
            
            # Save the schedule again to commit the added sessions
            schedule.save()

            # Check if the teacher already has a schedule for the provided day
            existing_teacher_schedules = TeacherSchedule.objects.filter(teacher=teacher, schedules__day=details.get('day').upper())

            for schedule in existing_teacher_schedules:
                # Remove the specific schedules for that day
                schedule.schedules.filter(day=details.get('day').upper()).delete()

            # Check if the teacher already has a TeacherSchedule object
            teacher_schedule, created = TeacherSchedule.objects.get_or_create(teacher=teacher)

            # If the object was created, a new unique teacher_schedule_id will be generated
            if created:
                teacher_schedule.save()

            # Add the new schedule to the teacher's schedules
            teacher_schedule.schedules.add(schedule)

            # Save the TeacherSchedule object to commit any changes
            teacher_schedule.save()

        # Return a success response
        return {'message': 'teacher schedule successfully created'}
        
    except ValidationError as e:
        # Handle specific known validation errors
        return {'error': str(e)}
    
    except CustomUser.DoesNotExist:
        return {'error': 'an account with the provided credentials does not exist, please check the account details and try again'}
    
    except Exception as e:
        return { 'error': str(e) }


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
def search_group_schedules(user, details):
    """
    Function to search and retrieve group schedules for a specific grade.

    Args:
        user (str): The account ID of the user making the request.
        details (dict): A dictionary containing the grade_id to identify the grade.

    Returns:
        dict: A dictionary containing either the group schedules or an error message.

    Raises:
        CustomUser.DoesNotExist: If the user with the provided account ID does not exist.
        Grade.DoesNotExist: If the grade with the provided ID does not exist.
        Exception: For any other unexpected errors.
    """
    try:
        # Retrieve the account making the request
        account = CustomUser.objects.get(account_id=user)
        
        # Retrieve the specified grade
        grade = Grade.objects.get(grade_id=details.get('grade_id'))

        # Ensure the specified grade belongs to the same school as the account's school
        if account.school != grade.school:
            return {"error": "the specified grade does not belong to your school. please ensure you are attempting to access group schedules for a grade in your own school"}

        # Retrieve all group schedules associated with the specified grade
        group_schedules = GroupSchedule.objects.filter(grade=grade)

        # Serialize the group schedules to return them in the response
        serializer = GroupScheduleSerializer(group_schedules, many=True)
        return {"schedules": serializer.data}
    
    except CustomUser.DoesNotExist:
        # Handle case where the user account does not exist
        return {'error': 'the account with the provided credentials does not exist, please check the account details and try again'}
    
    except Grade.DoesNotExist:
        # Handle case where the grade does not exist
        return {'error': 'the specified grade does not exist, please check the grade details and try again'}

    except Exception as e:
        # Handle any other unexpected errors
        return {'error': str(e)}
    

@database_sync_to_async
def delete_schedule(user, details):

    try:
        account = CustomUser.objects.get(account_id=user)
        
        # Retrieve the schedule object
        schedule = Schedule.objects.get(schedule_id=details.get('schedule_id'))

        # Retrieve the TeacherSchedule object linked to this schedule
        teacher_schedule = schedule.teacher_linked_to.first()

        # Check if the user has permission to delete the schedule
        if account.school != teacher_schedule.teacher.school:
            return {"error": 'unauthorized request.. permission denied'}

        # Delete the schedule
        schedule.delete()
        
        return {'message': 'schedule deleted successfully'}
        
    except CustomUser.DoesNotExist:
        return { 'error': 'account with the provided credentials does not exist' }
    
    except Exception as e:
        return { 'error': str(e) }


@database_sync_to_async
def add_students_to_register_class(user, details):

    try:
        account = CustomUser.objects.get(account_id=user)
        classroom = Classroom.objects.get(class_id=details.get('class_id'), school=account.school, register_class=True)

        if details.get('students') == '':
            return { 'error': f'invalid request.. no students were provided. please provide students to be added to the specified class' }
        
        students_list = details.get('students').split(', ')
        
        existing_students = []
        for student in students_list:
            if classroom.students.filter(account_id=student).exists():
                existing_students.append(student)
        
        if existing_students:
            return {'error' : f'invalid request.. the provided list of students includes students that are already in this class, please review the list of users then submit the list again'}
        
        with transaction.atomic():

            for student in students_list:
                classroom.students.add(CustomUser.objects.get(account_id=student, school=account.school, grade=classroom.grade))

            classroom.save()
            
        return {'message': 'students successfully added added to the class'}
        
    except CustomUser.DoesNotExist:
        return { 'error': 'account with the provided credentials does not exist' }
            
    except Classroom.DoesNotExist:
        return { 'error': 'register class with the provided credentials does not exist, request denied' }

    except Exception as e:
        return { 'error': str(e) }


@database_sync_to_async
def remove_student_from_register_class(user, details):

    try:
        account = CustomUser.objects.get(account_id=user)
        classroom = Classroom.objects.get(class_id=details.get('class_id'), school=account.school, register_class=True)

        if classroom.students.filter(account_id=details.get('account_id')).exists():
            with transaction.atomic():
                classroom.students.remove(classroom.students.get(account_id=details.get('account_id')))
                classroom.save()
            
            return { 'message': f'student successfully removed from register class group {classroom.group}' }
        
        return { 'error': f'can not remove student from class.. the provided student is not part of the register class' }
               
    except CustomUser.DoesNotExist:
        return { 'error': 'account with the provided credentials does not exist' }
    
    except Classroom.DoesNotExist:
        return { 'error': 'class with the provided credentials does not exist' }

    except Exception as e:
        return { 'error': str(e) }
    

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

    try:
        account = CustomUser.objects.get(account_id=user)
        classroom = Classroom.objects.get(class_id=details.get('class_id'), school=account.school)

        if classroom.teacher is not None:
            teacher = AccountSerializer(classroom.teacher).data
            accounts = CustomUser.objects.filter(role='TEACHER', school=account.school).exclude(account_id=classroom.teacher.account_id).order_by('name', 'surname', 'account_id')
        
        else:
            teacher = None
            accounts = CustomUser.objects.filter(role='TEACHER', school=account.school).order_by('name', 'surname', 'account_id')
            
        teachers = AccountSerializer(accounts, many=True).data
        return { 'teacher' : teacher, "teachers" : teachers, 'group' : classroom.group, 'classroom_identifier' : classroom.classroom_identifier  }
        
    except CustomUser.DoesNotExist:
        return { 'error': 'account with the provided credentials does not exist' }
            
    except Classroom.DoesNotExist:
        return { 'error': 'class with the provided credentials does not exist' }

    except Exception as e:
        return { 'error': str(e) }
    

@database_sync_to_async
def form_data_for_adding_students_to_register_class(user, details):

    try:
        account = CustomUser.objects.get(account_id=user)
        classroom = Classroom.objects.get(class_id=details.get('class_id'), school=account.school)

        # Get all students who are in the same grade and already in a register class
        students_in_register_classes = CustomUser.objects.filter(enrolled_classes__grade=classroom.grade, enrolled_classes__register_class=True)

        # Exclude these students from the current classroom's grade
        students = classroom.grade.students.exclude(id__in=students_in_register_classes)

        serializer = AccountSerializer(students, many=True)

        return {"students": serializer.data}
    
    except CustomUser.DoesNotExist:
        return { 'error': 'account with the provided credentials does not exist' }
            
    except Classroom.DoesNotExist:
        return { 'error': 'class with the provided credentials does not exist' }

    except Exception as e:
        return { 'error': str(e) }

    