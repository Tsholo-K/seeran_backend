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
from users.models import Principal, Admin, Teacher, Student, Parent
from grades.models import Grade
from terms.models import Term
from subjects.models import Subject
from classes.models import Classroom
from announcements.models import Announcement
from daily_schedule_sessions.models import DailyScheduleSession
from student_group_timetables.models import StudentGroupTimetable
from teacher_timetables.models import TeacherTimetable
from daily_schedules.models import DailySchedule

# serilializers
from users.serializers.parents.parents_serializers import ParentAccountCreationSerializer
from grades.serializers import GradeCreationSerializer
from terms.serializers import  TermCreationSerializer
from subjects.serializers import  SubjectCreationSerializer
from classes.serializers import ClassCreationSerializer
from student_group_timetables.serializers import StudentGroupScheduleCreationSerializer
from announcements.serializers import AnnouncementCreationSerializer

# checks
from users.checks import permission_checks

# mappings
from users.maps import role_specific_maps

# queries
from users.complex_queries import queries

# utlity functions
from permissions.utils import has_permission
from audit_logs.utils import log_audit


@database_sync_to_async
def create_grade(user, role, details):
    try:
        # Get the appropriate model for the requesting user's role
        Model = role_specific_maps.account_access_control_mapping[role]

        # Retrieve the user and related school in a single query using select_related
        requesting_account = Model.objects.select_related('school').only('school').get(account_id=user)

        # Check if the user has permission to create a grade
        if role != 'PRINCIPAL' and not has_permission(requesting_account, 'CREATE', 'GRADE'):
            response = f'could not proccess your request, you do not have the necessary permissions to create a grade'

            log_audit(
                actor=requesting_account,
                action='CREATE',
                target_model='GRADE',
                outcome='DENIED',
                response=response,
                school=requesting_account.school
            )

            return {'error': response}

        # Set the school field in the details to the user's school ID
        details['school'] = requesting_account.school.pk

        # Serialize the details for grade creation
        serializer = GradeCreationSerializer(data=details)
        if serializer.is_valid():
            # Create the grade within a transaction to ensure atomicity
            with transaction.atomic():
                grade = Grade.objects.create(**serializer.validated_data)
                response = f'grade {grade.grade} has been successfully created for your school. you can now add students, subjects, classes and start tracking attendance and performnace'

                log_audit(
                    actor=requesting_account,
                    action='CREATE',
                    target_model='GRADE',
                    target_object_id=str(grade.grade_id),
                    outcome='CREATED',
                    response=response,
                    school=requesting_account.school,
                )

            return {"message": response}
        
        error_response = '; '.join([f"{key}: {', '.join(value)}" for key, value in serializer.errors.items()])

        log_audit(
            actor=requesting_account,
            action='CREATE',
            target_model='GRADE',
            outcome='ERROR',
            response=f'Validation failed: {error_response}',
            school=requesting_account.school
        )

        return {"error": error_response}
               
    except Principal.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'a principal account with the provided credentials does not exist, please check your account details and try again'}
                   
    except Admin.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'an admin account with the provided credentials does not exist, please check your account details and try again'}

    except ValidationError as e:
        error_message = e.messages[0].lower() if isinstance(e.messages, list) and e.messages else str(e).lower()
        log_audit(
            actor=requesting_account,
            action='CREATE',
            target_model='GRADE',
            target_object_id=str(grade.grade_id) if grade else 'N/A',
            outcome='ERROR',
            response=error_message,
            school=requesting_account.school
        )
        return {"error": error_message}

    except Exception as e:
        error_message = str(e)
        log_audit(
            actor=requesting_account,
            action='CREATE',
            target_model='GRADE',
            target_object_id=str(grade.grade_id) if grade else 'N/A',
            outcome='ERROR',
            response=error_message,
            school=requesting_account.school
        )
        return {'error': error_message}


@database_sync_to_async
def delete_grade(user, role, details):
    try:
        # Get the appropriate model for the requesting user's role
        Model = role_specific_maps.account_access_control_mapping[role]

        # Retrieve the user and related school in a single query using select_related
        requesting_account = Model.objects.select_related('school').only('school').get(account_id=user)

        grade = Grade.objects.get(grade_id=details.get('grade'), school=requesting_account.school)

        # Check if the user has permission to create a grade
        if role != 'PRINCIPAL' and not has_permission(requesting_account, 'DELETE', 'GRADE'):
            response = f'could not proccess your request, you do not have the necessary permissions to delete a grade'

            log_audit(
                actor=requesting_account,
                action='DELETE',
                target_model='GRADE',
                target_object_id=grade.grade_id,
                outcome='DENIED',
                response=response,
                school=requesting_account.school
            )

            return {'error': response}

        # Create the grade within a transaction to ensure atomicity
        with transaction.atomic():
            response = f"your schools grade {grade.grade} has been successfully deleted. the grade and all it's associated data will no longer be assessible on the system"

            log_audit(
                actor=requesting_account,
                action='DELETE',
                target_model='GRADE',
                target_object_id=str(grade.grade_id),
                outcome='CREATED',
                response=response,
                school=requesting_account.school,
            )

            grade.delete()
            
        return {'message' : response}
               
    except Principal.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'a principal account with the provided credentials does not exist, please check your account details and try again'}
                   
    except Admin.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'an admin account with the provided credentials does not exist, please check your account details and try again'}
        
    except Grade.DoesNotExist:
        # Handle the case where the provided grade ID does not exist
        return {'error': 'a grade in your school with the provided credentials does not exist. please check the grade details and try again.'}

    except ValidationError as e:
        error_message = e.messages[0].lower() if isinstance(e.messages, list) and e.messages else str(e).lower()

        log_audit(
            actor=requesting_account,
            action='DELETE',
            target_model='GRADE',
            target_object_id=str(grade.grade_id) if grade else 'N/A',
            outcome='ERROR',
            response=error_message,
            school=requesting_account.school
        )

        return {"error": error_message}

    except Exception as e:
        error_message = str(e)

        log_audit(
            actor=requesting_account,
            action='DELETE',
            target_model='GRADE',
            target_object_id=str(grade.grade_id) if grade else 'N/A',
            outcome='ERROR',
            response=error_message,
            school=requesting_account.school
        )

        return {'error': error_message}
    

