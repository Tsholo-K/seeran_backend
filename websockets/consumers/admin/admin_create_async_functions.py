# channels
from channels.db import database_sync_to_async

# django
from django.db import transaction
from django.utils.dateparse import parse_time
from django.core.exceptions import ValidationError

# models 
from accounts.models import BaseAccount, Teacher, Student
from permission_groups.models import AdminPermissionGroup, TeacherPermissionGroup
from account_permissions.models import AdminAccountPermission, TeacherAccountPermission
from school_announcements.models import Announcement
from grades.models import Grade
from terms.models import Term
from subjects.models import Subject
from classrooms.models import Classroom
from assessments.models import Assessment
from topics.models import Topic
from student_activities.models import StudentActivity
from timetable_sessions.models import TimetableSession
from student_group_timetables.models import StudentGroupTimetable
from teacher_timetables.models import TeacherTimetable
from timetables.models import Timetable

# serilializers
from permission_groups.serializers import AdminPermissionGroupCreationSerializer, TeacherPermissionGroupCreationSerializer
from grades.serializers import GradeCreationSerializer
from terms.serializers import  TermCreationSerializer
from subjects.serializers import  SubjectCreationSerializer
from classrooms.serializers import ClassroomCreationSerializer
from assessments.serializers import AssessmentCreationSerializer
from student_activities.serializers import ActivityCreationSerializer
from student_group_timetables.serializers import StudentGroupTimetableCreationSerializer
from school_announcements.serializers import AnnouncementCreationSerializer

# utility functions 
from accounts import utils as accounts_utilities
from account_permissions import utils as permissions_utilities
from audit_logs import utils as audits_utilities


@database_sync_to_async
def create_account(account, role, details):
    try:
        if details.get('role') not in ['ADMIN', 'TEACHER', 'STUDENT']:
            return {"error": 'could not proccess your request, the provided account role is invalid'}
        
        created_account = None  # Initialize school as None to prevent issues in error handling
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = accounts_utilities.get_account_and_linked_school(account, role)

        if details['role'] == 'ADMIN' and role == 'ADMIN':
            response = f'could not proccess your request, your accounts role does not have enough permissions to perform this action.'
            audits_utilities.log_audit(actor=requesting_account, action='DELETE', target_model='ACCOUNT', outcome='DENIED', server_response=response, school=requesting_account.school)
            return {'error': response}

        # Check if the user has permission to create a grade
        if role != 'PRINCIPAL' and not permissions_utilities.has_permission(requesting_account, 'CREATE', 'ACCOUNT'):
            response = f'could not proccess your request, you do not have the necessary permissions to delete a classroom'
            audits_utilities.log_audit(actor=requesting_account, action='CREATE', target_model='ACCOUNT', outcome='DENIED', server_response=response, school=requesting_account.school)
            return {'error': response}
        
        if details['role'] == 'STUDENT':
            grade = requesting_account.school.grades.get(grade_id=details.get('grade'))
            details['grade'] = grade.id

        details['school'] = requesting_account.school.id

        # Get the appropriate model and related fields (select_related and prefetch_related)
        # for the requesting user's role from the mapping.
        Model, Serializer = accounts_utilities.get_account_and_creation_serializer(details['role'])
        serializer = Serializer(data=details)
        if serializer.is_valid():
            with transaction.atomic():
                created_account = Model.objects.create(**serializer.validated_data)

                if details['role'] == 'TEACHER' and details.get('grant_full_access'):
                    permission_group, created = requesting_account.school.teacher_permission_groups.get_or_create(group_name='Full Access', description='Grants teachers full access to manage their assigned classrooms, including student records, assessments, grading, and attendance. This permission allows teachers to maintain control over all aspects of their classroom operations, ensuring they can effectively support student learning and classroom management.')
                    if created:
                        permissions = []
                        for action, targets in {"create": ["ACTIVITY","ASSESSMENT"], "update": ["ASSESSMENT"], "view": ["ACCOUNT","PROGRESS_REPORT","CLASSROOM","ATTENDANCE","ACTIVITY","ASSESSMENT","TRANSCRIPT","DAILY_SCHEDULE","GROUP_TIMETABLE"], "delete": ["ASSESSMENT"], "submit": ["ATTENDANCE"], "generate": ["PROGRESS_REPORT"]}.items():
                            for target in targets:
                                permissions.append(TeacherAccountPermission(linked_permission_group=permission_group, action=action.upper(), target_model=target.upper(), can_execute=True))

                        batch_size = 50
                        for i in range(0, len(permissions), batch_size):
                            TeacherAccountPermission.objects.bulk_create(permissions[i:i + batch_size])

                    permission_group.update_subscribers(subscribers_list=[created_account.account_id], subscribe=True)
                    permission_group.update_counts()
                    response = f"A new teacher account has been successfully created for your school. The account has also been added to the full access teacher permission group as per your request to grant the account full access to manage it's own classrooms. Depending on the validity of the provided email address, a confirmation email has been sent to them, the account holder can now sign-in and activate their account."

                else:
                    response = f"A new {details['role'].lower()} account has been successfully created for your school. Depending on the validity of the provided email address (if applicable), a confirmation email has been sent to their inbox, the account holder can now sign-in and activate their account."

                audits_utilities.log_audit(actor=requesting_account, action='CREATE', target_model='ACCOUNT', target_object_id=str(created_account.account_id), outcome='CREATED', server_response=response, school=requesting_account.school)

            if details['role'] == 'STUDENT' and not details.get('email_address'):
                return {'message' : 'A new student account has been successfully created, unfortunately accounts with no linked email addresses cannot access the system. You can always update hteir email address later per their consent'}
            
            return {'account' : created_account}
            
        # Return serializer errors if the data is not valid, format it as a string
        error_response = '; '.join([f"{key}: {', '.join(value)}" for key, value in serializer.errors.items()])
        audits_utilities.log_audit(actor=requesting_account, action='CREATE', target_model='ACCOUNT', target_object_id=str(created_account.account_id), outcome='ERROR', server_response=f'Validation failed: {error_response}', school=requesting_account.school)
        return {"error": error_response}
        
    except Grade.DoesNotExist:
        # Handle the case where the provided grade ID does not exist
        return {'error': 'Could not process your request, a grade in your school with the provided credentials does not exist. Please check the grade details and try again.'}

    except ValidationError as e:
        error_message = e.messages[0].lower() if isinstance(e.messages, list) and e.messages else str(e).lower()
        audits_utilities.log_audit(actor=requesting_account, action='CREATE', target_model='ACCOUNT', target_object_id=str(created_account.account_id), outcome='ERROR', server_response=error_message, school=requesting_account.school)
        return {"error": error_message}

    except Exception as e:
        error_message = str(e)
        audits_utilities.log_audit(actor=requesting_account, action='CREATE', target_model='ACCOUNT', target_object_id=str(created_account.account_id), outcome='ERROR', server_response=error_message, school=requesting_account.school)
        return {'error': error_message}


