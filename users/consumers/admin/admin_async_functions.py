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
from timetables.models import Session, Schedule, TeacherSchedule
from grades.models import Grade, Subject
from classes.models import Classroom

# serilializers
from users.serializers import AccountUpdateSerializer, IDSerializer, ProfileSerializer, StudentProfileSerializer, UsersSerializer, AccountCreationSerializer, TeachersSerializer, StudentAccountCreationIDSerializer, StudentAccountCreationPNSerializer
from timetables.serializers import SchedulesSerializer
from grades.serializers import GradesSerializer, GradeSerializer, SubjectDetailSerializer
from classes.serializers import ClassSerializer, ClassUpdateSerializer, TeacherClassesSerializer

# utility functions 
    
    
@database_sync_to_async
def create_account(user, name, surname, email, role):

    try:
        account = CustomUser.objects.get(account_id=user)
        data = {'name': name, 'surname': surname, 'email': email, 'school': account.school.pk, 'role': role}
        
        if CustomUser.objects.filter(email=email).exists():
            return {"error": "an account with the provided email address already exists"}
        
        serializer = AccountCreationSerializer(data=data)
        
        if serializer.is_valid():
            
            with transaction.atomic():
                user = CustomUser.objects.create_user(**serializer.validated_data)
            
            return {'user' : user}
            
        return {"error" : serializer.errors}
    
    except IntegrityError as e:
        return {'error': 'account with the provided email address already exists'}
           
    except CustomUser.DoesNotExist:
        return { 'error': 'account with the provided credentials does not exist' }
    
    except Exception as e:
        return { 'error': str(e) }


@database_sync_to_async
def create_student_account(user, name, surname, email, grade_id, identification, citizen):

    try:
        if email != '':
            if CustomUser.objects.filter(email=email).exists():
                return {"error": "an account with the provided email address already exists"}
        
        account = CustomUser.objects.get(account_id=user)
        grade = Grade.objects.get(grade_id=grade_id, school=account.school)
        
        if citizen == 'yes':
            if CustomUser.objects.filter(id_number=identification).exists():
                return {"error": "a user with this ID number already exists."}
            
            data = {'name': name, 'surname': surname, 'email': email, 'grade': grade.pk, 'school': account.school.pk, 'role': 'STUDENT', 'id_number': identification}
            serializer = StudentAccountCreationIDSerializer(data=data)
        
        else:
            if CustomUser.objects.filter(passport_number=identification).exists():
                return {"error": "a user with this Passport Number already exists."}
            
            data = {'name': name, 'surname': surname, 'email': email, 'grade': grade.pk, 'school': account.school.pk, 'role': 'STUDENT', 'passport_number': identification}
            serializer = StudentAccountCreationPNSerializer(data=data)
        
        if serializer.is_valid():
            
            with transaction.atomic():
                user = CustomUser.objects.create_user(**serializer.validated_data)
            
            if email != '':
                return {'user' : user }
            
            else:
                return {'message' : 'student account successfully created.. you can now link a parent, add to classes and much more'}
            
        return {"error" : serializer.errors}
    
    except IntegrityError as e:
        return {'error': 'account with the provided email address already exists'}
           
    except CustomUser.DoesNotExist:
        return { 'error': 'account with the provided credentials does not exist' }
    
    except Grade.DoesNotExist:
        return { 'error': 'grade with the provided credentials does not exist' }

    except Exception as e:
        return { 'error': str(e) }


@database_sync_to_async
def update_account(user, updates, account_id):

    try:
        if updates.get('email') != (None or ''):
            if CustomUser.objects.filter(email=updates.get('email')).exists():
                return {"error": "an account with the provided email address already exists"}

        admin = CustomUser.objects.get(account_id=user)
        account  = CustomUser.objects.get(account_id=account_id, school=admin.school)

        if account.role == 'FOUNDER' or (account.role in ['PRINCIPAL', 'ADMIN'] and admin.role != 'PRINCIPAL') or (account.role != 'PARENT' and admin.school != account.school) or account.role == 'PARENT':
            return { "error" : 'unauthorized access.. permission denied' }
        
        serializer = AccountUpdateSerializer(instance=account, data=updates)
        
        if serializer.is_valid():
            
            with transaction.atomic():
                serializer.save()
                account.refresh_from_db()  # Refresh the user instance from the database
            
            serializer = IDSerializer(instance=account)
            return { "user" : serializer.data }
            
        return {"error" : serializer.errors}
    
    except IntegrityError as e:
        return {'error': 'account with the provided email address already exists'}
    
    except CustomUser.DoesNotExist:
        return { 'error': 'account with the provided credentials does not exist' }
    
    except Exception as e:
        return { 'error': str(e) }
    
    