@database_sync_to_async
def create_term(user, role, details):
    try:
        # Get the appropriate model for the requesting user's role
        Model = role_specific_maps.account_access_control_mapping[role]

        # Retrieve the user and related school in a single query using select_related
        requesting_account = Model.objects.select_related('school').only('school').get(account_id=user)

        # Check if the user has permission to create a grade
        if role != 'PRINCIPAL' and not has_permission(requesting_account, 'CREATE', 'TERM'):
            response = f'could not proccess your request, you do not have the necessary permissions to create a term'

            log_audit(
                actor=requesting_account,
                action='CREATE',
                target_model='TERM',
                outcome='DENIED',
                response=response,
                school=requesting_account.school
            )
            
            return {'error': response}

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
                term = Term.objects.create(**serializer.validated_data)
                response = f"term {term.term} for grade {grade.grade} has been successfully created for your schools"

                log_audit(
                    actor=requesting_account,
                    action='CREATE',
                    target_model='TERM',
                    target_object_id=str(term.term_id),
                    outcome='CREATED',
                    response=response,
                    school=requesting_account.school,
                )

            return {'message': response}
        
        error_response = '; '.join([f"{key}: {', '.join(value)}" for key, value in serializer.errors.items()])

        log_audit(
            actor=requesting_account,
            action='CREATE',
            target_model='TERM',
            outcome='ERROR',
            response=f'Validation failed: {error_response}',
            school=requesting_account.school
        )

        return {"error": error_response}
               
    except Principal.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'a principal account with the provided credentials does not exist, please check your account details and try again'}
                   
    except Admin.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'an admin account with the provided credentials does not exist, please check your account details and try again'}
        
    except Grade.DoesNotExist:
        # Handle the case where the provided grade ID does not exist
        return {'error': 'a grade in your school with the provided credentials does not exist. please check the grade details and try again.'}
    
    except ValidationError as e:
        error_message = e.messages[0].lower() if isinstance(e.messages, list) and e.messages else str(e).lower()

        log_audit(
            actor=requesting_account,
            action='CREATE',
            target_model='TERM',
            target_object_id=str(term.term_id) if term else 'N/A',
            outcome='ERROR',
            response=error_message,
            school=requesting_account.school
        )

        return {"error": error_message}

    except Exception as e:
        error_message = str(e)

        log_audit(
            actor=requesting_account,
            action='CREATE',
            target_model='TERM',
            target_object_id=str(term.term_id) if term else 'N/A',
            outcome='ERROR',
            response=error_message,
            school=requesting_account.school
        )

        return {'error': error_message}
    

@database_sync_to_async
def create_subject(user, role, details):
    try:
        # Get the appropriate model for the requesting user's role
        Model = role_specific_maps.account_access_control_mapping[role]

        # Retrieve the user and related school in a single query using select_related
        requesting_account = Model.objects.select_related('school').only('school').get(account_id=user)

        # Check if the user has permission to create a grade
        if role != 'PRINCIPAL' and not has_permission(requesting_account, 'CREATE', 'SUBJECT'):
            response = f'could not proccess your request, you do not have the necessary permissions to create a subject'

            log_audit(
                actor=requesting_account,
                action='CREATE',
                target_model='SUBJECT',
                outcome='DENIED',
                response=response,
                school=requesting_account.school
            )
            
            return {'error': response}

        grade = Grade.objects.get(grade_id=details.get('grade'), school=requesting_account.school)

        details['grade'] = grade.pk

        # Serialize the details for grade creation
        serializer = SubjectCreationSerializer(data=details)
        # Validate the serialized data
        if serializer.is_valid():
            # Create the grade within a transaction to ensure atomicity
            with transaction.atomic():
                subject = Subject.objects.create(**serializer.validated_data)
                response = f"{subject.subject} subject has been successfully created for your schools grade {grade.grade}".lower()

                log_audit(
                    actor=requesting_account,
                    action='CREATE',
                    target_model='SUBJECT',
                    target_object_id=str(subject.subject_id),
                    outcome='CREATED',
                    response=response,
                    school=requesting_account.school,
                )

            return {"message": response}
        
        error_response = '; '.join([f"{key}: {', '.join(value)}" for key, value in serializer.errors.items()])

        log_audit(
            actor=requesting_account,
            action='CREATE',
            target_model='SUBJECT',
            outcome='ERROR',
            response=f'Validation failed: {error_response}',
            school=requesting_account.school
        )

        return {"error": error_response}
               
    except Principal.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'a principal account with the provided credentials does not exist, please check your account details and try again'}
                   
    except Admin.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'an admin account with the provided credentials does not exist, please check your account details and try again'}
        
    except Grade.DoesNotExist:
        # Handle the case where the provided grade ID does not exist
        return {'error': 'a grade in your school with the provided credentials does not exist. please check the grade details and try again.'}
    
    except ValidationError as e:
        error_message = e.messages[0].lower() if isinstance(e.messages, list) and e.messages else str(e).lower()

        log_audit(
            actor=requesting_account,
            action='CREATE',
            target_model='SUBJECT',
            target_object_id=str(subject.subject_id) if subject else 'N/A',
            outcome='ERROR',
            response=error_message,
            school=requesting_account.school
        )

        return {"error": error_message}

    except Exception as e:
        error_message = str(e)

        log_audit(
            actor=requesting_account,
            action='CREATE',
            target_model='SUBJECT',
            target_object_id=str(subject.subject_id) if subject else 'N/A',
            outcome='ERROR',
            response=error_message,
            school=requesting_account.school
        )

        return {'error': error_message}
    