@database_sync_to_async
def create_permission_group(account, role, details):
    try:
        permission_group = None  # Initialize school as None to prevent issues in error handling
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = accounts_utilities.get_account_and_linked_school(account, role)

        # Check if the user has permission to create a grade
        if role != 'PRINCIPAL' and not permissions_utilities.has_permission(requesting_account, 'CREATE', 'PERMISSION'):
            response = f'could not proccess your request, you do not have the necessary permissions to create permission groups. please contact your principal to adjust you permissions for creating permission groups.'
            audits_utilities.log_audit(actor=requesting_account, action='CREATE', target_model='PERMISSION', outcome='DENIED', server_response=response, school=requesting_account.school)
            return {'error': response}
        
        # Check if the 'permissions' key is provided and not empty
        if 'permissions' not in details or not details['permissions']:
            response = ('could not process your request, no permissions have been provided. Please specify the permissions you want to assign to the group and try again.')
            audits_utilities.log_audit(actor=requesting_account, action='CREATE', target_model='PERMISSION', outcome='ERROR', server_response=response, school=requesting_account.school)
            return {'error': response}
        
        elif 'group' not in details or details['group'] not in ['admin', 'teacher']:
            response = f'could not proccess your request, the provided information is invalid for the action you are trying to perform. please make sure to provide a valid group (admin or teacher) for which the permission group is for and try again'
            audits_utilities.log_audit(actor=requesting_account, action='VIEW', target_model='ASSESSMENT', outcome='ERROR', server_response=response, school=requesting_account.school)
            return {'error': response}

        details['school'] = requesting_account.school.id

        # Determine the group type based on the role
        if details['group'] == 'admin':
            # Create an admin permission group
            serializer = AdminPermissionGroupCreationSerializer(data=details)
            
        elif details['group'] == 'teacher':
            # Create a teacher permission group
            serializer = TeacherPermissionGroupCreationSerializer(data=details)

        if serializer.is_valid():
            with transaction.atomic():

                # Determine the group type based on the role
                if details['group'] == 'admin':
                    # Create an admin permission group
                    permission_group  = AdminPermissionGroup.objects.create(**serializer.validated_data)
                    permissions = []
                    for action, targets in details['permissions'].items():
                        for target in targets:
                            permissions.append(AdminAccountPermission(linked_permission_group=permission_group, action=action.upper(), target_model=target.upper(), can_execute=True))

                    batch_size = 50
                    for i in range(0, len(permissions), batch_size):
                        AdminAccountPermission.objects.bulk_create(permissions[i:i + batch_size])

                elif details['group'] == 'teacher':
                    # Create a teacher permission group
                    permission_group  = TeacherPermissionGroup.objects.create(**serializer.validated_data)
                    permissions = []
                    for action, targets in details['permissions'].items():
                        for target in targets:
                            permissions.append(TeacherAccountPermission(linked_permission_group=permission_group, action=action.upper(), target_model=target.upper(), can_execute=True))

                    batch_size = 50
                    for i in range(0, len(permissions), batch_size):
                        TeacherAccountPermission.objects.bulk_create(permissions[i:i + batch_size])

                permission_group.update_counts()
                
                response = f"{details['group']} permission group with the name, {details['group_name']}, has been successfully created. you can now subscribe {details['group']}'s to the group to provide them with the specified permissions"
                audits_utilities.log_audit(actor=requesting_account, action='CREATE', target_model='PERMISSION', target_object_id=str(permission_group.permission_group_id), outcome='CREATED', server_response=response, school=requesting_account.school)

            return {'message' : response}
            
        # Return serializer errors if the data is not valid, format it as a string
        error_response = '; '.join([f"{key}: {', '.join(value)}" for key, value in serializer.errors.items()])
        audits_utilities.log_audit(actor=requesting_account, action='CREATE', target_model='PERMISSION', target_object_id=str(permission_group.permission_group_id) if permission_group else 'N/A', outcome='ERROR', server_response=f'Validation failed: {error_response}', school=requesting_account.school)

        return {"error": error_response}

    except ValidationError as e:
        error_message = e.messages[0].lower() if isinstance(e.messages, list) and e.messages else str(e).lower()
        audits_utilities.log_audit(actor=requesting_account, action='CREATE', target_model='PERMISSION', target_object_id=str(permission_group.permission_group_id) if permission_group else 'N/A', outcome='ERROR', server_response=error_message, school=requesting_account.school)

        return {"error": error_message}

    except Exception as e:
        error_message = str(e)
        audits_utilities.log_audit(actor=requesting_account, action='CREATE', target_model='PERMISSION', target_object_id=str(permission_group.permission_group_id) if permission_group else 'N/A', outcome='ERROR', server_response=error_message, school=requesting_account.school)

        return {'error': error_message}