@database_sync_to_async
def delete_account(user, account_id):

    try:
        admin = CustomUser.objects.get(account_id=user)
        account  = CustomUser.objects.get(account_id=account_id)

        if account.role == 'FOUNDER' or (account.role in ['PRINCIPAL', 'ADMIN'] and admin.role != 'PRINCIPAL') or (account.role != 'PARENT' and admin.school != account.school) or account.role == 'PARENT':
            return { "error" : 'unauthorized action.. permission denied' }
        
        account.delete()
                            
        return {"message" : 'account successfully deleted'}
        
    except CustomUser.DoesNotExist:
        return { 'error': 'account with the provided credentials does not exist' }
    
    except Exception as e:
        return { 'error': str(e) }
    

@database_sync_to_async
def search_account_profile(user, account_id):

    try:
        admin = CustomUser.objects.get(account_id=user)
        account  = CustomUser.objects.get(account_id=account_id)

        if account.role == 'FOUNDER' or (account.role != 'PARENT' and admin.school != account.school) or (account.role == 'PARENT' and not account.children.filter(school=admin.school).exists()):
            return { "error" : 'unauthorized access.. permission denied' }

        if account.role == 'STUDENT':
            serializer = StudentProfileSerializer(instance=account)
        else:
            serializer = ProfileSerializer(instance=account)

        return { "user" : serializer.data }
        
    except CustomUser.DoesNotExist:
        return { 'error': 'account with the provided credentials does not exist' }
    
    except Exception as e:
        return { 'error': str(e) }
    
    
@database_sync_to_async
def search_account_id(user, account_id):

    try:
        admin = CustomUser.objects.get(account_id=user)
        account  = CustomUser.objects.get(account_id=account_id)

        if account.role == 'FOUNDER' or (account.role != 'PARENT' and admin.school != account.school) or (account.role == 'PARENT' and not account.children.filter(school=admin.school).exists()):
            return { "error" : 'unauthorized access.. permission denied' }

        # return the users profile
        serializer = IDSerializer(instance=account)
        return { "user" : serializer.data }
        
    except CustomUser.DoesNotExist:
        return { 'error': 'account with the provided credentials does not exist' }
    
    except Exception as e:
        return { 'error': str(e) }
    

@database_sync_to_async
def search_accounts(user, role):

    try:
        if role not in ['ADMIN', 'TEACHER']:
            return { "error" : 'invalid role request' }
        
        account = CustomUser.objects.get(account_id=user)

        if role == 'ADMIN':
            accounts = CustomUser.objects.filter( Q(role='ADMIN') | Q(role='PRINCIPAL'), school=account.school).exclude(account_id=user)
    
        if role == 'TEACHER':
            accounts = CustomUser.objects.filter(role=role, school=account.school)

        serializer = UsersSerializer(accounts, many=True)
        return { "users" : serializer.data }
        
    except CustomUser.DoesNotExist:
        return { 'error': 'account with the provided credentials does not exist' }
    
    except Exception as e:
        return { 'error': str(e) }


SCHOOL_GRADES_CHOICES = [('000', 'Grade 000'), ('00', 'Grade 00'), ('R', 'Grade R'), ('1', 'Grade 1'), ('2', 'Grade 2'), ('3', 'Grade 3'), ('4', 'Grade 4'), ('5', 'Grade 5'), ('6', 'Grade 6'), ('7', 'Grade 7'), ('8', 'Grade 8'), ('9', 'Grade 9'), ('10', 'Grade 10'), ('11', 'Grade 11'), ('12', 'Grade 12')]

@database_sync_to_async
def create_grade(user, grade, subjects):

    try:
        account = CustomUser.objects.get(account_id=user)

        if Grade.objects.filter(grade=grade, school=account.school).exists():
            return {"error": f"grade {grade} already exists for the school, duplicate grades is not allowed"}
        
        # Calculate the grade order
        grade_order = [choice[0] for choice in SCHOOL_GRADES_CHOICES].index(grade)

        with transaction.atomic():
            # Include the grade_order when creating the Grade instance
            grad = Grade.objects.create(grade=grade, grade_order=grade_order, school=account.school)
            grad.save()

            if subjects:
                subject_list = subjects.split(', ')
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
def fetch_student_grades(user):

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
def search_grade(user, grade_id):

    try:
        account = CustomUser.objects.get(account_id=user)
        
        grade  = Grade.objects.get(school=account.school, grade_id=grade_id)
        serializer = GradeSerializer(instance=grade)

        return { 'grade' : serializer.data}
    
    except Grade.DoesNotExist:
        return { 'error': 'grade with the provided credentials does not exist' }

    except CustomUser.DoesNotExist:
        return { 'error': 'account with the provided credentials does not exist' }
    
    except Exception as e:
        return { 'error': str(e) }