@database_sync_to_async
def create_class(user, role, details):
    try:
        # Get the appropriate model for the requesting user's role
        Model = role_specific_maps.account_access_control_mapping[role]

        # Retrieve the user and related school in a single query using select_related
        requesting_account = Model.objects.select_related('school').only('school').get(account_id=user)

        classroom = None

        # Check if the user has permission to create a grade
        if role != 'PRINCIPAL' and not has_permission(requesting_account, 'CREATE', 'CLASSROOM'):
            response = f'could not proccess your request, you do not have the necessary permissions to create a classroom'

            log_audit(
                actor=requesting_account,
                action='CREATE',
                target_model='CLASSROOM',
                outcome='DENIED',
                response=response,
                school=requesting_account.school
            )
            
            return {'error': response}

        # Retrieve the grade and validate school ownership
        grade = Grade.objects.select_related('school').get(grade_id=details.get('grade'), school=requesting_account.school)

        if details.get('register_class'):
            details['subject'] = None

            response = {'message': f'register classroom for grade {grade.grade} has been created successfully. you can now add students and track attendance.'}
        
        elif details.get('subject'):
            # Retrieve the subject and validate it against the grade
            subject = Subject.objects.get(subject_id=details.get('subject'), grade=grade)
            
            details['subject'] = subject.pk
            details['register_class'] = False

            response = {'message': f'classroom for grade {grade.grade} {subject.subject} has been created successfully.. you can now add students and track performance.'.lower()}
        
        else:
            response = "could not proccess your request, invalid classroom creation details. please provide all required information and try again."

            log_audit(
                actor=requesting_account,
                action='CREATE',
                target_model='CLASSROOM',
                outcome='ERROR',
                response=response,
                school=requesting_account.school
            )
            
            return {'error': response}

        # Set the school and grade fields
        details.update({'school': requesting_account.school.pk, 'grade': grade.pk})

        # If a teacher is specified, update the teacher for the class
        if details.get('teacher'):
             teacker = Teacher.objects.only('pk').get(account_id=details['teacher'], school=requesting_account.school)
             details['teacher'] = teacker.pk

        # Serialize and validate the data
        serializer = ClassCreationSerializer(data=details)
        if serializer.is_valid():
            # Create the class within a transaction
            with transaction.atomic():
                classroom = Classroom.objects.create(**serializer.validated_data)

                log_audit(
                    actor=requesting_account,
                    action='CREATE',
                    target_model='CLASSROOM',
                    target_object_id=str(classroom.classroom_id),
                    outcome='CREATED',
                    response=response,
                    school=requesting_account.school,
                )

            return response
        
        error_response = '; '.join([f"{key}: {', '.join(value)}" for key, value in serializer.errors.items()])

        log_audit(
            actor=requesting_account,
            action='CREATE',
            target_model='CLASSROOM',
            outcome='ERROR',
            response=f'Validation failed: {error_response}',
            school=requesting_account.school
        )

        return {"error": error_response}
               
    except Principal.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'a principal account with the provided credentials does not exist, please check your account details and try again'}
                   
    except Admin.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'an admin account with the provided credentials does not exist, please check your account details and try again'}
               
    except Teacher.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'a teacher account with the provided credentials does not exist, please check the account details and try again'}
        
    except Grade.DoesNotExist:
        # Handle the case where the provided grade ID does not exist
        return {'error': 'a grade in your school with the provided credentials does not exist. please check the grade details and try again.'}
    
    except Subject.DoesNotExist:
        return {'error': 'a subject in your school with the provided credentials does not exist. please check the subject details and try again.'}
    
    except ValidationError as e:
        error_message = e.messages[0].lower() if isinstance(e.messages, list) and e.messages else str(e).lower()

        log_audit(
            actor=requesting_account,
            action='CREATE',
            target_model='CLASSROOM',
            target_object_id=str(classroom.classroom_id) if classroom else 'N/A',
            outcome='ERROR',
            response=error_message,
            school=requesting_account.school
        )

        return {"error": error_message}

    except Exception as e:
        error_message = str(e)

        log_audit(
            actor=requesting_account,
            action='CREATE',
            target_model='CLASSROOM',
            target_object_id=str(classroom.classroom_id) if classroom else 'N/A',
            outcome='ERROR',
            response=error_message,
            school=requesting_account.school
        )

        return {'error': error_message}
    