@database_sync_to_async
def create_announcement(user, role, details):
    try:
        announcement = None  # Initialize requested_account as None to prevent issues in error handling
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = accounts_utilities.get_account_and_linked_school(user, role)

        # Check if the user has permission to create a group schedule
        if role != 'PRINCIPAL' and not permissions_utilities.has_permission(requesting_account, 'CREATE', 'ANNOUNCEMENT'):
            response = 'could not process your request, you do not have the necessary permissions to create announcements.'
            audits_utilities.log_audit(actor=requesting_account, action='CREATE', target_model='ANNOUNCEMENT', outcome='DENIED', response=response, school=requesting_account.school)

            return {'error': response}

        # Add user and school information to the announcement details
        details.update({'announcer': requesting_account.pk, 'school': requesting_account.school.pk})

        # Serialize the announcement data
        serializer = AnnouncementCreationSerializer(data=details)
        if serializer.is_valid():
            with transaction.atomic():
                announcement = Announcement.objects.create(**serializer.validated_data)

                response = 'the announcement is now available to all users in the school and the parents linked to them.'
                audits_utilities.log_audit(actor=requesting_account, action='CREATE', target_model='ANNOUNCEMENT', target_object_id=str(announcement.announcement_id), outcome='DELETED', response=response, school=requesting_account.school)

            return {'message': response}

        error_response = '; '.join([f"{key}: {', '.join(value)}" for key, value in serializer.errors.items()])
        audits_utilities.log_audit(actor=requesting_account, action='CREATE', target_model='ANNOUNCEMENT', outcome='ERROR', response=f'Validation failed: {error_response}', school=requesting_account.school)

        return {"error": error_response}

    except ValidationError as e:
        error_message = e.messages[0].lower() if isinstance(e.messages, list) and e.messages else str(e).lower()
        audits_utilities.log_audit(actor=requesting_account, action='CREATE', target_model='ANNOUNCEMENT', target_object_id=str(announcement.announcement_id) if announcement else 'N/A', outcome='ERROR', response=error_message, school=requesting_account.school)

        return {"error": error_message}

    except Exception as e:
        error_message = str(e)
        audits_utilities.log_audit(actor=requesting_account, action='CREATE', target_model='ANNOUNCEMENT', target_object_id=str(announcement.announcement_id) if announcement else 'N/A', outcome='ERROR', response=error_message, school=requesting_account.school)

        return {'error': error_message}


@database_sync_to_async
def create_grade(account, role, details):
    try:
        grade = None  # Initialize grade as None to prevent issues in error handling
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = accounts_utilities.get_account_and_linked_school(account, role)

        # Check if the user has permission to create a grade
        if role != 'PRINCIPAL' and not permissions_utilities.has_permission(requesting_account, 'CREATE', 'GRADE'):
            response = f'could not proccess your request, you do not have the necessary permissions to create a grade'
            audits_utilities.log_audit(actor=requesting_account, action='CREATE', target_model='GRADE', outcome='DENIED', server_response=response, school=requesting_account.school)
            return {'error': response}

        # Set the school field in the details to the user's school ID
        details['school'] = requesting_account.school.id

        # Serialize the details for grade creation
        serializer = GradeCreationSerializer(data=details)
        if serializer.is_valid():
            # Create the grade within a transaction to ensure atomicity
            with transaction.atomic():
                grade = Grade.objects.create(**serializer.validated_data)

                response = f'grade {grade.grade} has been successfully created for your school. you can now add students, subjects, classes and start tracking attendance and performnace'
                audits_utilities.log_audit(actor=requesting_account, action='CREATE', target_model='GRADE', target_object_id=str(grade.grade_id), outcome='CREATED', server_response=response, school=requesting_account.school,)

            return {'message' : response}
                
        # Return serializer errors if the data is not valid, format it as a string
        error_response = '; '.join([f"{key}: {', '.join(value)}" for key, value in serializer.errors.items()])
        audits_utilities.log_audit(actor=requesting_account, action='CREATE', target_model='GRADE', target_object_id=str(grade.grade_id), outcome='ERROR', server_response=f'Validation failed: {error_response}', school=requesting_account.school)

        return {"error": error_response}

    except ValidationError as e:
        error_message = e.messages[0].lower() if isinstance(e.messages, list) and e.messages else str(e).lower()
        audits_utilities.log_audit(actor=requesting_account, action='CREATE', target_model='GRADE', target_object_id=str(grade.grade_id), outcome='ERROR', server_response=error_message, school=requesting_account.school)

        return {"error": error_message}

    except Exception as e:
        error_message = str(e)
        audits_utilities.log_audit(actor=requesting_account, action='CREATE', target_model='GRADE', target_object_id=str(grade.grade_id), outcome='ERROR', server_response=error_message, school=requesting_account.school)

        return {'error': error_message}