@database_sync_to_async
def create_subjects(user, grade_id, subjects):

    try:
        account = CustomUser.objects.get(account_id=user)
        grade = Grade.objects.get(grade_id=grade_id, school=account.school)

        if subjects == '':
            return { 'error': f'invalid request.. no subjects were provided' }
        
        subject_list = subjects.split(', ')
        
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
def search_subject(user, grade_id, subject_id):

    try:
        account = CustomUser.objects.get(account_id=user)
        grade  = Grade.objects.get(school=account.school, grade_id=grade_id)

        subject = Subject.objects.get(subject_id=subject_id, grade=grade)

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
def create_subject_class(user, grade_id, subject_id, group, classroom, classroom_teacher):

    try:
        account = CustomUser.objects.get(account_id=user)

        if classroom_teacher:
            teacher = CustomUser.objects.get(account_id=classroom_teacher, school=account.school)
        else:
            teacher = None

        grade = Grade.objects.get(grade_id=grade_id, school=account.school)
        subject = Subject.objects.get(subject_id=subject_id, grade=grade)

        with transaction.atomic():
            new_class = Classroom.objects.create(classroom_identifier=classroom, group=group, grade=grade, teacher=teacher, school=account.school, subject=subject)
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
def update_class(user, class_id, updates):

    try:
        account = CustomUser.objects.get(account_id=user)
        classroom = Classroom.objects.get(class_id=class_id, school=account.school)

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
    
    except Grade.DoesNotExist:
        return { 'error': 'grade with the provided credentials does not exist' }
    
    except Subject.DoesNotExist:
        return { 'error': 'subject with the provided credentials does not exist' }

    except Exception as e:
        return { 'error': str(e) }
    

@database_sync_to_async
def search_class(user, class_id):

    try:
        account = CustomUser.objects.get(account_id=user)
        classroom = Classroom.objects.get(class_id=class_id, school=account.school)

        serializer = ClassSerializer(classroom)

        return {"class": serializer.data}
    
    except CustomUser.DoesNotExist:
        return { 'error': 'account with the provided credentials does not exist' }
           
    except Classroom.DoesNotExist:
        return { 'error': 'grade with the provided credentials does not exist' }
    
    except Exception as e:
        return { 'error': str(e) }


@database_sync_to_async
def search_teacher_classes(user, teacher_id):

    try:
        account = CustomUser.objects.get(account_id=user)
        classes = CustomUser.objects.get(account_id=teacher_id, school=account.school).taught_classes.all()

        serializer = TeacherClassesSerializer(classes, many=True)

        return {"classes": serializer.data}
    
    except CustomUser.DoesNotExist:
        return { 'error': 'account with the provided credentials does not exist' }
           
    except Classroom.DoesNotExist:
        return { 'error': 'grade with the provided credentials does not exist' }
    
    except Exception as e:
        return { 'error': str(e) }
    

@database_sync_to_async
def search_students(user, grade_id):

    try:
        account = CustomUser.objects.get(account_id=user)
        students = Grade.objects.get(grade_id=grade_id, school=account.school.pk).students.all()

        serializer = UsersSerializer(students, many=True)

        return {"students": serializer.data}
    
    except CustomUser.DoesNotExist:
        return { 'error': 'account with the provided credentials does not exist' }
           
    except Grade.DoesNotExist:
        return { 'error': 'grade with the provided credentials does not exist' }
    
    except Exception as e:
        return { 'error': str(e) }
    