@database_sync_to_async
def delete_class(user, role, details):
    try:
        # Get the appropriate model for the requesting user's role
        Model = role_specific_maps.account_access_control_mapping[role]

        # Retrieve the user and related school in a single query using select_related
        requesting_account = Model.objects.select_related('school').only('school').get(account_id=user)

        # Check if the user has permission to create a grade
        if role != 'PRINCIPAL' and not has_permission(requesting_account, 'DELETE', 'CLASSROOM'):
            response = f'could not proccess your request, you do not have the necessary permissions to delete a classroom'

            log_audit(
                actor=requesting_account,
                action='DELETE',
                target_model='CLASSROOM',
                outcome='DENIED',
                response=response,
                school=requesting_account.school
            )
            
            return {'error': response}

        # Retrieve the grade
        classroom = Classroom.objects.select_related('grade').only('grade__grade').get(class_id=details.get('class'), school=requesting_account.school)

        response = f'grade {classroom.grade.grade} classroom deleted successfully, the classroom will no longer be accessible or available in your schools data'
        
        with transaction.atomic():
            classroom.delete()

            log_audit(
                actor=requesting_account,
                action='DELETE',
                target_model='CLASSROOM',
                target_object_id=str(classroom.classroom_id),
                outcome='DELETED',
                response=response,
                school=requesting_account.school,
            )

        return {'message': response}
               
    except Principal.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'a principal account with the provided credentials does not exist, please check your account details and try again'}
                   
    except Admin.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'an admin account with the provided credentials does not exist, please check your account details and try again'}

    except Classroom.DoesNotExist:
        # Handle case where the grade does not exist
        return {'error': 'classroom with the provided credentials does not exist'}
    
    except ValidationError as e:
        error_message = e.messages[0].lower() if isinstance(e.messages, list) and e.messages else str(e).lower()

        log_audit(
            actor=requesting_account,
            action='DELETE',
            target_model='CLASSROOM',
            target_object_id=str(classroom.classroom_id) if classroom else 'N/A',
            outcome='ERROR',
            response=error_message,
            school=requesting_account.school
        )

        return {"error": error_message}

    except Exception as e:
        error_message = str(e)

        log_audit(
            actor=requesting_account,
            action='DELETE',
            target_model='CLASSROOM',
            target_object_id=str(classroom.classroom_id) if classroom else 'N/A',
            outcome='ERROR',
            response=error_message,
            school=requesting_account.school
        )

        return {'error': error_message}


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

        # Check if the user has permission to create a grade
        if role != 'PRINCIPAL' and not has_permission(requesting_account, 'CREATE', 'ACCOUNT'):
            response = f'could not proccess your request, you do not have the necessary permissions to delete a classroom'

            log_audit(
                actor=requesting_account,
                action='CREATE',
                target_model='ACCOUNT',
                outcome='DENIED',
                response=response,
                school=requesting_account.school
            )
            
            return {'error': response}

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
                created_account = Model.objects.create(**serializer.validated_data)
                response = f"{details['role']} account successfully created. the {details['role']} can now sign-in and activate the account".lower()

                log_audit(
                    actor=requesting_account,
                    action='CREATE',
                    target_model='ACCOUNT',
                    target_object_id=str(created_account.account_id),
                    outcome='CREATED',
                    response=response,
                    school=requesting_account.school,
                )

            if details['role'] == 'STUDENT' and not details.get('email'):
                return {'message' : 'the students account has been successfully created, accounts with no email addresses can not '}
            
            return {'user' : created_account}
            
        error_response = '; '.join([f"{key}: {', '.join(value)}" for key, value in serializer.errors.items()])

        log_audit(
            actor=requesting_account,
            action='CREATE',
            target_model='ACCOUNT',
            outcome='ERROR',
            response=f'Validation failed: {error_response}',
            school=requesting_account.school
        )

        return {"error": error_response}
               
    except Principal.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'a principal account with the provided credentials does not exist, please check your account details and try again'}
                   
    except Admin.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'an admin account with the provided credentials does not exist, please check your account details and try again'}
        
    except Grade.DoesNotExist:
        # Handle the case where the provided grade ID does not exist
        return {'error': 'a grade in your school with the provided credentials does not exist. please check the grade details and try again.'}
    
    except ValidationError as e:
        error_message = e.messages[0].lower() if isinstance(e.messages, list) and e.messages else str(e).lower()

        log_audit(
            actor=requesting_account,
            action='CREATE',
            target_model='ACCOUNT',
            target_object_id=str(created_account.account_id) if created_account else 'N/A',
            outcome='ERROR',
            response=error_message,
            school=requesting_account.school
        )

        return {"error": error_message}

    except Exception as e:
        error_message = str(e)

        log_audit(
            actor=requesting_account,
            action='CREATE',
            target_model='ACCOUNT',
            target_object_id=str(created_account.account_id) if created_account else 'N/A',
            outcome='ERROR',
            response=error_message,
            school=requesting_account.school
        )

        return {'error': error_message}