@database_sync_to_async
def create_term(user, role, details):
    try:
        term = None  # Initialize term as None to prevent issues in error handling
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = accounts_utilities.get_account_and_linked_school(user, role)

        # Check if the user has permission to create a grade
        if role != 'PRINCIPAL' and not permissions_utilities.has_permission(requesting_account, 'CREATE', 'TERM'):
            response = f'could not proccess your request, you do not have the necessary permissions to create a term'
            audits_utilities.log_audit(actor=requesting_account, action='CREATE', target_model='TERM', outcome='DENIED', server_response=response, school=requesting_account.school)

            return {'error': response}
        
        # Check if the 'permissions' key is provided and not empty
        if 'grade' not in details:
            response = f'could not proccess your request, the provided information is invalid for the action you are trying to perform. please make sure to provide a valid grade ID and try again'
            audits_utilities.log_audit(actor=requesting_account, action='CREATE', target_model='TERM', outcome='ERROR', server_response=response, school=requesting_account.school)
            return {'error': response}

        grade = requesting_account.school.grades.get(grade_id=details['grade'])

        # Add the school ID to the term details
        details['school'] = requesting_account.school.id
        details['grade'] = grade.id

        # Initialize the serializer with the incoming data
        serializer = TermCreationSerializer(data=details)
        if serializer.is_valid():
            # Using atomic transaction to ensure data integrity
            with transaction.atomic():
                # Create the new term using the validated data
                term = Term.objects.create(**serializer.validated_data)

                response = f"A new term, {term.term}, for your schools {grade.grade} has been successfully created."
                audits_utilities.log_audit(actor=requesting_account, action='CREATE', target_model='TERM', target_object_id=str(term.term_id), outcome='CREATED', server_response=response, school=requesting_account.school,)

            return {"message": response}
        
        # Return serializer errors if the data is not valid, format it as a string
        error_response = '; '.join([f"{key}: {', '.join(value)}" for key, value in serializer.errors.items()])
        audits_utilities.log_audit(actor=requesting_account, action='CREATE', target_model='TERM', target_object_id=str(term.term_id), outcome='ERROR', server_response=f'Validation failed: {error_response}', school=requesting_account.school)
        return {"error": error_response}

    except Grade.DoesNotExist:
        # Handle the case where the provided grade ID does not exist
        return {'error': 'a grade in your school with the provided credentials does not exist. please check the grade details and try again.'}

    except ValidationError as e:
        error_message = e.messages[0].lower() if isinstance(e.messages, list) and e.messages else str(e).lower()
        audits_utilities.log_audit(actor=requesting_account, action='CREATE', target_model='TERM', target_object_id=str(term.term_id), outcome='ERROR', server_response=error_message, school=requesting_account.school)
        return {"error": error_message}

    except Exception as e:
        error_message = str(e)
        audits_utilities.log_audit(actor=requesting_account, action='CREATE', target_model='TERM', target_object_id=str(term.term_id), outcome='ERROR', server_response=error_message, school=requesting_account.school)
        return {'error': error_message}