@database_sync_to_async
def create_teacher_schedule(user, details):

    try:
        sessions = details['sessions']
        day_of_week = details['day'].upper()
        account_id = details['account_id']

        if not sessions or not day_of_week or not account_id:
            return { "error" : 'missing information' }

        if day_of_week not in [ 'MONDAY', 'TUESDAY', 'WEDNESDAY', 'THURSDAY', 'FRIDAY', 'SATURDAY', 'SUNDAY']:
            return { "error" : 'invalid schedule day' }

        admin = CustomUser.objects.get(account_id=user)
        account = CustomUser.objects.get(account_id=account_id, role='TEACHER')

        if account.school != admin.school:
            return { "error" : 'unauthorized access.. permission denied' }

        with transaction.atomic():
            
            schedule = Schedule(day=day_of_week)
            schedule.save()  # Save to generate a unique schedule_id
            
            # Iterate over the sessions in the provided data
            for session_info in sessions:
                
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
            existing_teacher_schedule = TeacherSchedule.objects.filter(teacher=account, schedules__day=day_of_week)

            for schedules in existing_teacher_schedule:
                # Remove the specific schedules for that day
                schedules.schedules.filter(day=day_of_week).delete()

            # Check if the teacher already has a TeacherSchedule object
            teacher_schedule, created = TeacherSchedule.objects.get_or_create(teacher=account)

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
        return { 'error': 'account with the provided credentials does not exist' }
    
    except Exception as e:
        return { 'error': str(e) }


@database_sync_to_async
def delete_teacher_schedule(user, schedule_id):

    try:
        admin = CustomUser.objects.get(account_id=user)
        
        # Retrieve the schedule object
        schedule = Schedule.objects.get(schedule_id=schedule_id)

        # Retrieve the TeacherSchedule object linked to this schedule
        teacher_schedule = schedule.teacher_linked_to.first()

        # Check if the user has permission to delete the schedule
        if admin.school != teacher_schedule.teacher.school:
            return {"error": 'permission denied'}

        # Delete the schedule
        schedule.delete()
        
        # Return a success response
        return {'message': 'Schedule deleted successfully'}
        
    except CustomUser.DoesNotExist:
        return { 'error': 'account with the provided credentials does not exist' }
    
    except Exception as e:
        return { 'error': str(e) }
    

@database_sync_to_async
def search_teacher_schedules(user, account_id):

    try:
        admin = CustomUser.objects.get(account_id=user)
        account  = CustomUser.objects.get(account_id=account_id)

        if account.role != 'TEACHER' or  admin.school != account.school:
            return { "error" : 'unauthorized access.. permission denied' }
        
        if hasattr(account, 'teacher_schedule'):
            teacher_schedule = account.teacher_schedule
            schedules = teacher_schedule.schedules.all().order_by('day')
            serializer = SchedulesSerializer(schedules, many=True)
    
            return {"schedules": serializer.data}
        
        else:
            return {"schedules": []}
        
    except CustomUser.DoesNotExist:
        return { 'error': 'account with the provided credentials does not exist' }
    
    except Exception as e:
        return { 'error': str(e) }


@database_sync_to_async
def form_subject_class(user):

    try:
        account = CustomUser.objects.get(account_id=user)

        accounts = CustomUser.objects.filter(role='TEACHER', school=account.school).order_by('name', 'surname', 'account_id')
        serializer = TeachersSerializer(accounts, many=True)

        return { "teachers" : serializer.data }
        
    except CustomUser.DoesNotExist:
        return { 'error': 'account with the provided credentials does not exist' }
    
    except Exception as e:
        return { 'error': str(e) }
    

@database_sync_to_async
def form_class_update(user, class_id):

    try:
        account = CustomUser.objects.get(account_id=user)
        classroom = Classroom.objects.get(class_id=class_id, school=account.school)

        if classroom.teacher is not None:
            teacher = TeachersSerializer(classroom.teacher)

            accounts = CustomUser.objects.filter(role='TEACHER', school=account.school).exclude(account_id=classroom.teacher.account_id).order_by('name', 'surname', 'account_id')
            teachers = TeachersSerializer(accounts, many=True)

            return { 'teacher' : teacher.data, "teachers" : teachers.data, 'group' : classroom.group, 'classroom_identifier' : classroom.classroom_identifier  }
        
        else:
            accounts = CustomUser.objects.filter(role='TEACHER', school=account.school).order_by('name', 'surname', 'account_id')
            teachers = TeachersSerializer(accounts, many=True)

            return { 'teacher' : None, "teachers" : teachers.data, 'group' : classroom.group, 'classroom_identifier' : classroom.classroom_identifier  }
        
    except CustomUser.DoesNotExist:
        return { 'error': 'account with the provided credentials does not exist' }
            
    except Classroom.DoesNotExist:
        return { 'error': 'class with the provided credentials does not exist' }

    except Exception as e:
        return { 'error': str(e) }