@database_sync_to_async
def link_parent(user, role, details):
    try:    
        # Get the appropriate model and related fields (select_related and prefetch_related)
        # for the requesting user's role from the mapping.
        Model = role_specific_maps.account_access_control_mapping[role]

        # Retrieve the user and related school in a single query using select_related
        requesting_account = Model.objects.select_related('school').only('school').get(account_id=user)

        # Check if the user has permission to create a grade
        if role != 'PRINCIPAL' and not has_permission(requesting_account, 'LINK', 'ACCOUNT'):
            response = f'could not proccess your request, you do not have the necessary permissions to link parents to student accounts'

            log_audit(
                actor=requesting_account,
                action='LINK',
                target_model='ACCOUNT',
                outcome='DENIED',
                response=response,
                school=requesting_account.school
            )
            
            return {'error': response}

        student = Student.objects.prefetch_related('parents').get(account_id=details.get('student'), school=requesting_account.school)

        # Check if the child already has two or more parents linked
        student_parent_count = student.parents.count()
        if student_parent_count >= 2:
            response = f"the provided student account has reached the maximum number of linked parents. please unlink one of the existing parents to link a new one"

            log_audit(
                actor=requesting_account,
                action='LINK',
                target_model='ACCOUNT',
                target_object_id=str(student.account_id),
                outcome='DENIED',
                response=response,
                school=requesting_account.school
            )

            return {"error": response}
        
        # Check if an account with the provided email already exists
        existing_parent = Parent.objects.filter(email=details.get('email')).first()
        if existing_parent:
            with transaction.atomic():
                existing_parent.children.add(student)

                log_audit(
                    actor=requesting_account,
                    action='LINK',
                    target_model='ACCOUNT',
                    target_object_id=str(student.account_id),
                    outcome='LINKED',
                    response='parent account successfully linked to student. the parent can now sign-in and activate their account',
                    school=requesting_account.school,
                )

            return {'user' : existing_parent}

        details['role'] = 'PARENT'
        
        serializer = ParentAccountCreationSerializer(data=details)
        if serializer.is_valid():
            with transaction.atomic():
                parent = Parent.objects.create(**serializer.validated_data)
                parent.children.add(student)

                log_audit(
                    actor=requesting_account,
                    action='LINK',
                    target_model='ACCOUNT',
                    target_object_id=str(parent.account_id),
                    outcome='LINKED',
                    response='parent account successfully created and linked to student. the parent can now sign-in and activate their account',
                    school=requesting_account.school,
                )

            return {'user' : parent}
            
        error_response = '; '.join([f"{key}: {', '.join(value)}" for key, value in serializer.errors.items()])

        log_audit(
            actor=requesting_account,
            action='LINK',
            target_model='ACCOUNT',
            outcome='ERROR',
            response=f'Validation failed: {error_response}',
            school=requesting_account.school
        )

        return {"error": error_response}
               
    except Principal.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'a principal account with the provided credentials does not exist, please check your account details and try again'}
                   
    except Admin.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'an admin account with the provided credentials does not exist, please check your account details and try again'}
                                      
    except Student.DoesNotExist:
        # Handle the case where the requested student account does not exist.
        return {'error': 'A student account with the provided credentials does not exist, please check the account details and try again'}

    except Parent.DoesNotExist:
        # Handle the case where the requested parent account does not exist.
        return {'error': 'A parent account with the provided credentials does not exist, please check the account details and try again'}
    
    except ValidationError as e:
        error_message = e.messages[0].lower() if isinstance(e.messages, list) and e.messages else str(e).lower()

        log_audit(
            actor=requesting_account,
            action='LINK',
            target_model='ACCOUNT',
            target_object_id=str(student.account_id) if student else 'N/A',
            outcome='ERROR',
            response=error_message,
            school=requesting_account.school
        )

        return {"error": error_message}

    except Exception as e:
        error_message = str(e)

        log_audit(
            actor=requesting_account,
            action='LINK',
            target_model='ACCOUNT',
            target_object_id=str(student.account_id) if student else 'N/A',
            outcome='ERROR',
            response=error_message,
            school=requesting_account.school
        )

        return {'error': error_message}
        
    
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

        # Check if the user has permission to create a grade
        if role != 'PRINCIPAL' and not has_permission(requesting_account, 'DELETE', 'ACCOUNT'):
            response = f'could not proccess your request, you do not have the necessary permissions to delete accounts'

            log_audit(
                actor=requesting_account,
                action='DELETE',
                target_model='ACCOUNT',
                outcome='DENIED',
                response=response,
                school=requesting_account.school
            )
            
            return {'error': response}

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

                log_audit(
                    actor=requesting_account,
                    action='DELETE',
                    target_model='ACCOUNT',
                    target_object_id=str(requested_account.account_id),
                    outcome='CREATED',
                    response='parent account successfully created and linked to student. the parent can now sign-in and activate the account',
                    school=requesting_account.school,
                )
                
                requested_account.delete()

            return {"message" : 'account successfully deleted'}

        response = 'could not proccess your request, the provided account role is invalid'

        log_audit(
            actor=requesting_account,
            action='DELETE',
            target_model='ACCOUNT',
            target_object_id=str(requested_account.account_id),
            outcome='CREATED',
            response=response,
            school=requesting_account.school,
        )

        return {"error": response}
               
    except Principal.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'a principal account with the provided credentials does not exist, please check your account details and try again'}
                   
    except Admin.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'an admin account with the provided credentials does not exist, please check your account details and try again'}

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
        error_message = e.messages[0].lower() if isinstance(e.messages, list) and e.messages else str(e).lower()

        log_audit(
            actor=requesting_account,
            action='DELETE',
            target_model='ACCOUNT',
            target_object_id=str(requested_account.account_id) if requested_account else 'N/A',
            outcome='ERROR',
            response=error_message,
            school=requesting_account.school
        )

        return {"error": error_message}

    except Exception as e:
        error_message = str(e)

        log_audit(
            actor=requesting_account,
            action='DELETE',
            target_model='ACCOUNT',
            target_object_id=str(requested_account.account_id) if requested_account else 'N/A',
            outcome='ERROR',
            response=error_message,
            school=requesting_account.school
        )

        return {'error': error_message}


@database_sync_to_async
def unlink_parent(user, role, details):
    try:
        # Get the appropriate model for the requesting user's role
        Model = role_specific_maps.account_access_control_mapping[role]

        # Retrieve the user and related school in a single query using select_related
        requesting_account = Model.objects.select_related('school').only('school').get(account_id=user)

        # Check if the user has permission to create a grade
        if role != 'PRINCIPAL' and not has_permission(requesting_account, 'UNLINK', 'ACCOUNT'):
            response = f'could not proccess your request, you do not have the necessary permissions to unlink parents from student accounts'

            log_audit(
                actor=requesting_account,
                action='UNLINK',
                target_model='ACCOUNT',
                outcome='DENIED',
                response=response,
                school=requesting_account.school
            )
            
            return {'error': response}

        # Fetch the student account using the provided child ID
        student = Student.objects.prefetch_related('parents').get(account_id=details.get('student'), school=requesting_account.school)

        # Fetch the parent account using the provided parent ID
        parent = student.parents.filter(account_id=details.get('parent')).first()

        if not parent:
            response = "could not process your request, the specified student account is not a child of the provided parent account. please ensure the provided information is complete and true"

            log_audit(
                actor=requesting_account,
                action='UNLINK',
                target_model='ACCOUNT',
                target_object_id=str(student.account_id),
                outcome='DENIED',
                response=response,
                school=requesting_account.school
            )
            
            return {"error": response}

        # Remove the child from the parent's list of children
        with transaction.atomic():
            parent.children.remove(student)
            if parent.children.len <= 0:
                parent.is_active = False
                parent.save()

            response = "the parent account has been successfully unlinked from the student. the account will no longer be associated with the student or have access to the student's data"

            log_audit(
                actor=requesting_account,
                action='UNLINK',
                target_model='ACCOUNT',
                target_object_id=str(student.account_id),
                outcome='UNLINKED',
                response=response,
                school=requesting_account.school,
            )

        return {"message": response}
               
    except Principal.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'a principal account with the provided credentials does not exist, please check your account details and try again'}
                   
    except Admin.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'an admin account with the provided credentials does not exist, please check your account details and try again'}
                   
    except Student.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'a student account in your school with the provided credentials does not exist, please check the account details and try again'}
                   
    except Parent.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'a parent account with the provided credentials does not exist, please check the account details and try again'}
    
    except ValidationError as e:
        error_message = e.messages[0].lower() if isinstance(e.messages, list) and e.messages else str(e).lower()

        log_audit(
            actor=requesting_account,
            action='UNLINK',
            target_model='ACCOUNT',
            target_object_id=str(student.account_id) if student else 'N/A',
            outcome='ERROR',
            response=error_message,
            school=requesting_account.school
        )

        return {"error": error_message}

    except Exception as e:
        error_message = str(e)

        log_audit(
            actor=requesting_account,
            action='UNLINK',
            target_model='ACCOUNT',
            target_object_id=str(student.account_id) if student else 'N/A',
            outcome='ERROR',
            response=error_message,
            school=requesting_account.school
        )

        return {'error': error_message}