@database_sync_to_async
def create_subject(user, role, details):
    try:
        subject = None  # Initialize subject as None to prevent issues in error handling
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = accounts_utilities.get_account_and_linked_school(user, role)

        # Check if the user has permission to create a grade
        if role != 'PRINCIPAL' and not permissions_utilities.has_permission(requesting_account, 'CREATE', 'SUBJECT'):
            response = f'could not proccess your request, you do not have the necessary permissions to create a subject'
            audits_utilities.log_audit(actor=requesting_account, action='CREATE', target_model='SUBJECT', outcome='DENIED', response=response, school=requesting_account.school)

            return {'error': response}

        grade = requesting_account.school.grades.get(grade_id=details.get('grade'))

        details['grade'] = grade.pk

        # Serialize the details for grade creation
        serializer = SubjectCreationSerializer(data=details)
        # Validate the serialized data
        if serializer.is_valid():
            # Create the grade within a transaction to ensure atomicity
            with transaction.atomic():
                subject = Subject.objects.create(**serializer.validated_data)

                response = f"{subject.subject} subject has been successfully created for your schools grade {grade.grade}".lower()
                audits_utilities.log_audit(actor=requesting_account, action='CREATE', target_model='SUBJECT', target_object_id=str(subject.subject_id) if subject else 'N/A', outcome='CREATED', response=response, school=requesting_account.school,)

            return {"message": response}
                
        # Return serializer errors if the data is not valid, format it as a string
        error_response = '; '.join([f"{key}: {', '.join(value)}" for key, value in serializer.errors.items()])
        audits_utilities.log_audit(actor=requesting_account, action='CREATE', target_model='SUBJECT', target_object_id=str(subject.subject_id) if subject else 'N/A', outcome='ERROR', response=f'Validation failed: {error_response}', school=requesting_account.school)

        return {"error": error_response}

    except Grade.DoesNotExist:
        # Handle the case where the provided grade ID does not exist
        return {'error': 'a grade in your school with the provided credentials does not exist. please check the grade details and try again.'}

    except ValidationError as e:
        error_message = e.messages[0].lower() if isinstance(e.messages, list) and e.messages else str(e).lower()
        audits_utilities.log_audit(actor=requesting_account, action='CREATE', target_model='SUBJECT', target_object_id=str(subject.subject_id) if subject else 'N/A', outcome='ERROR', response=error_message, school=requesting_account.school)

        return {"error": error_message}

    except Exception as e:
        error_message = str(e)
        audits_utilities.log_audit(actor=requesting_account, action='CREATE', target_model='SUBJECT', target_object_id=str(subject.subject_id) if subject else 'N/A', outcome='ERROR', response=error_message, school=requesting_account.school)

        return {'error': error_message}


@database_sync_to_async
def create_classroom(account, role, details):
    try:
        classroom = None  # Initialize classroom as None to prevent issues in error handling
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = accounts_utilities.get_account_and_linked_school(account, role)

        # Check if the user has permission to create a grade
        if role != 'PRINCIPAL' and not permissions_utilities.has_permission(requesting_account, 'CREATE', 'CLASSROOM'):
            response = f'could not proccess your request, you do not have the necessary permissions to create a classroom'
            audits_utilities.log_audit(actor=requesting_account, action='CREATE', target_model='CLASSROOM', outcome='DENIED', server_response=response, school=requesting_account.school)

            return {'error': response}
        
        # Check if the 'grade' key is provided and not empty
        elif 'grade' not in details and ('register_classroom' not in details or 'subject' not in details):
            response = f'could not proccess your request, the provided information is invalid for the action you are trying to perform. please make sure to provide a valid grade ID and try again'
            audits_utilities.log_audit(actor=requesting_account, action='CREATE', target_model='CLASSROOM', outcome='ERROR', server_response=response, school=requesting_account.school)
            return {'error': response}

        # Retrieve the grade and validate school ownership
        grade = requesting_account.school.grades.get(grade_id=details['grade'])

        if details.get('register_classroom'):
            details['subject'] = None

            response = f"A new register classroom, group {details['group']}, for your schools grade {grade.grade} has been successfully created. You can now {'assign a teacher to the classroom,' if not details.get('teacher') else None} add students and start tracking attendance."
        
        else:
            # Retrieve the subject and validate it against the grade
            subject = requesting_account.school.subjects.get(subject_id=details['subject'], grade=grade)
            
            details['register_classroom'] = False
            details['subject'] = subject.id

            response = f"A new classroom, group {details['group']}, for your schools grade {grade.grade} {subject.subject.lower()} subject has been successfully created. You can now {'assign a teacher to the classroom,' if not details.get('teacher') else None} add students and track performance."

        # Set the school and grade fields
        details.update({'school': requesting_account.school.id, 'grade': grade.id})

        # If a teacher is specified, update the teacher for the class
        if details.get('teacher'):
            teacher = requesting_account.school.teachers.only('id').get(account_id=details['teacher'])
            details['teacher'] = teacher.id

        # Serialize and validate the data
        serializer = ClassroomCreationSerializer(data=details)
        if serializer.is_valid():
            # Create the class within a transaction
            with transaction.atomic():
                classroom = Classroom.objects.create(**serializer.validated_data)

                audits_utilities.log_audit(actor=requesting_account, action='CREATE', target_model='CLASSROOM', target_object_id=str(classroom.classroom_id) if classroom else 'N/A', outcome='CREATED', server_response=response, school=requesting_account.school,)

            return {'message' : response}
                
        # Return serializer errors if the data is not valid, format it as a string
        error_response = '; '.join([f"{key}: {', '.join(value)}" for key, value in serializer.errors.items()])
        audits_utilities.log_audit(actor=requesting_account, action='CREATE', target_model='SUBJECT', target_object_id=str(classroom.classroom_id) if classroom else 'N/A', outcome='ERROR', server_response=f'Validation failed: {error_response}', school=requesting_account.school)
        return {"error": error_response}
               
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
        audits_utilities.log_audit(actor=requesting_account, action='CREATE', target_model='CLASSROOM', target_object_id=str(classroom.classroom_id) if classroom else 'N/A', outcome='ERROR', server_response=error_message, school=requesting_account.school)
        return {"error": error_message}

    except Exception as e:
        error_message = str(e)
        audits_utilities.log_audit(actor=requesting_account, action='CREATE', target_model='CLASSROOM', target_object_id=str(classroom.classroom_id) if classroom else 'N/A', outcome='ERROR', server_response=error_message, school=requesting_account.school)
        return {'error': error_message}


