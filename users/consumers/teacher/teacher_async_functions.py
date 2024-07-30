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
from users.serializers import AccountUpdateSerializer, IDSerializer, ProfileSerializer, StudentProfileSerializer, AccountsSerializer, StudentAccountsSerializer, AccountCreationSerializer, TeachersSerializer, StudentAccountCreationIDSerializer, StudentAccountCreationPNSerializer
from timetables.serializers import SchedulesSerializer
from grades.serializers import GradesSerializer, GradeSerializer, SubjectDetailSerializer, ClassesSerializer
from classes.serializers import ClassSerializer, ClassUpdateSerializer, TeacherClassesSerializer, TeacherRegisterClassSerializer

# utility functions 
    
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
def search_my_register_class(user):

    try:
        teacher = CustomUser.objects.get(account_id=user)
        teacher_register_class = Classroom.objects.get(teacher__account_id=teacher.account_id, school=teacher.school, register_class=True)

        serializer = TeacherRegisterClassSerializer(teacher_register_class)

        return {"register_class": serializer.data}
    
    except CustomUser.DoesNotExist:
        return { 'error': 'account with the provided credentials does not exist' }
               
    except Classroom.DoesNotExist:
        return { 'register_class': None }
    
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
def search_my_classes(user):

    try:
        teacher = CustomUser.objects.get(account_id=user)
        classes = Classroom.objects.filter(teacher=teacher, school=teacher.school, register_class=False)

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

        serializer = StudentAccountsSerializer(students, many=True)

        return {"students": serializer.data}
    
    except CustomUser.DoesNotExist:
        return { 'error': 'account with the provided credentials does not exist' }
           
    except Grade.DoesNotExist:
        return { 'error': 'grade with the provided credentials does not exist' }
    
    except Exception as e:
        return { 'error': str(e) }


@database_sync_to_async
def create_group_schedule(user, group_name, grade_id):

    try:
        account = CustomUser.objects.get(account_id=user)
        grade = Grade.objects.get(grade_id=grade_id, school=account.school)

        with transaction.atomic():
            new_schedule = GroupSchedule.create(group_name=group_name, grade=grade)
            new_schedule.save()

        # Return a success response
        return {'message': f'group schedule for grade {grade.grade} successfully created.. you can now link students and add schedules to it'}
        
    except ValidationError as e:
        # Handle specific known validation errors
        return {'error': str(e)}
        
    except Grade.DoesNotExist:
        return { 'error': 'grade with the provided credentials does not exist' }

    except CustomUser.DoesNotExist:
        return { 'error': 'account with the provided credentials does not exist' }
    
    except Exception as e:
        return { 'error': str(e) }


@database_sync_to_async
def create_teacher_schedule(user, sessions, day, account_id):

    try:
        if day not in [ 'MONDAY', 'TUESDAY', 'WEDNESDAY', 'THURSDAY', 'FRIDAY', 'SATURDAY', 'SUNDAY']:
            return { "error" : 'invalid schedule day' }

        admin = CustomUser.objects.get(account_id=user)
        account = CustomUser.objects.get(account_id=account_id, role='TEACHER')

        if account.school != admin.school:
            return { "error" : 'unauthorized request.. permission denied' }

        with transaction.atomic():
            schedule = Schedule(day=day, day_order=Schedule.DAY_OF_THE_WEEK_ORDER[day])
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
            existing_teacher_schedules = TeacherSchedule.objects.filter(teacher=account, schedules__day=day)

            for schedule in existing_teacher_schedules:
                # Remove the specific schedules for that day
                schedule.schedules.filter(day=day).delete()

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
def search_schedules(user, account_id):

    try:
        admin = CustomUser.objects.get(account_id=user)
        account  = CustomUser.objects.get(account_id=account_id)

        if account.role not in ['TEACHER', 'STUDENT'] or  admin.school != account.school:
            return { "error" : 'unauthorized request.. permission denied' }
        
        if account.role == 'STUDENT':
            group_schedules = GroupSchedule.objects.get(students=account)
            schedules = group_schedules.schedules.all()
            serializer = SchedulesSerializer(schedules, many=True)

            return {"schedules": serializer.data, 'group_name' : group_schedules.group_name}

        if account.role == 'TEACHER':
            teacher_schedule = TeacherSchedule.objects.get(teacher=account)
            schedules = teacher_schedule.schedules.all()
            serializer = SchedulesSerializer(schedules, many=True)

            return {"schedules": serializer.data}
        
    except CustomUser.DoesNotExist:
        return { 'error': 'account with the provided credentials does not exist' }
    
    except TeacherSchedule.DoesNotExist:
        return { 'schedules': [] }
    
    except GroupSchedule.DoesNotExist:
        return {'schedules': [], 'group_name' : 'No Group' }
    
    except Exception as e:
        return { 'error': str(e) }


@database_sync_to_async
def delete_teacher_schedule(user, schedule_id):

    try:
        account = CustomUser.objects.get(account_id=user)
        
        # Retrieve the schedule object
        schedule = Schedule.objects.get(schedule_id=schedule_id)

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
def add_students_to_register_class(user, class_id, students):

    try:
        account = CustomUser.objects.get(account_id=user)
        classroom = Classroom.objects.get(class_id=class_id, school=account.school, register_class=True)

        if students == '':
            return { 'error': f'invalid request.. no students were provided. please provide students to be added to the specified class' }
        
        students_list = students.split(', ')
        
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
def remove_student_from_register_class(user, class_id, account_id):

    try:
        account = CustomUser.objects.get(account_id=user)
        classroom = Classroom.objects.get(class_id=class_id, school=account.school, register_class=True)

        if classroom.students.filter(account_id=account_id).exists():
            with transaction.atomic():
                classroom.students.remove(classroom.students.get(account_id=account_id))
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
    

@database_sync_to_async
def form_add_students_to_register_class(user, class_id):

    try:
        account = CustomUser.objects.get(account_id=user)
        classroom = Classroom.objects.get(class_id=class_id, school=account.school)

        # Get all students who are in the same grade and already in a register class
        students_in_register_classes = CustomUser.objects.filter(enrolled_classes__grade=classroom.grade, enrolled_classes__register_class=True)

        # Exclude these students from the current classroom's grade
        students = classroom.grade.students.exclude(id__in=students_in_register_classes)

        serializer = StudentAccountsSerializer(students, many=True)

        return {"students": serializer.data}
    
    except CustomUser.DoesNotExist:
        return { 'error': 'account with the provided credentials does not exist' }
            
    except Classroom.DoesNotExist:
        return { 'error': 'class with the provided credentials does not exist' }

    except Exception as e:
        return { 'error': str(e) }

    