@database_sync_to_async
def create_daily_schedule(user, role, details):
    try:
        # Get the appropriate model and related fields (select_related and prefetch_related)
        # for the requesting user's role from the mapping.
        Model = role_specific_maps.account_access_control_mapping[role]

        # Retrieve the user and related school in a single query using select_related
        requesting_account = Model.objects.select_related('school').only('school').get(account_id=user)

        # Check if the user has permission to create a schedule
        if role != 'PRINCIPAL' and not has_permission(requesting_account, 'CREATE', 'DAILY_SCHEDULE'):
            response = 'Could not process your request, you do not have the necessary permissions to create schedules.'

            log_audit(
                actor=requesting_account,
                action='CREATE',
                target_model='DAILY_SCHEDULE',
                outcome='DENIED',
                response=response,
                school=requesting_account.school
            )
            
            return {'error': response}

        if details.get('group_timetable'):
            group_timetable = StudentGroupTimetable.objects.get(group_timetable_id=details['group_timetable'], grade__school=requesting_account.school)
        
        elif details.get('teacher'):
            teacher = Teacher.objects.get(account_id=details['teacher'], school=requesting_account.school)

        else:
            response = 'Could not process your request, invalid information provided.'

            log_audit(
                actor=requesting_account,
                action='CREATE',
                target_model='DAILY_SCHEDULE',
                outcome='DENIED',
                response=response,
                school=requesting_account.school
            )

            return {"error": response}

        # Validate the day
        day = details.get('day_of_week', '').upper()
        if day not in DailySchedule.DAY_OF_THE_WEEK_ORDER:
            return {"error": 'the provided day for the schedule is invalid. Please check that the day is valid.'}

        with transaction.atomic():
            # Create a new daily schedule
            daily_schedule = DailySchedule.objects.create(day_of_week=day, day_of_week_order=DailySchedule.DAY_OF_THE_WEEK_ORDER[day])

            sessions = [
                DailyScheduleSession(
                    session_type=session_info['class'],
                    classroom=session_info.get('classroom'),
                    start_time=parse_time(f"{session_info['start_time']['hour']}:{session_info['start_time']['minute']}:{session_info['start_time']['second']}"),
                    end_time=parse_time(f"{session_info['end_time']['hour']}:{session_info['end_time']['minute']}:{session_info['end_time']['second']}")
                ) for session_info in details.get('sessions', [])
            ]

            DailyScheduleSession.objects.bulk_create(sessions)
            daily_schedule.sessions.add(*sessions)
            
            if details.get('group'):
                group_timetable.daily_schedules.filter(day_of_week=day).delete()
                group_timetable.daily_schedules.add(daily_schedule)
                
                response = {'message': 'A new schedule has been added to the group\'s weekly schedules. All subscribed students should be able to view the sessions in the schedule when they check their timetables.'}

            elif details.get('teacher'):
                teacher_timetable, created = TeacherTimetable.objects.get_or_create(teacher=teacher)
                if not created:
                    teacher_timetable.daily_schedules.filter(day_of_week=day).delete()
                teacher_timetable.daily_schedules.add(daily_schedule)

                response = {'message': 'A new schedule has been added to the teacher\'s weekly schedules. They should be able to view the sessions in the schedule when they check their timetable.'}
                    
            log_audit(
                actor=requesting_account,
                action='CREATE',
                target_model='DAILY_SCHEDULE',
                target_object_id=str(daily_schedule.daily_schedule_id),
                outcome='CREATED',
                response=response,
                school=requesting_account.school,
            )

        return response
               
    except Principal.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'a principal account with the provided credentials does not exist, please check your account details and try again'}
                   
    except Admin.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'an admin account with the provided credentials does not exist, please check your account details and try again'}

    except Teacher.DoesNotExist:
        # Handle the case where the requested teacher account does not exist.
        return {'error': 'a teacher account with the provided credentials does not exist, please check the account details and try again'}

    except StudentGroupTimetable.DoesNotExist:
        # Handle the case where the requested student account does not exist.
        return {'error': 'a group timetable in your school with the provided credentials does not exist. please check the group details and try again.'}
    
    except ValidationError as e:
        error_message = e.messages[0].lower() if isinstance(e.messages, list) and e.messages else str(e).lower()

        log_audit(
            actor=requesting_account,
            action='CREATE',
            target_model='DAILY_SCHEDULE',
            target_object_id=str(daily_schedule.daily_schedule_id) if daily_schedule else 'N/A',
            outcome='ERROR',
            response=error_message,
            school=requesting_account.school
        )

        return {"error": error_message}

    except Exception as e:
        error_message = str(e)

        log_audit(
            actor=requesting_account,
            action='CREATE',
            target_model='DAILY_SCHEDULE',
            target_object_id=str(daily_schedule.daily_schedule_id) if daily_schedule else 'N/A',
            outcome='ERROR',
            response=error_message,
            school=requesting_account.school
        )

        return {'error': error_message}