@database_sync_to_async
def create_assessment(user, role, details):
    try:
        assessment = None  # Initialize assessment as None to prevent issues in error handling
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = accounts_utilities.get_account_and_linked_school(user, role)

        # Check if the user has permission to create an assessment
        if role != 'PRINCIPAL' and not permissions_utilities.has_permission(requesting_account, 'CREATE', 'ASSESSMENT'):
            response = f'could not proccess your request, you do not have the necessary permissions to create assessments.'
            audits_utilities.log_audit(actor=requesting_account, action='CREATE', target_model='ASSESSMENT', outcome='DENIED', response=response, school=requesting_account.school)

            return {'error': response}

        elif details.get('classroom'):
            classroom = requesting_account.school.classes.select_related('grade', 'subject').prefetch_related('grade__terms').get(classroom_id=details.get('classroom'))

            term = classroom.grade.terms.get(term_id=details.get('term'))
            subject = classroom.subject.pk

            details['classroom'] = classroom.pk
            details['grade'] = classroom.grade.pk
 
        elif details.get('grade') and details.get('subject'):
            grade = requesting_account.school.grades.prefetch_related('terms', 'subjects').get(grade_id=details.get('grade'))
            
            term = grade.terms.get(term_id=details.get('term'))
            subject = grade.subjects.get(subject_id=details.get('subject'))
            
            details['grade'] = grade.pk

        else:
            response = "could not proccess your request, invalid assessment creation details. please provide all required information and try again."
            audits_utilities.log_audit(actor=requesting_account, action='CREATE', target_model='ASSESSMENT', outcome='ERROR', response=response, school=requesting_account.school)

            return {'error': response}

        if details.get('moderator'):
            moderator = BaseAccount.objects.only('id').get(account_id=details['moderator'])
            details['moderator'] = moderator.id

        details['assessor'] = requesting_account.id
        details['school'] = requesting_account.school.id
        details['term'] = term.id
        details['subject'] = subject.id

        # Serialize the details for assessment creation
        serializer = AssessmentCreationSerializer(data=details)
        if serializer.is_valid():
            # Create the assessment within a transaction to ensure atomicity
            with transaction.atomic():
                assessment = Assessment.objects.create(**serializer.validated_data)

                if details.get('topics'):
                    topics = []
                    for name in details['topics']:
                        topic, _ = Topic.objects.get_or_create(name=name)
                        topics.append(topic)

                    assessment.topics.set(topics)
                    
                response = f'assessment {assessment.unique_identifier} has been successfully created, and will become accessible to all the students being assessed and their parents'
                audits_utilities.log_audit(actor=requesting_account, action='CREATE', target_model='ASSESSMENT', target_object_id=str(assessment.assessment_id), outcome='CREATED', response=response, school=requesting_account.school)

            return {"message": response}
        
        error_response = '; '.join([f"{key}: {', '.join(value)}" for key, value in serializer.errors.items()])
        audits_utilities.log_audit(actor=requesting_account, action='CREATE', target_model='ASSESSMENT', outcome='ERROR', response=f'Validation failed: {error_response}', school=requesting_account.school)

        return {"error": error_response}
    
    except Classroom.DoesNotExist:
        # Handle case where the classroom does not exist
        return {'error': 'a classroom in your school with the provided credentials does not exist. please check the classroom details and try again.'}
                       
    except Grade.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'an grade for your school with the provided credentials does not exist, please check the grade details and try again'}
                       
    except Term.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'a term for your school with the provided credentials does not exist, please check the term details and try again'}
        
    except Subject.DoesNotExist:
        # Handle case where the subject does not exist
        return {'error': 'a subject in your school with the provided credentials does not exist, please check the subject details and try again.'}

    except ValidationError as e:
        error_message = e.messages[0].lower() if isinstance(e.messages, list) and e.messages else str(e).lower()
        audits_utilities.log_audit(actor=requesting_account, action='CREATE', target_model='ASSESSMENT', target_object_id=str(assessment.assessment_id) if assessment else 'N/A', outcome='ERROR', response=error_message, school=requesting_account.school)

        return {"error": error_message}

    except Exception as e:
        error_message = str(e)
        audits_utilities.log_audit(actor=requesting_account, action='CREATE', target_model='ASSESSMENT', target_object_id=str(assessment.assessment_id) if assessment else 'N/A', outcome='ERROR', response=error_message, school=requesting_account.school)

        return {'error': error_message}