@database_sync_to_async
def create_group_timetable(user, role, details):
    try:
        # Get the appropriate model for the requesting user's role
        Model = role_specific_maps.account_access_control_mapping[role]

        # Retrieve the user and related school in a single query using select_related
        requesting_account = Model.objects.select_related('school').only('school').get(account_id=user)

        # Check if the user has permission to create a group schedule
        if role != 'PRINCIPAL' and not has_permission(requesting_account, 'CREATE', 'GROUP_TIMETABLE'):
            response = 'Could not process your request, you do not have the necessary permissions to create group timetables.'

            log_audit(
                actor=requesting_account,
                action='CREATE',
                target_model='GROUP_TIMETABLE',
                outcome='DENIED',
                response=response,
                school=requesting_account.school
            )
            
            return {'error': response}

        grade = Grade.objects.get(grade_id=details.get('grade'), school=requesting_account.school)
        details['grade'] = grade.pk

        serializer = StudentGroupScheduleCreationSerializer(data=details)
        if serializer.is_valid():
            with transaction.atomic():
                group_timetable = StudentGroupTimetable.objects.create(**serializer.validated_data)
                response = 'You can now add individual daily schedules and subscribe students in the grade to the group timetable for a shared weekly schedule.'
            
                log_audit(
                    actor=requesting_account,
                    action='CREATE',
                    target_model='GROUP_TIMETABLE',
                    target_object_id=str(group_timetable.group_timetable_id),
                    outcome='CREATED',
                    response=response,
                    school=requesting_account.school,
                )

            return {'message': response}

        error_response = '; '.join([f"{key}: {', '.join(value)}" for key, value in serializer.errors.items()])

        log_audit(
            actor=requesting_account,
            action='CREATE',
            target_model='GROUP_TIMETABLE',
            outcome='ERROR',
            response=f'Validation failed: {error_response}',
            school=requesting_account.school
        )

        return {"error": error_response}
               
    except Principal.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'a principal account with the provided credentials does not exist, please check your account details and try again'}
                   
    except Admin.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'an admin account with the provided credentials does not exist, please check your account details and try again'}

    except Grade.DoesNotExist:
        # Handle the case where the requested grade does not exist.
        return {'error': 'A grade in your school with the provided credentials does not exist. Please check the grade details and try again.'}
    
    except ValidationError as e:
        error_message = e.messages[0].lower() if isinstance(e.messages, list) and e.messages else str(e).lower()

        log_audit(
            actor=requesting_account,
            action='CREATE',
            target_model='GROUP_TIMETABLE',
            target_object_id=str(group_timetable.group_timetable_id) if group_timetable else 'N/A',
            outcome='ERROR',
            response=error_message,
            school=requesting_account.school
        )

        return {"error": error_message}

    except Exception as e:
        error_message = str(e)

        log_audit(
            actor=requesting_account,
            action='CREATE',
            target_model='GROUP_TIMETABLE',
            target_object_id=str(group_timetable.group_timetable_id) if group_timetable else 'N/A',
            outcome='ERROR',
            response=error_message,
            school=requesting_account.school
        )

        return {'error': error_message}
    

@database_sync_to_async
def delete_daily_schedule(user, role, details):
    try:
        # Get the appropriate model and related fields (select_related and prefetch_related)
        # for the requesting user's role from the mapping.
        Model, select_related, prefetch_related = role_specific_maps.account_model_and_attr_mapping[role]

        # Build the queryset for the requesting account with the necessary related fields.
        requesting_account = queries.account_and_its_attr_query_build(Model, select_related, prefetch_related).get(account_id=user)

        # Check if the user has permission to create a group schedule
        if role != 'PRINCIPAL' and not has_permission(requesting_account, 'DELETE', 'DAILY_SCHEDULE'):
            response = 'Could not process your request, you do not have the necessary permissions to delete daily schedules.'

            log_audit(
                actor=requesting_account,
                action='DELETE',
                target_model='DAILY_SCHEDULE',
                outcome='DENIED',
                response=response,
                school=requesting_account.school
            )
            
            return {'error': response}

        if details.get('group'):
            schedule = DailySchedule.objects.get(daily_schedule_id=details.get('schedule'), student_group_timetable__grade__school=requesting_account.school)
            response = {'message': 'the schedule has been successfully deleted from the group schedule and will be removed from schedules of all students subscribed to the group schedule'}
            
        if details.get('teacher'):
            schedule = DailySchedule.objects.get(daily_schedule_id=details.get('schedule'), teacher_timetable__teacher__school=requesting_account.school)
            response = {'message': 'the schedule has been successfully deleted from the teachers schedule and will no longer be available to the teacher'}
            
        else:
            response = 'could not process your request, the provided type is invalid'

            log_audit(
                actor=requesting_account,
                action='DELETE',
                target_model='DAILY_SCHEDULE',
                outcome='DENIED',
                response=response,
                school=requesting_account.school
            )

            return {"error": response}
        
        with transaction.atomic():
            log_audit(
                actor=requesting_account,
                action='DELETE',
                target_model='DAILY_SCHEDULE',
                target_object_id=str(schedule.daily_schedule_id),
                outcome='DELETED',
                response=response,
                school=requesting_account.school
            )

            schedule.delete()

        return response
               
    except Principal.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'a principal account with the provided credentials does not exist, please check your account details and try again'}
                   
    except Admin.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'an admin account with the provided credentials does not exist, please check your account details and try again'}

    except DailySchedule.DoesNotExist:
        # Handle the case where the provided schedule_id does not exist
        return {'error': 'a schedule for your school with the provided credentials does not exist. please verify the details and try again.'}
    
    except ValidationError as e:
        error_message = e.messages[0].lower() if isinstance(e.messages, list) and e.messages else str(e).lower()

        log_audit(
            actor=requesting_account,
            action='DELETE',
            target_model='DAILY_SCHEDULE',
            target_object_id=str(schedule.daily_schedule_id) if schedule else 'N/A',
            outcome='ERROR',
            response=error_message,
            school=requesting_account.school
        )

        return {"error": error_message}

    except Exception as e:
        error_message = str(e)

        log_audit(
            actor=requesting_account,
            action='DELETE',
            target_model='DAILY_SCHEDULE',
            target_object_id=str(schedule.daily_schedule_id) if schedule else 'N/A',
            outcome='ERROR',
            response=error_message,
            school=requesting_account.school
        )

        return {'error': error_message}