@database_sync_to_async
def create_group_timetable(account, role, details):
    try:
        group_timetable = None  # Initialize group timetable as None to prevent issues in error handling
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = accounts_utilities.get_account_and_linked_school(account, role)

        # Check if the user has permission to create a group schedule
        if role != 'PRINCIPAL' and not permissions_utilities.has_permission(requesting_account, 'CREATE', 'GROUP_TIMETABLE'):
            response = 'Could not process your request, you do not have the necessary permissions to create group timetables.'
            audits_utilities.log_audit(actor=requesting_account, action='CREATE', target_model='GROUP_TIMETABLE', outcome='DENIED', server_response=response, school=requesting_account.school)
            return {'error': response}
        
        # Check if the 'grade' key is provided and not empty
        if 'grade' not in details:
            response = f'could not proccess your request, the provided information is invalid for the action you are trying to perform. please make sure to provide a valid grade ID and try again'
            audits_utilities.log_audit(actor=requesting_account, action='CREATE', target_model='GROUP_TIMETABLE', outcome='ERROR', server_response=response, school=requesting_account.school)
            return {'error': response}

        grade = requesting_account.school.grades.get(grade_id=details['grade'])
        details['grade'] = grade.id
        details['school'] = requesting_account.school.id

        serializer = StudentGroupTimetableCreationSerializer(data=details)
        if serializer.is_valid():
            with transaction.atomic():
                group_timetable = StudentGroupTimetable.objects.create(**serializer.validated_data)
                response = f'A new group timetable for your schools grade {grade.grade} has been successfully created. You can now add individual daily timetables and subscribe students in the grade to the group timetable for a shared weekly schedule.'
            
                audits_utilities.log_audit(actor=requesting_account, action='CREATE', target_model='GROUP_TIMETABLE', target_object_id=str(group_timetable.group_timetable_id) if group_timetable else 'N/A', outcome='CREATED', server_response=response, school=requesting_account.school)

            return {'message': response}

        error_response = '; '.join([f"{key}: {', '.join(value)}" for key, value in serializer.errors.items()])
        audits_utilities.log_audit(actor=requesting_account, action='CREATE', target_model='GROUP_TIMETABLE', target_object_id=str(group_timetable.group_timetable_id) if group_timetable else 'N/A', outcome='ERROR', server_response=f'Validation failed: {error_response}', school=requesting_account.school)
        return {"error": error_response}

    except Grade.DoesNotExist:
        # Handle the case where the requested grade does not exist.
        return {'error': 'A grade in your school with the provided credentials does not exist. Please check the grade details and try again.'}

    except ValidationError as e:
        error_message = e.messages[0].lower() if isinstance(e.messages, list) and e.messages else str(e).lower()
        audits_utilities.log_audit(actor=requesting_account, action='CREATE', target_model='GROUP_TIMETABLE', target_object_id=str(group_timetable.group_timetable_id) if group_timetable else 'N/A', outcome='ERROR', server_response=error_message, school=requesting_account.school)
        return {"error": error_message}

    except Exception as e:
        error_message = str(e)
        audits_utilities.log_audit(actor=requesting_account, action='CREATE', target_model='GROUP_TIMETABLE', target_object_id=str(group_timetable.group_timetable_id) if group_timetable else 'N/A', outcome='ERROR', server_response=error_message, school=requesting_account.school)
        return {'error': error_message}


@database_sync_to_async
def create_timetable(account, role, details):
    try:
        # Validate the day
        day_of_week = details.get('day_of_week', '').upper()
        if day_of_week not in [day[0] for day in Timetable.DAY_OF_THE_WEEK_CHOICES]:
            return {"error": 'Could not process your request, the provided day for the timetable is invalid. Please review the provided day of the week for the timetable and then try again.'}

        timetable = None  # Initialize daily schedule as None to prevent issues in error handling
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = accounts_utilities.get_account_and_linked_school(account, role)

        # Check if the user has permission to create a schedule
        if role != 'PRINCIPAL' and not permissions_utilities.has_permission(requesting_account, 'CREATE', 'TIMETABLE'):
            response = 'Could not process your request, you do not have the necessary permissions to create schedules.'
            audits_utilities.log_audit(actor=requesting_account, action='CREATE', target_model='TIMETABLE', outcome='DENIED', server_response=response, school=requesting_account.school)

            return {'error': response}

        if not 'group_timetable' in details and not 'teacher' in details:
            response = f'could not proccess your request, the provided information is invalid for the action you are trying to perform. please make sure to provide valid group timetable or teacher ID and try again'
            audits_utilities.log_audit(actor=requesting_account, action='CREATE', target_model='TIMETABLE', outcome='ERROR', server_response=response, school=requesting_account.school)
            return {'error': response}

        if details.get('group_timetable'):
            group_timetable = requesting_account.school.group_timetables.get(group_timetable_id=details['group_timetable'])
        
        else:
            teacher = requesting_account.school.teachers.get(account_id=details['teacher'])

        with transaction.atomic():
            if details.get('group_timetable'):
                group_timetable.timetables.filter(day_of_week=day_of_week).delete()
                # Create a new timetable
                timetable = requesting_account.school.timetables.create(day_of_week=day_of_week, day_of_week_order=Timetable.DAY_OF_THE_WEEK_ORDER[day_of_week], student_group_timetable=group_timetable)
                
                group_timetable.timetables_count = group_timetable.timetables.count()
                group_timetable.save()

                response = f'A new timetable has been added to the group\'s weekly schedules. All subscribed students should be able to view the sessions in the timetable when they check their timetables again.'

            else:
                teacher_timetable, created = teacher.teacher_timetable.prefetch_related('timetables').get_or_create()
                if not created:
                    teacher_timetable.timetables.filter(day_of_week=day_of_week).delete()

                # Create a new timetable
                timetable = requesting_account.school.timetables.create(day_of_week=day_of_week, day_of_week_order=Timetable.DAY_OF_THE_WEEK_ORDER[day_of_week], teacher_timetable=teacher_timetable)
                
                group_timetable.timetables_count = group_timetable.timetables.count()
                group_timetable.save()

                response = f'A new timetable has been added to the teacher\'s weekly schedules. They should be able to view the sessions in the schedule when they check their timetables again.'

            sessions = [
                TimetableSession(
                    session_type=session['class'],
                    session_location=session.get('classroom'),
                    seesion_start_time=parse_time(session['startTime']),
                    seesion_end_time=parse_time(session['endTime']),
                    timetable=timetable,
                    school=requesting_account.school
                ) for session in details.get('sessions', [])
            ]

            TimetableSession.objects.bulk_create(sessions)
                    
            audits_utilities.log_audit(actor=requesting_account, action='CREATE', target_model='TIMETABLE', target_object_id=str(timetable.timetable_id) if timetable else 'N/A', outcome='CREATED', server_response=response, school=requesting_account.school,)

        return {'message' : response}

    except Teacher.DoesNotExist:
        # Handle the case where the requested teacher account does not exist.
        return {'error': 'Could not process your request, a teacher account with the provided credentials does not exist, please check the account details and try again'}

    except StudentGroupTimetable.DoesNotExist:
        # Handle the case where the requested student account does not exist.
        return {'error': 'Could not process your request, a group timetable in your school with the provided credentials does not exist. please check the group details and try again.'}

    except ValidationError as e:
        error_message = e.messages[0].lower() if isinstance(e.messages, list) and e.messages else str(e).lower()
        audits_utilities.log_audit(actor=requesting_account, action='CREATE', target_model='TIMETABLE', target_object_id=str(timetable.timetable_id) if timetable else 'N/A', outcome='ERROR', server_response=error_message, school=requesting_account.school)
        return {"error": error_message}

    except Exception as e:
        error_message = str(e)
        audits_utilities.log_audit(actor=requesting_account, action='CREATE', target_model='TIMETABLE', target_object_id=str(timetable.timetable_id) if timetable else 'N/A', outcome='ERROR', server_response=error_message, school=requesting_account.school)
        return {'error': error_message}
    

@database_sync_to_async
def create_student_activity(user, role, details):
    try:
        activity = None
        requesting_user = BaseAccount.objects.get(account_id=user)
        
        requested_account = None  # Initialize requested_account as None to prevent issues in error handling
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = accounts_utilities.get_account_and_attr(user, role)

        # Check if the user has permission to create activities
        if role != 'PRINCIPAL' and not permissions_utilities.has_permission(requesting_account, 'LOG', 'ACTIVITY'):
            response = f'could not proccess your request, you do not have the necessary permissions to log activities assessments.'
            audits_utilities.log_audit(actor=requesting_account, action='LOG', target_model='ACTIVITY', outcome='DENIED', response=response, school=requesting_account.school)

            return {'error': response}

        # Retrieve the student account
        requested_account = Student.objects.get(account_id=details.get('recipient'), school=requesting_account.school)

        # Prepare the data for serialization
        details['recipient'] = requested_account.pk
        details['logger'] = requesting_user.pk
        details['school'] = requesting_account.school.pk

        # Initialize the serializer with the prepared data
        serializer = ActivityCreationSerializer(data=details)
        if serializer.is_valid():
            with transaction.atomic():
                activity = StudentActivity.objects.create(**serializer.validated_data)

                response = f'activity successfully logged. the activity is now available to everyone with access to the student\'s data.'
                audits_utilities.log_audit(actor=requesting_account, action='LOG', target_model='ACTIVITY', target_object_id=str(activity.activity_id), outcome='LOGGED', response=response, school=requesting_account.school)

            return {'message': response}

        error_response = '; '.join([f"{key}: {', '.join(value)}" for key, value in serializer.errors.items()])
        audits_utilities.log_audit(actor=requesting_account, action='LOG', target_model='ACTIVITY', outcome='ERROR', response=f'Validation failed: {error_response}', school=requesting_account.school)

        return {"error": error_response}

    except BaseAccount.DoesNotExist:
        # Handle case where the user or student account does not exist
        return {'error': 'an account with the provided credentials does not exist. Please check the account details and try again.'}

    except ValidationError as e:
        error_message = e.messages[0].lower() if isinstance(e.messages, list) and e.messages else str(e).lower()
        audits_utilities.log_audit(actor=requesting_account, action='LOG', target_model='ACTIVITY', target_object_id=str(activity.activity_id) if activity else 'N/A', outcome='ERROR', response=error_message, school=requesting_account.school)

        return {"error": error_message}

    except Exception as e:
        error_message = str(e)
        audits_utilities.log_audit(actor=requesting_account, action='LOG', target_model='ACTIVITY', target_object_id=str(activity.activity_id) if activity else 'N/A', outcome='ERROR', response=error_message, school=requesting_account.school)

        return {'error': error_message}
    