@database_sync_to_async
def delete_group_schedule(user, role, details):
    try:
        # Get the appropriate model for the requesting user's role
        Model = role_specific_maps.account_access_control_mapping[role]

        # Retrieve the user and related school in a single query using select_related
        requesting_account = Model.objects.select_related('school').only('school').get(account_id=user)

        # Check if the user has permission to create a group schedule
        if role != 'PRINCIPAL' and not has_permission(requesting_account, 'DELETE', 'GROUP_TIMETABLE'):
            response = 'could not process your request, you do not have the necessary permissions to delete group timetables.'

            log_audit(
                actor=requesting_account,
                action='DELETE',
                target_model='GROUP_TIMETABLE',
                outcome='DENIED',
                response=response,
                school=requesting_account.school
            )
            
            return {'error': response}

        group_timtable = StudentGroupTimetable.objects.select_related('grade').get(group_timetable_id=details.get('group_schedule'), grade__school=requesting_account.school)
        
        with transaction.atomic():
            response = f'grade {group_timtable.grade.grade} group timetable {group_timtable.group_name} has been successfully deleted'

            log_audit(
                actor=requesting_account,
                action='DELETE',
                target_model='GROUP_TIMETABLE',
                target_object_id=str(group_timtable.group_timetable_id),
                outcome='DELETED',
                response=response,
                school=requesting_account.school
            )

            group_timtable.delete()

        return {'message': response}
               
    except Principal.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'a principal account with the provided credentials does not exist, please check your account details and try again'}
                   
    except Admin.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'an admin account with the provided credentials does not exist, please check your account details and try again'}

    except StudentGroupTimetable.DoesNotExist:
        # Handle case where group schedule does not exist
        return {'error': 'a group timetable for your school with the provided credentials does not exist, please check the group details and try again'}
    
    except ValidationError as e:
        error_message = e.messages[0].lower() if isinstance(e.messages, list) and e.messages else str(e).lower()

        log_audit(
            actor=requesting_account,
            action='DELETE',
            target_model='GROUP_TIMETABLE',
            target_object_id=str(group_timtable.group_timetable_id) if group_timtable else 'N/A',
            outcome='ERROR',
            response=error_message,
            school=requesting_account.school
        )

        return {"error": error_message}

    except Exception as e:
        error_message = str(e)

        log_audit(
            actor=requesting_account,
            action='DELETE',
            target_model='GROUP_TIMETABLE',
            target_object_id=str(group_timtable.group_timetable_id) if group_timtable else 'N/A',
            outcome='ERROR',
            response=error_message,
            school=requesting_account.school
        )

        return {'error': error_message}


@database_sync_to_async
def announce(user, role, details):
    try:
        # Get the appropriate model for the requesting user's role
        Model = role_specific_maps.account_access_control_mapping[role]

        # Retrieve the user and related school in a single query using select_related
        requesting_account = Model.objects.select_related('school').only('school').get(account_id=user)

        # Check if the user has permission to create a group schedule
        if role != 'PRINCIPAL' and not has_permission(requesting_account, 'CREATE', 'ANNOUNCEMENT'):
            response = 'could not process your request, you do not have the necessary permissions to create announcements.'

            log_audit(
                actor=requesting_account,
                action='CREATE',
                target_model='ANNOUNCEMENT',
                outcome='DENIED',
                response=response,
                school=requesting_account.school
            )
            
            return {'error': response}

        # Add user and school information to the announcement details
        details.update({'announcer': requesting_account.pk, 'school': requesting_account.school.pk})

        # Serialize the announcement data
        serializer = AnnouncementCreationSerializer(data=details)
        if serializer.is_valid():
            with transaction.atomic():
                announcement = Announcement.objects.create(**serializer.validated_data)
                response = 'the announcement is now available to all users in the school and the parents linked to them.'

                log_audit(
                    actor=requesting_account,
                    action='CREATE',
                    target_model='ANNOUNCEMENT',
                    target_object_id=str(announcement.announcement_id),
                    outcome='DELETED',
                    response=response,
                    school=requesting_account.school
                )

            return {'message': response}
        

        error_response = '; '.join([f"{key}: {', '.join(value)}" for key, value in serializer.errors.items()])

        log_audit(
            actor=requesting_account,
            action='CREATE',
            target_model='ANNOUNCEMENT',
            outcome='ERROR',
            response=f'Validation failed: {error_response}',
            school=requesting_account.school
        )

        return {"error": error_response}
               
    except Principal.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'a principal account with the provided credentials does not exist, please check your account details and try again'}
                   
    except Admin.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'an admin account with the provided credentials does not exist, please check your account details and try again'}
    
    except ValidationError as e:
        error_message = e.messages[0].lower() if isinstance(e.messages, list) and e.messages else str(e).lower()

        log_audit(
            actor=requesting_account,
            action='CREATE',
            target_model='ANNOUNCEMENT',
            target_object_id=str(announcement.announcement_id) if announcement else 'N/A',
            outcome='ERROR',
            response=error_message,
            school=requesting_account.school
        )

        return {"error": error_message}

    except Exception as e:
        error_message = str(e)

        log_audit(
            actor=requesting_account,
            action='CREATE',
            target_model='ANNOUNCEMENT',
            target_object_id=str(announcement.announcement_id) if announcement else 'N/A',
            outcome='ERROR',
            response=error_message,
            school=requesting_account.school
        )

        return {'error': error_message}



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
    