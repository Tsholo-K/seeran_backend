# python 
from datetime import datetime

# channels
from channels.db import database_sync_to_async

# django
from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_time
from django.core.exceptions import ValidationError

# models 
from users.models import BaseUser, Principal, Admin, Teacher, Student, Parent
from grades.models import Grade
from announcements.models import Announcement
from terms.models import Term
from subjects.models import Subject
from classes.models import Classroom
from attendances.models import Attendance
from assessments.models import Assessment, Submission
from transcripts.models import Transcript
from assessments.models import Topic
from activities.models import Activity
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
from assessments.serializers import AssessmentCreationSerializer
from transcripts.serializers import TranscriptCreationSerializer
from activities.serializers import ActivityCreationSerializer
from student_group_timetables.serializers import StudentGroupScheduleCreationSerializer
from announcements.serializers import AnnouncementCreationSerializer

# checks
from users.checks import permission_checks

# mappings
from users.maps import role_specific_maps

# utility functions 
from users import utils as users_utilities
from permissions import utils as permissions_utilities
from audit_logs import utils as audits_utilities



@database_sync_to_async
def delete_school_account(user, role, details):
    try:
        school = None  # Initialize school as None to prevent issues in error handling
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = users_utilities.get_account_and_linked_school(user, role)

        if role not in ['PRINCIPAL']:
            response = f'could not proccess your request, you do not have the necessary permissions to delete your schools account. only the principal can delete the schools account from the system.'
            audits_utilities.log_audit(actor=requesting_account, action='DELETE', target_model='ACCOUNT', outcome='DENIED', response=response, school=requesting_account.school)

            return {'error': response}
        
        school = requesting_account.school

        with transaction.atomic():
            # Perform bulk delete operations without triggering signals
            Principal.objects.filter(school=school).delete()
            Admin.objects.filter(school=school).delete()
            Teacher.objects.filter(school=school).delete()
            Student.objects.filter(school=school).delete()
            Classroom.objects.filter(school=school).delete()
            Grade.objects.filter(school=school).delete()

            # Delete the School instance
            school.delete()

        # Return a success message
        return {"message": "school account deleted successfully, it was nice while it lasted"}

    except ValidationError as e:
        error_message = e.messages[0].lower() if isinstance(e.messages, list) and e.messages else str(e).lower()
        audits_utilities.log_audit(actor=requesting_account, action='DELETE', target_model='ACCOUNT', target_object_id=str(school.school_id) if school else 'N/A', outcome='ERROR', response=error_message, school=requesting_account.school)

        return {"error": error_message}

    except Exception as e:
        error_message = str(e)
        audits_utilities.log_audit(actor=requesting_account, action='DELETE', target_model='ACCOUNT', target_object_id=str(school.school_id) if school else 'N/A', outcome='ERROR', response=error_message, school=requesting_account.school)

        return {'error': error_message}


@database_sync_to_async
def create_account(user, role, details):
    try:
        if details.get('role') not in ['ADMIN', 'TEACHER', 'STUDENT']:
            return {"error": 'could not proccess your request, the provided account role is invalid'}
        
        created_account = None  # Initialize school as None to prevent issues in error handling
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = users_utilities.get_account_and_linked_school(user, role)

        if details['role'] == 'ADMIN' and role == 'ADMIN':
            response = f'could not proccess your request, your accounts role does not have enough permissions to perform this action.'

            audits_utilities.log_audit(actor=requesting_account, action='DELETE', target_model='ACCOUNT', outcome='DENIED', response=response, school=requesting_account.school)

            return {'error': response}

        # Check if the user has permission to create a grade
        if role != 'PRINCIPAL' and not permissions_utilities.has_permission(requesting_account, 'CREATE', 'ACCOUNT'):
            response = f'could not proccess your request, you do not have the necessary permissions to delete a classroom'
            audits_utilities.log_audit(actor=requesting_account, action='CREATE', target_model='ACCOUNT', outcome='DENIED', response=response, school=requesting_account.school)

            return {'error': response}

        if details['role'] == 'STUDENT':
            grade = requesting_account.school.grades.get(grade_id=details.get('grade'))
            details['grade'] = grade.pk

        details['school'] = requesting_account.school.pk

        # Get the appropriate model and related fields (select_related and prefetch_related)
        # for the requesting user's role from the mapping.
        Model, Serializer = role_specific_maps.account_creation_model_and_serializer_mapping[details['role']]

        serializer = Serializer(data=details)
        if serializer.is_valid():
            with transaction.atomic():
                created_account = Model.objects.create(**serializer.validated_data)
                
                response = f"{details['role']} account successfully created. the {details['role']} can now sign-in and activate the account".lower()
                audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='CLASSROOM', target_object_id=str(created_account.account_id) if created_account else 'N/A', outcome='CREATED', response=response, school=requesting_account.school,)

            if details['role'] == 'STUDENT' and not details.get('email'):
                return {'message' : 'the students account has been successfully created, accounts with no email addresses can not '}
            
            return {'user' : created_account}
            
        # Return serializer errors if the data is not valid, format it as a string
        error_response = '; '.join([f"{key}: {', '.join(value)}" for key, value in serializer.errors.items()])
        audits_utilities.log_audit(actor=requesting_account, action='CREATE', target_model='ACCOUNT', target_object_id=str(created_account.account_id) if created_account else 'N/A', outcome='ERROR', response=f'Validation failed: {error_response}', school=requesting_account.school)

        return {"error": error_response}
        
    except Grade.DoesNotExist:
        # Handle the case where the provided grade ID does not exist
        return {'error': 'a grade in your school with the provided credentials does not exist. please check the grade details and try again.'}

    except ValidationError as e:
        error_message = e.messages[0].lower() if isinstance(e.messages, list) and e.messages else str(e).lower()
        audits_utilities.log_audit(actor=requesting_account, action='CREATE', target_model='ACCOUNT', target_object_id=str(created_account.account_id) if created_account else 'N/A', outcome='ERROR', response=error_message, school=requesting_account.school)

        return {"error": error_message}

    except Exception as e:
        error_message = str(e)
        audits_utilities.log_audit(actor=requesting_account, action='CREATE', target_model='ACCOUNT', target_object_id=str(created_account.account_id) if created_account else 'N/A', outcome='ERROR', response=error_message, school=requesting_account.school)

        return {'error': error_message}


@database_sync_to_async
def link_parent(user, role, details):
    try:    
        student = None  # Initialize student as None to prevent issues in error handling
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = users_utilities.get_account_and_linked_school(user, role)

        # Check if the user has permission to link acounts
        if role != 'PRINCIPAL' and not permissions_utilities.has_permission(requesting_account, 'LINK', 'ACCOUNT'):
            response = f'could not proccess your request, you do not have the necessary permissions to link parents to student accounts'
            audits_utilities.log_audit(actor=requesting_account, action='LINK', target_model='ACCOUNT', outcome='DENIED', response=response, school=requesting_account.school)

            return {'error': response}

        student = Student.objects.prefetch_related('parents').get(account_id=details.get('student'), school=requesting_account.school)

        # Check if the child already has two or more parents linked
        student_parent_count = student.parents.count()
        if student_parent_count >= 2:
            response = f"the provided student account has reached the maximum number of linked parents. please unlink one of the existing parents to link a new one"
            audits_utilities.log_audit(actor=requesting_account, action='LINK', target_model='ACCOUNT', outcome='DENIED', response=response, school=requesting_account.school)

            return {'error': response}
        
        # Check if an account with the provided email already exists
        existing_parent = Parent.objects.filter(email=details.get('email')).first()
        if existing_parent:
            return {'user' : existing_parent, 'notice' : 'there is already a parent account with the provide email address'}

        details['role'] = 'PARENT'
        
        serializer = ParentAccountCreationSerializer(data=details)
        if serializer.is_valid():
            with transaction.atomic():
                parent = Parent.objects.create(**serializer.validated_data)
                parent.children.add(student)

                response = f'parent account successfully created and linked to student. the parent can now sign-in and activate their account'
                audits_utilities.log_audit(actor=requesting_account, action='LINK', target_model='ACCOUNT', target_object_id=str(student.account_id) if student else 'N/A', outcome='LINKED', response=response, school=requesting_account.school,)

            return {'user' : parent}
            
        # Return serializer errors if the data is not valid, format it as a string
        error_response = '; '.join([f"{key}: {', '.join(value)}" for key, value in serializer.errors.items()])
        audits_utilities.log_audit(actor=requesting_account, action='LINK', target_model='ACCOUNT', target_object_id=str(student.account_id) if student else 'N/A', outcome='ERROR', response=f'Validation failed: {error_response}', school=requesting_account.school)

        return {"error": error_response}
                                      
    except Student.DoesNotExist:
        # Handle the case where the requested student account does not exist.
        return {'error': 'A student account with the provided credentials does not exist, please check the account details and try again'}

    except ValidationError as e:
        error_message = e.messages[0].lower() if isinstance(e.messages, list) and e.messages else str(e).lower()
        audits_utilities.log_audit(actor=requesting_account, action='LINK', target_model='ACCOUNT', target_object_id=str(student.account_id) if student else 'N/A', outcome='ERROR', response=error_message, school=requesting_account.school)

        return {"error": error_message}

    except Exception as e:
        error_message = str(e)
        audits_utilities.log_audit(actor=requesting_account, action='LINK', target_model='ACCOUNT', target_object_id=str(student.account_id) if student else 'N/A', outcome='ERROR', response=error_message, school=requesting_account.school)

        return {'error': error_message}
        
    
@database_sync_to_async
def delete_account(user, role, details):
    try:
        if details.get('role') not in ['ADMIN', 'TEACHER', 'STUDENT']:
            return {"error": 'could not proccess your request, the provided account role is invalid'}

        requested_account = None  # Initialize requested_account as None to prevent issues in error handling
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = users_utilities.get_account_and_attr(user, role)

        if details['role'] == 'ADMIN' and role == 'ADMIN':
            response = f'could not proccess your request, your accounts role does not have enough permissions to perform this action.'
            audits_utilities.log_audit(actor=requesting_account, action='DELETE', target_model='ACCOUNT', outcome='DENIED', response=response, school=requesting_account.school)

            return {'error': response}

        # Check if the user has permission to create a grade
        if role != 'PRINCIPAL' and not permissions_utilities.has_permission(requesting_account, 'DELETE', 'ACCOUNT'):
            response = f'could not proccess your request, you do not have the necessary permissions to delete accounts'
            audits_utilities.log_audit(actor=requesting_account, action='DELETE', target_model='ACCOUNT', outcome='DENIED', response=response, school=requesting_account.school)

            return {'error': response}

        elif details['role'] in ['ADMIN', 'TEACHER', 'STUDENT']:
            # Retrieve the requesting users account and related school in a single query using select_related
            requested_account = users_utilities.get_account_and_attr(details.get('account'), details['role'])

            # Check if the requesting user has permission to update the requested user's account.
            permission_error = permission_checks.check_update_details_permissions(requesting_account, requested_account)
            if permission_error:
                return permission_error

            with transaction.atomic():
                response = f"{details['role']} account successfully deleted.".lower()
                audits_utilities.log_audit(actor=requesting_account, action='DELETE', target_model='ACCOUNT', target_object_id=str(requested_account.grade_id) if requested_account else 'N/A', outcome='DELETED', response=response, school=requesting_account.school)

                requested_account.delete()

            return {"message" : response}

        response = 'could not proccess your request, the provided account role is invalid'
        audits_utilities.log_audit(actor=requesting_account, action='DELETE', target_model='ACCOUNT', outcome='DENIED', response=response, school=requesting_account.school)

        return {'error': response}

    except ValidationError as e:
        error_message = e.messages[0].lower() if isinstance(e.messages, list) and e.messages else str(e).lower()
        audits_utilities.log_audit(actor=requesting_account, action='DELETE', target_model='ACCOUNT', target_object_id=str(requested_account.grade_id) if requested_account else 'N/A', outcome='ERROR', response=error_message, school=requesting_account.school)

        return {"error": error_message}

    except Exception as e:
        error_message = str(e)
        audits_utilities.log_audit(actor=requesting_account, action='DELETE', target_model='ACCOUNT', target_object_id=str(requested_account.grade_id) if requested_account else 'N/A', outcome='ERROR', response=error_message, school=requesting_account.school)

        return {'error': error_message}


@database_sync_to_async
def unlink_parent(user, role, details):
    try:
        student = None  # Initialize student as None to prevent issues in error handling
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = users_utilities.get_account_and_linked_school(user, role)

        # Check if the user has permission to create a grade
        if role != 'PRINCIPAL' and not permissions_utilities.has_permission(requesting_account, 'UNLINK', 'ACCOUNT'):
            response = f'could not proccess your request, you do not have the necessary permissions to unlink parents from student accounts'
            audits_utilities.log_audit(actor=requesting_account, action='UNLINK', target_model='ACCOUNT', outcome='DENIED', response=response, school=requesting_account.school)

            return {'error': response}

        # Fetch the student account using the provided child ID
        student = Student.objects.prefetch_related('parents').get(account_id=details.get('student'), school=requesting_account.school)

        # Fetch the parent account using the provided parent ID
        parent = student.parents.filter(account_id=details.get('parent')).first()

        if not parent:
            response = "could not process your request, the specified student account is not a child of the provided parent account. please ensure the provided information is complete and true"
            audits_utilities.log_audit(actor=requesting_account, action='UNLINK', target_model='ACCOUNT', target_object_id=str(student.account_id), outcome='DENIED', response=response, school=requesting_account.school)

            return {'error': response}

        # Remove the child from the parent's list of children
        with transaction.atomic():
            parent.children.remove(student)
            if parent.children.len <= 0:
                parent.is_active = False
                parent.save()

            response = "the parent account has been successfully unlinked from the student. the account will no longer be associated with the student or have access to the student's data"
            audits_utilities.log_audit(actor=requesting_account, action='UNLINK', target_model='ACCOUNT', target_object_id=str(student.account_id) if student else 'N/A', outcome='UNLINKED', response=response, school=requesting_account.school,)

        return {"message": response}
                   
    except Student.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'a student account in your school with the provided credentials does not exist, please check the account details and try again'}

    except ValidationError as e:
        error_message = e.messages[0].lower() if isinstance(e.messages, list) and e.messages else str(e).lower()
        audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='GRADE', target_object_id=str(student.account_id) if student else 'N/A', outcome='ERROR', response=error_message, school=requesting_account.school)

        return {"error": error_message}

    except Exception as e:
        error_message = str(e)
        audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='GRADE', target_object_id=str(student.account_id) if student else 'N/A', outcome='ERROR', response=error_message, school=requesting_account.school)

        return {'error': error_message}


@database_sync_to_async
def create_grade(user, role, details):
    try:
        grade = None  # Initialize grade as None to prevent issues in error handling
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = users_utilities.get_account_and_linked_school(user, role)

        # Check if the user has permission to create a grade
        if role != 'PRINCIPAL' and not permissions_utilities.has_permission(requesting_account, 'CREATE', 'GRADE'):
            response = f'could not proccess your request, you do not have the necessary permissions to create a grade'
            audits_utilities.log_audit(actor=requesting_account, action='CREATE', target_model='GRADE', outcome='DENIED', response=response, school=requesting_account.school)

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
                audits_utilities.log_audit(actor=requesting_account, action='CREATE', target_model='GRADE', target_object_id=str(grade.grade_id) if grade else 'N/A', outcome='CREATED', response=response, school=requesting_account.school,)

            return {'message' : response}
                
        # Return serializer errors if the data is not valid, format it as a string
        error_response = '; '.join([f"{key}: {', '.join(value)}" for key, value in serializer.errors.items()])
        audits_utilities.log_audit(actor=requesting_account, action='CREATE', target_model='GRADE', target_object_id=str(grade.grade_id) if grade else 'N/A', outcome='ERROR', response=f'Validation failed: {error_response}', school=requesting_account.school)

        return {"error": error_response}

    except ValidationError as e:
        error_message = e.messages[0].lower() if isinstance(e.messages, list) and e.messages else str(e).lower()
        audits_utilities.log_audit(actor=requesting_account, action='CREATE', target_model='GRADE', target_object_id=str(grade.grade_id) if grade else 'N/A', outcome='ERROR', response=error_message, school=requesting_account.school)

        return {"error": error_message}

    except Exception as e:
        error_message = str(e)
        audits_utilities.log_audit(actor=requesting_account, action='CREATE', target_model='GRADE', target_object_id=str(grade.grade_id) if grade else 'N/A', outcome='ERROR', response=error_message, school=requesting_account.school)

        return {'error': error_message}


@database_sync_to_async
def delete_grade(user, role, details):
    try:
        grade = None  # Initialize requested_account as None to prevent issues in error handling
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = users_utilities.get_account_and_linked_school(user, role)

        # Check if the user has permission to create a grade
        if role != 'PRINCIPAL' and not permissions_utilities.has_permission(requesting_account, 'DELETE', 'GRADE'):
            response = f'could not proccess your request, you do not have the necessary permissions to delete a grade'
            audits_utilities.log_audit(actor=requesting_account, action='DELETE', target_model='GRADE', outcome='DENIED', response=response, school=requesting_account.school)

            return {'error': response}

        grade = requesting_account.school.grades.get(grade_id=details.get('grade'), school=requesting_account.school)

        # Create the grade within a transaction to ensure atomicity
        with transaction.atomic():
            response = f"your schools grade {grade.grade} has been successfully deleted. the grade and all it's associated data will no longer be assessible on the system"
            audits_utilities.log_audit(actor=requesting_account, action='DELETE', target_model='GRADE', target_object_id=str(grade.grade_id) if grade else 'N/A', outcome='DELETED', response=response, school=requesting_account.school,)
            
            grade.delete()

        return {'message' : response}
    
    except Grade.DoesNotExist:
        # Handle the case where the provided grade ID does not exist
        return {'error': 'a grade in your school with the provided credentials does not exist. please check the grade details and try again.'}

    except ValidationError as e:
        error_message = e.messages[0].lower() if isinstance(e.messages, list) and e.messages else str(e).lower()
        audits_utilities.log_audit(actor=requesting_account, action='DELETE', target_model='GRADE', target_object_id=str(grade.grade_id) if grade else 'N/A', outcome='ERROR', response=error_message, school=requesting_account.school)

        return {"error": error_message}

    except Exception as e:
        error_message = str(e)
        audits_utilities.log_audit(actor=requesting_account, action='DELETE', target_model='GRADE', target_object_id=str(grade.grade_id) if grade else 'N/A', outcome='ERROR', response=error_message, school=requesting_account.school)

        return {'error': error_message}
    

@database_sync_to_async
def create_term(user, role, details):
    try:
        term = None  # Initialize term as None to prevent issues in error handling
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = users_utilities.get_account_and_linked_school(user, role)

        # Check if the user has permission to create a grade
        if role != 'PRINCIPAL' and not permissions_utilities.has_permission(requesting_account, 'CREATE', 'TERM'):
            response = f'could not proccess your request, you do not have the necessary permissions to create a term'
            audits_utilities.log_audit(actor=requesting_account, action='CREATE', target_model='TERM', outcome='DENIED', response=response, school=requesting_account.school)

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
                audits_utilities.log_audit(actor=requesting_account, action='CREATE', target_model='TERM', target_object_id=str(term.term_id), outcome='CREATED', response=response, school=requesting_account.school,)

            return {"message": response}
        
        # Return serializer errors if the data is not valid, format it as a string
        error_response = '; '.join([f"{key}: {', '.join(value)}" for key, value in serializer.errors.items()])
        audits_utilities.log_audit(actor=requesting_account, action='CREATE', target_model='TERM', target_object_id=str(term.term_id) if term else 'N/A', outcome='ERROR', response=f'Validation failed: {error_response}', school=requesting_account.school)

        return {"error": error_response}

    except Grade.DoesNotExist:
        # Handle the case where the provided grade ID does not exist
        return {'error': 'a grade in your school with the provided credentials does not exist. please check the grade details and try again.'}

    except ValidationError as e:
        error_message = e.messages[0].lower() if isinstance(e.messages, list) and e.messages else str(e).lower()
        audits_utilities.log_audit(actor=requesting_account, action='CREATE', target_model='TERM', target_object_id=str(term.term_id) if term else 'N/A', outcome='ERROR', response=error_message, school=requesting_account.school)

        return {"error": error_message}

    except Exception as e:
        error_message = str(e)
        audits_utilities.log_audit(actor=requesting_account, action='CREATE', target_model='TERM', target_object_id=str(term.term_id) if term else 'N/A', outcome='ERROR', response=error_message, school=requesting_account.school)

        return {'error': error_message}


@database_sync_to_async
def delete_term(user, role, details):
    try:
        term = None  # Initialize term as None to prevent issues in error handling
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = users_utilities.get_account_and_linked_school(user, role)

        # Check if the user has permission to create a grade
        if role != 'PRINCIPAL' and not permissions_utilities.has_permission(requesting_account, 'DELETE', 'TERM'):
            response = f'could not proccess your request, you do not have the necessary permissions to delete a grade'
            audits_utilities.log_audit(actor=requesting_account, action='DELETE', target_model='TERM', outcome='DENIED', response=response, school=requesting_account.school)

            return {'error': response}

        term = requesting_account.school.terms.get(term_id=details.get('term'))

        # Create the grade within a transaction to ensure atomicity
        with transaction.atomic():
            response = f"a term in your school with the term ID {term.term_id} has been successfully deleted. the term and all it's associated data will no longer be assessible on the system"
            audits_utilities.log_audit(actor=requesting_account, action='DELETE', target_model='TERM', target_object_id=str(term.term_id) if term else 'N/A', outcome='DELETED', response=response, school=requesting_account.school,)
            
            term.delete()

        return {'message' : response}
    
    except Term.DoesNotExist:
        # Handle the case where the provided grade ID does not exist
        return {'error': 'a term in your school with the provided credentials does not exist. please check the term details and try again.'}

    except ValidationError as e:
        error_message = e.messages[0].lower() if isinstance(e.messages, list) and e.messages else str(e).lower()
        audits_utilities.log_audit(actor=requesting_account, action='DELETE', target_model='TERM', target_object_id=str(term.term_id) if term else 'N/A', outcome='ERROR', response=error_message, school=requesting_account.school)

        return {"error": error_message}

    except Exception as e:
        error_message = str(e)
        audits_utilities.log_audit(actor=requesting_account, action='DELETE', target_model='TERM', target_object_id=str(term.term_id) if term else 'N/A', outcome='ERROR', response=error_message, school=requesting_account.school)

        return {'error': error_message}


@database_sync_to_async
def create_subject(user, role, details):
    try:
        subject = None  # Initialize subject as None to prevent issues in error handling
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = users_utilities.get_account_and_linked_school(user, role)

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
def delete_subject(user, role, details):
    try:
        subject = None  # Initialize subject as None to prevent issues in error handling
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = users_utilities.get_account_and_linked_school(user, role)

        # Check if the user has permission to create a grade
        if role != 'PRINCIPAL' and not permissions_utilities.has_permission(requesting_account, 'DELETE', 'SUBJECT'):
            response = f'could not proccess your request, you do not have the necessary permissions to delete a subject'
            audits_utilities.log_audit(actor=requesting_account, action='DELETE', target_model='SUBJECT', outcome='DENIED', response=response, school=requesting_account.school)

            return {'error': response}

        subject = Subject.objects.get(subject_id=details.get('subject'), school=requesting_account.school)

        # Create the grade within a transaction to ensure atomicity
        with transaction.atomic():
            response = f"a subject in your school with the subject ID {subject.subject_id} has been successfully deleted. the term and all it's associated data will no longer be assessible on the system"
            audits_utilities.log_audit(actor=requesting_account, action='DELETE', target_model='SUBJECT', target_object_id=str(subject.subject_id) if subject else 'N/A', outcome='DELETED', response=response, school=requesting_account.school,)
            
            subject.delete()

        return {'message' : response}
    
    except Subject.DoesNotExist:
        # Handle the case where the provided grade ID does not exist
        return {'error': 'a subject in your school with the provided credentials does not exist. please check the subject details and try again.'}

    except ValidationError as e:
        error_message = e.messages[0].lower() if isinstance(e.messages, list) and e.messages else str(e).lower()
        audits_utilities.log_audit(actor=requesting_account, action='DELETE', target_model='SUBJECT', target_object_id=str(subject.subject_id) if subject else 'N/A', outcome='ERROR', response=error_message, school=requesting_account.school)

        return {"error": error_message}

    except Exception as e:
        error_message = str(e)
        audits_utilities.log_audit(actor=requesting_account, action='DELETE', target_model='SUBJECT', target_object_id=str(subject.subject_id) if subject else 'N/A', outcome='ERROR', response=error_message, school=requesting_account.school)

        return {'error': error_message}
    
    
@database_sync_to_async
def create_class(user, role, details):
    try:
        classroom = None  # Initialize classroom as None to prevent issues in error handling
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = users_utilities.get_account_and_linked_school(user, role)

        # Check if the user has permission to create a grade
        if role != 'PRINCIPAL' and not permissions_utilities.has_permission(requesting_account, 'CREATE', 'CLASSROOM'):
            response = f'could not proccess your request, you do not have the necessary permissions to create a classroom'
            audits_utilities.log_audit(actor=requesting_account, action='CREATE', target_model='CLASSROOM', outcome='DENIED', response=response, school=requesting_account.school)

            return {'error': response}

        # Retrieve the grade and validate school ownership
        grade = Grade.objects.select_related('school').get(grade_id=details.get('grade'), school=requesting_account.school)

        if details.get('register_class'):
            details['subject'] = None

            response = f'register classroom for grade {grade.grade} has been created successfully. you can now add students and track attendance.'
        
        elif details.get('subject'):
            # Retrieve the subject and validate it against the grade
            subject = Subject.objects.get(subject_id=details.get('subject'), grade=grade)
            
            details['subject'] = subject.pk
            details['register_class'] = False

            response = f'classroom for grade {grade.grade} {subject.subject} has been created successfully.. you can now add students and track performance.'.lower()
        
        else:
            response = "could not proccess your request, invalid classroom creation details. please provide all required information and try again."
            audits_utilities.log_audit(actor=requesting_account, action='CREATE', target_model='CLASSROOM', outcome='ERROR', response=response, school=requesting_account.school,)

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

                audits_utilities.log_audit(actor=requesting_account, action='CREATE', target_model='CLASSROOM', target_object_id=str(classroom.classroom_id) if classroom else 'N/A', outcome='CREATED', response=response, school=requesting_account.school,)

            return {'message' : response}
                
        # Return serializer errors if the data is not valid, format it as a string
        error_response = '; '.join([f"{key}: {', '.join(value)}" for key, value in serializer.errors.items()])
        audits_utilities.log_audit(actor=requesting_account, action='CREATE', target_model='SUBJECT', target_object_id=str(classroom.classroom_id) if classroom else 'N/A', outcome='ERROR', response=f'Validation failed: {error_response}', school=requesting_account.school)

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
        audits_utilities.log_audit(actor=requesting_account, action='CREATE', target_model='CLASSROOM', target_object_id=str(classroom.classroom_id) if classroom else 'N/A', outcome='ERROR', response=error_message, school=requesting_account.school)

        return {"error": error_message}

    except Exception as e:
        error_message = str(e)
        audits_utilities.log_audit(actor=requesting_account, action='CREATE', target_model='CLASSROOM', target_object_id=str(classroom.classroom_id) if classroom else 'N/A', outcome='ERROR', response=error_message, school=requesting_account.school)

        return {'error': error_message}


@database_sync_to_async
def delete_class(user, role, details):
    try:
        classroom = None  # Initialize classroom as None to prevent issues in error handling
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = users_utilities.get_account_and_linked_school(user, role)

        # Check if the user has permission to create a grade
        if role != 'PRINCIPAL' and not permissions_utilities.has_permission(requesting_account, 'DELETE', 'CLASSROOM'):
            response = f'could not proccess your request, you do not have the necessary permissions to delete a classroom'
            audits_utilities.log_audit(actor=requesting_account, action='DELETE', target_model='CLASSROOM', outcome='DENIED', response=response, school=requesting_account.school)

            return {'error': response}

        classroom = Classroom.objects.select_related('grade').only('grade__grade').get(class_id=details.get('class'), school=requesting_account.school)
        response = f'grade {classroom.grade.grade} classroom deleted successfully, the classroom will no longer be accessible or available in your schools data'
        
        with transaction.atomic():
            classroom.delete()

            audits_utilities.log_audit(actor=requesting_account, action='DELETE', target_model='CLASSROOM', target_object_id=str(classroom.classroom_id) if classroom else 'N/A', outcome='LINKED', response=response, school=requesting_account.school,)

        return {'message': response}

    except Classroom.DoesNotExist:
        # Handle case where the grade does not exist
        return {'error': 'classroom with the provided credentials does not exist'}

    except ValidationError as e:
        error_message = e.messages[0].lower() if isinstance(e.messages, list) and e.messages else str(e).lower()
        audits_utilities.log_audit(actor=requesting_account, action='DELETE', target_model='CLASSROOM', target_object_id=str(classroom.classroom_id) if classroom else 'N/A', outcome='ERROR', response=error_message, school=requesting_account.school)

        return {"error": error_message}

    except Exception as e:
        error_message = str(e)
        audits_utilities.log_audit(actor=requesting_account, action='DELETE', target_model='CLASSROOM', target_object_id=str(classroom.classroom_id) if classroom else 'N/A', outcome='ERROR', response=error_message, school=requesting_account.school)

        return {'error': error_message}


@database_sync_to_async
def set_assessment(user, role, details):
    try:
        assessment = None  # Initialize assessment as None to prevent issues in error handling
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = users_utilities.get_account_and_linked_school(user, role)

        # Check if the user has permission to create an assessment
        if role != 'PRINCIPAL' and not permissions_utilities.has_permission(requesting_account, 'CREATE', 'ASSESSMENT'):
            response = f'could not proccess your request, you do not have the necessary permissions to create assessments.'
            audits_utilities.log_audit(actor=requesting_account, action='CREATE', target_model='ASSESSMENT', outcome='DENIED', response=response, school=requesting_account.school)

            return {'error': response}


        elif details.get('classroom'):
            classroom = requesting_account.school.classes.select_related('grade', 'subject').prefetch_related('grade__terms').get(classroom_id=details.get('classroom'))

            # Check for existing assessment with the same unique identifier in the same school
            existing_assessment = requesting_account.school.assessments.filter(
                unique_identifier=details.get('unique_identifier'),
                classroom=classroom
            ).first()

            if existing_assessment:
                with transaction.atomic():

                    # Duplicate the assessment for the other classroom
                    duplicate_assessment = Assessment.objects.create(
                        unique_identifier=existing_assessment.unique_identifier,
                        assessor=requesting_account,
                        moderator=existing_assessment.moderator,
                        date_set=timezone.now(),
                        due_date=existing_assessment.due_date,
                        pass_rate=existing_assessment.pass_rate,
                        average_score=existing_assessment.average_score,
                        start_time=existing_assessment.start_time, 
                        dead_line=existing_assessment.dead_line,
                        title=existing_assessment.title,
                        total=existing_assessment.total,
                        formal=existing_assessment.formal,
                        percentage_towards_term_mark=existing_assessment.percentage_towards_term_mark,
                        term=existing_assessment.term,
                        subject=existing_assessment.subject,
                        classroom=classroom,
                        grade=existing_assessment.grade,
                        school=requesting_account.school
                    )

                    # Copy topics from the original assessment
                    duplicate_assessment.topics.set(existing_assessment.topics.all())

                    response = f'assessment with unique identifier {duplicate_assessment.unique_identifier} created for classroom {classroom.classroom_id}.'
                    audits_utilities.log_audit(actor=requesting_account, action='CREATE', target_model='ASSESSMENT', target_object_id=str(duplicate_assessment.assessment_id), outcome='CREATED', response=response, school=requesting_account.school)

                return {"message": response}

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
            moderator = BaseUser.objects.only('pk').get(account_id=details['moderator'])
            details['moderator'] = moderator.pk

        details['assessor'] = requesting_account.pk
        details['school'] = requesting_account.school.pk
        details['term'] = term.pk
        details['subject'] = subject.pk

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
def delete_assessment(user, role, details):
    try:
        assessment = None  # Initialize assessment as None to prevent issues in error handling
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = users_utilities.get_account_and_linked_school(user, role)

        # Check if the user has permission to create an assessment
        if role != 'PRINCIPAL' and not permissions_utilities.has_permission(requesting_account, 'DELETE', 'ASSESSMENT'):
            response = f'could not proccess your request, you do not have the necessary permissions to delete assessments.'
            audits_utilities.log_audit( actor=requesting_account, action='DELETE', target_model='ASSESSMENT', outcome='DENIED', response=response, school=requesting_account.school)

            return {'error': response}
        
        # Fetch the assessment from the requesting user's school
        assessment = requesting_account.school.assessments.get(assessment_id=details.get('assessment'))

        with transaction.atomic():
            response = f"assessment with assessment ID {assessment.assessment_id} has been successfully deleted, along with it's associated data"
            audits_utilities.log_audit(actor=requesting_account, action='DELETE', target_model='ASSESSMENT', target_object_id=str(assessment.assessment_id), outcome='DELETED', response=response, school=requesting_account.school)

            assessment.delete()

        return {"message": response}

    except Assessment.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'an assessment in your school with the provided credentials does not exist, please check the assessment details and try again'}

    except ValidationError as e:
        error_message = e.messages[0].lower() if isinstance(e.messages, list) and e.messages else str(e).lower()
        audits_utilities.log_audit(actor=requesting_account, action='CREATE', target_model='ASSESSMENT', target_object_id=str(assessment.assessment_id) if assessment else 'N/A', outcome='ERROR', response=error_message, school=requesting_account.school)

        return {"error": error_message}

    except Exception as e:
        error_message = str(e)
        audits_utilities.log_audit(actor=requesting_account, action='CREATE', target_model='ASSESSMENT', target_object_id=str(assessment.assessment_id) if assessment else 'N/A', outcome='ERROR', response=error_message, school=requesting_account.school)

        return {'error': error_message}


@database_sync_to_async
def submit_submissions(user, role, details):
    try:
        assessment = None  # Initialize assessment as None to prevent issues in error handling
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = users_utilities.get_account_and_linked_school(user, role)

        # Check if the user has permission to create an assessment
        if role != 'PRINCIPAL' and not permissions_utilities.has_permission(requesting_account, 'COLLECT', 'ASSESSMENT'):
            response = f'could not proccess your request, you do not have the necessary permissions to collect assessments.'
            audits_utilities.log_audit(actor=requesting_account, action='COLLECT', target_model='ASSESSMENT', outcome='DENIED', response=response, school=requesting_account.school)

            return {'error': response}
        
        student_ids = details['students'].split(', ')

        # Validate that all student IDs exist and are valid
        if not requesting_account.school.students.filter(account_id__in=student_ids).count() == len(student_ids):
            return {'error': 'one or more student account IDs are invalid. please check the provided students information and try again'}
        
        # Fetch the assessment from the requesting user's school
        assessment = requesting_account.school.assessments.get(assessment_id=details.get('assessment'))

        # Prepare the list of Submission objects, dynamically setting status based on the deadline
        submissions = []
        for student_id in student_ids:
            student = requesting_account.school.students.get(account_id=student_id)
            submissions.append(Submission(assessment=assessment, student=student))

        with transaction.atomic():
            # Bulk create Submission objects
            Submission.objects.bulk_create(submissions)

            response = f"assessment submission successfully collected from {len(student_ids)} students."
            audits_utilities.log_audit(actor=requesting_account, action='COLLECT', target_model='ASSESSMENT', target_object_id=str(assessment.assessment_id), outcome='COLLECTED', response=response, school=assessment.school)

        return {"message": response}

    except Assessment.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'an assessment in your school with the provided credentials does not exist, please check the assessment details and try again'}

    except ValidationError as e:
        error_message = e.messages[0].lower() if isinstance(e.messages, list) and e.messages else str(e).lower()
        audits_utilities.log_audit(actor=requesting_account, action='COLLECT', target_model='ASSESSMENT', target_object_id=str(assessment.assessment_id) if assessment else 'N/A', outcome='ERROR', response=error_message, school=requesting_account.school)

        return {"error": error_message}

    except Exception as e:
        error_message = str(e)
        audits_utilities.log_audit(actor=requesting_account, action='COLLECT', target_model='ASSESSMENT', target_object_id=str(assessment.assessment_id) if assessment else 'N/A', outcome='ERROR', response=error_message, school=requesting_account.school)

        return {'error': error_message}


@database_sync_to_async
def grade_student(user, role, details):
    try:
        assessment = None  # Initialize assessment as None to prevent issues in error handling
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = users_utilities.get_account_and_linked_school(user, role)

        # Check if the user has permission to create an assessment
        if role != 'PRINCIPAL' and not permissions_utilities.has_permission(requesting_account, 'GRADE', 'ASSESSMENT'):
            response = f'could not proccess your request, you do not have the necessary permissions to grade assessments.'
            audits_utilities.log_audit(actor=requesting_account, action='GRADE', target_model='ASSESSMENT', outcome='DENIED', response=response, school=requesting_account.school)

            return {'error': response}
                
        if not {'student', 'assessment'}.issubset(details):
            response = f'could not proccess your request, the provided information is invalid for the action you are trying to perform. please make sure to provide valid account and assessnt IDs and try again'
            audits_utilities.log_audit(actor=requesting_account, action='GRADE', target_model='ACCOUNT', outcome='ERROR', response=response, school=requesting_account.school)

            return {'error': response}

        # Fetch the assessment from the requesting user's school
        assessment = requesting_account.school.assessments.select_related('assessor','moderator').get(assessment_id=details['assessment'])
        
        # Check if the user has permission to moderate the assessment
        if requesting_account != assessment.assessor or requesting_account != assessment.moderator:
            response = f'could not proccess your request, you do not have the necessary permissions to grade this assessment. only the assessments assessor or moderator can assign scores to the assessment.'
            audits_utilities.log_audit(actor=requesting_account, action='GRADE', target_model='ASSESSMENT', outcome='DENIED', response=response, school=requesting_account.school)

            return {'error': response}

        student = requesting_account.school.students.get(account_id=details['student'])
        details['student'] = student.pk

        # Initialize the serializer with the prepared data
        serializer = TranscriptCreationSerializer(data=details)
        if serializer.is_valid():
            with transaction.atomic():
                transcript = Transcript.objects.create(**serializer.validated_data)

                response = f"student graded for assessment {assessment.unique_identifier}."
                audits_utilities.log_audit(actor=user,action='GRADE', target_model='ASSESSMENT', target_object_id=str(transcript.transcript_id), outcome='GRADED', response=response, school=assessment.school)

            return {"message": response}

        error_response = '; '.join([f"{key}: {', '.join(value)}" for key, value in serializer.errors.items()])
        audits_utilities.log_audit(actor=requesting_account, action='GRADE', target_model='ASSESSMENT', target_object_id=str(assessment.assessment_id) if assessment else 'N/A', outcome='ERROR', response=f'Validation failed: {error_response}', school=requesting_account.school)

        return {"error": error_response}

    except Assessment.DoesNotExist:
        # Handle the case where the provided assessment ID does not exist
        return {'error': 'an assessment in your school with the provided credentials does not exist, please check the assessment details and try again'}

    except Student.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'a student account with the provided credentials does not exist, please check the accounts details and try again'}

    except ValidationError as e:
        error_message = e.messages[0].lower() if isinstance(e.messages, list) and e.messages else str(e).lower()
        audits_utilities.log_audit(actor=requesting_account, action='GRADE', target_model='ASSESSMENT', target_object_id=str(assessment.assessment_id) if assessment else 'N/A', outcome='ERROR', response=error_message, school=requesting_account.school)

        return {"error": error_message}

    except Exception as e:
        error_message = str(e)
        audits_utilities.log_audit(actor=requesting_account, action='GRADE', target_model='ASSESSMENT', target_object_id=str(assessment.assessment_id) if assessment else 'N/A', outcome='ERROR', response=error_message, school=requesting_account.school)

        return {'error': error_message}
    

@database_sync_to_async
def submit_attendance(user, role, details):
    try:
        classroom = None  # Initialize classroom as None to prevent issues in error handling

        requesting_user = BaseUser.objects.get(account_id=user)
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = users_utilities.get_account_and_linked_school(user, role)

        # Check if the user has permission to create an assessment
        if role != 'PRINCIPAL' and not permissions_utilities.has_permission(requesting_account, 'SUBMIT', 'ATTENDANCE'):
            response = f'could not proccess your request, you do not have the necessary permissions to grade assessments.'
            audits_utilities.log_audit(actor=requesting_account, action='SUBMIT', target_model='ATTENDANCE', outcome='DENIED', response=response, school=requesting_account.school)

            return {'error': response}

        classroom = Classroom.objects.get(classroom_id=details.get('class'), school=requesting_account.school, register_class=True)
        
        today = timezone.localdate()

        if details.get('absent'):
            if classroom.attendances.filter(date__date=today).exists():
                return {'error': 'attendance register for this class has already been subimitted today.. can not resubmit'}

            with transaction.atomic():
                register = Attendance.objects.create(submitted_by=requesting_user, classroom=classroom)

                if details.get('students'):
                    register.absentes = True
                    for student in details['students'].split(', '):
                        register.absent_students.add(Student.objects.get(account_id=student))

                register.save()
            
                response = 'attendance register successfully taken for today'
                audits_utilities.log_audit(actor=requesting_account, action='SUBMIT', target_model='ATTENDANCE', target_object_id=str(student.account_id) if student else 'N/A', outcome='SUBMITTED', response=response, school=requesting_account.school,)

        if details.get('late'):
            if not details.get('students'):
                return {"error" : 'invalid request.. no students were provided.. at least one student is needed to be marked as late'}

            absentes = classroom.attendances.prefetch_related('absent_students').filter(date__date=today).first()
            if not absentes:
                return {'error': 'attendance register for this class has not been submitted today.. can not submit late arrivals before the attendance register'}

            if not absentes.absent_students.exists():
                return {'error': 'todays attendance register for this class has all students accounted for'}

            register = Attendance.objects.filter(date__date=today, classroom=classroom).first()
            
            with transaction.atomic():
                if not register:
                    register = Attendance.objects.create(submitted_by=requesting_user, classroom=classroom)
                    
                for student in details['students'].split(', '):
                    student = Student.objects.get(account_id=student)
                    absentes.absent_students.remove(student)
                    register.late_students.add(student)

                absentes.save()
                register.save()

                response = 'students marked as late, attendance register successfully updated'
                audits_utilities.log_audit(actor=requesting_account, action='SUBMIT', target_model='ATTENDANCE', target_object_id=str(student.account_id) if student else 'N/A', outcome='SUBMITTED', response=response, school=requesting_account.school,)

        return {'message': response}

    except BaseUser.DoesNotExist:
        # Handle case where the user or teacher account does not exist
        return {'error': 'The account with the provided credentials does not exist. Please check the account details and try again.'}
    
    except Classroom.DoesNotExist:
        return { 'error': 'class with the provided credentials does not exist' }

    except ValidationError as e:
        error_message = e.messages[0].lower() if isinstance(e.messages, list) and e.messages else str(e).lower()
        audits_utilities.log_audit(actor=requesting_account, action='SUBMIT', target_model='ATTENDANCE', target_object_id=str(classroom.classroom_id) if classroom else 'N/A', outcome='ERROR', response=error_message, school=requesting_account.school)

        return {"error": error_message}

    except Exception as e:
        error_message = str(e)
        audits_utilities.log_audit(actor=requesting_account, action='SUBMIT', target_model='ATTENDANCE', target_object_id=str(classroom.classroom_id) if classroom else 'N/A', outcome='ERROR', response=error_message, school=requesting_account.school)

        return {'error': error_message}
    

@database_sync_to_async
def log_activity(user, role, details):
    try:
        activity = None
        requesting_user = BaseUser.objects.get(account_id=user)
        
        requested_account = None  # Initialize requested_account as None to prevent issues in error handling
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = users_utilities.get_account_and_attr(user, role)

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
                activity = Activity.objects.create(**serializer.validated_data)

                response = f'activity successfully logged. the activity is now available to everyone with access to the student\'s data.'
                audits_utilities.log_audit(actor=requesting_account, action='LOG', target_model='ACTIVITY', target_object_id=str(activity.activity_id), outcome='LOGGED', response=response, school=requesting_account.school)

            return {'message': response}

        error_response = '; '.join([f"{key}: {', '.join(value)}" for key, value in serializer.errors.items()])
        audits_utilities.log_audit(actor=requesting_account, action='LOG', target_model='ACTIVITY', outcome='ERROR', response=f'Validation failed: {error_response}', school=requesting_account.school)

        return {"error": error_response}

    except BaseUser.DoesNotExist:
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


@database_sync_to_async
def create_daily_schedule(user, role, details):
    try:
        daily_schedule = None  # Initialize daily schedule as None to prevent issues in error handling
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = users_utilities.get_account_and_attr(user, role)

        # Check if the user has permission to create a schedule
        if role != 'PRINCIPAL' and not permissions_utilities.has_permission(requesting_account, 'CREATE', 'DAILY_SCHEDULE'):
            response = 'Could not process your request, you do not have the necessary permissions to create schedules.'
            audits_utilities.log_audit(actor=requesting_account, action='CREATE', target_model='DAILY_SCHEDULE', outcome='DENIED', response=response, school=requesting_account.school)

            return {'error': response}

        if details.get('group_timetable'):
            group_timetable = StudentGroupTimetable.objects.get(group_timetable_id=details['group_timetable'], grade__school=requesting_account.school)
        
        elif details.get('teacher'):
            teacher = Teacher.objects.get(account_id=details['teacher'], school=requesting_account.school)

        else:
            response = 'Could not process your request, invalid information provided.'
            audits_utilities.log_audit(actor=requesting_account, action='CREATE', target_model='DAILY_SCHEDULE', outcome='ERROR', response=response, school=requesting_account.school)

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
                    start_time=parse_time(session_info['start_time']),
                    end_time=parse_time(session_info['end_time'])) for session_info in details.get('sessions', []
                )
            ]

            DailyScheduleSession.objects.bulk_create(sessions)
            daily_schedule.sessions.add(*sessions)
            
            if details.get('group'):
                group_timetable.daily_schedules.filter(day_of_week=day).delete()
                group_timetable.daily_schedules.add(daily_schedule)
                
                response = 'A new schedule has been added to the group\'s weekly schedules. All subscribed students should be able to view the sessions in the schedule when they check their timetables.'

            elif details.get('teacher'):
                teacher_timetable, created = TeacherTimetable.objects.get_or_create(teacher=teacher)
                if not created:
                    teacher_timetable.daily_schedules.filter(day_of_week=day).delete()
                teacher_timetable.daily_schedules.add(daily_schedule)

                response = 'A new schedule has been added to the teacher\'s weekly schedules. They should be able to view the sessions in the schedule when they check their timetable.'
                    
            audits_utilities.log_audit(actor=requesting_account, action='CREATE', target_model='DAILY_SCHEDULE', target_object_id=str(daily_schedule.daily_schedule_id) if daily_schedule else 'N/A', outcome='CREATED', response=response, school=requesting_account.school,)

        return {'message' : response}

    except Teacher.DoesNotExist:
        # Handle the case where the requested teacher account does not exist.
        return {'error': 'a teacher account with the provided credentials does not exist, please check the account details and try again'}

    except StudentGroupTimetable.DoesNotExist:
        # Handle the case where the requested student account does not exist.
        return {'error': 'a group timetable in your school with the provided credentials does not exist. please check the group details and try again.'}

    except ValidationError as e:
        error_message = e.messages[0].lower() if isinstance(e.messages, list) and e.messages else str(e).lower()
        audits_utilities.log_audit(actor=requesting_account, action='CREATE', target_model='DAILY_SCHEDULE', target_object_id=str(daily_schedule.daily_schedule_id) if daily_schedule else 'N/A', outcome='ERROR', response=error_message, school=requesting_account.school)

        return {"error": error_message}

    except Exception as e:
        error_message = str(e)
        audits_utilities.log_audit(actor=requesting_account, action='CREATE', target_model='DAILY_SCHEDULE', target_object_id=str(daily_schedule.daily_schedule_id) if daily_schedule else 'N/A', outcome='ERROR', response=error_message, school=requesting_account.school)

        return {'error': error_message}


@database_sync_to_async
def delete_daily_schedule(user, role, details):
    try:
        daily_schedule = None  # Initialize schedule as None to prevent issues in error handling
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = users_utilities.get_account_and_linked_school(user, role)

        # Check if the user has permission to create a group schedule
        if role != 'PRINCIPAL' and not permissions_utilities.has_permission(requesting_account, 'DELETE', 'DAILY_SCHEDULE'):
            response = 'Could not process your request, you do not have the necessary permissions to delete daily schedules.'
            audits_utilities.log_audit(actor=requesting_account, action='DELETE', target_model='DAILY_SCHEDULE', outcome='DENIED', response=response, school=requesting_account.school)

            return {'error': response}

        if details.get('group'):
            daily_schedule = DailySchedule.objects.get(daily_schedule_id=details.get('schedule'), student_group_timetable__grade__school=requesting_account.school)
            response = 'the schedule has been successfully deleted from the group schedule and will be removed from schedules of all students subscribed to the group schedule'
            
        if details.get('teacher'):
            daily_schedule = DailySchedule.objects.get(daily_schedule_id=details.get('schedule'), teacher_timetable__teacher__school=requesting_account.school)
            response = 'the schedule has been successfully deleted from the teachers schedule and will no longer be available to the teacher'
            
        else:
            response = 'could not process your request, the provided type is invalid'

            audits_utilities.log_audit(actor=requesting_account, action='DELETE', target_model='DAILY_SCHEDULE', outcome='DENIED', response=response, school=requesting_account.school)

            return {"error": response}
        
        with transaction.atomic():
            audits_utilities.log_audit(actor=requesting_account, action='DELETE', target_model='DAILY_SCHEDULE', target_object_id=str(daily_schedule.daily_schedule_id), outcome='DELETED', response=response, school=requesting_account.school)

            daily_schedule.delete()

        return {'message': response}

    except DailySchedule.DoesNotExist:
        # Handle the case where the provided schedule_id does not exist
        return {'error': 'a schedule for your school with the provided credentials does not exist. please verify the details and try again.'}

    except ValidationError as e:
        error_message = e.messages[0].lower() if isinstance(e.messages, list) and e.messages else str(e).lower()
        audits_utilities.log_audit(actor=requesting_account, action='DELETE', target_model='DAILY_SCHEDULE', target_object_id=str(daily_schedule.daily_schedule_id) if daily_schedule else 'N/A', outcome='ERROR', response=error_message, school=requesting_account.school)

        return {"error": error_message}

    except Exception as e:
        error_message = str(e)
        audits_utilities.log_audit(actor=requesting_account, action='DELETE', target_model='DAILY_SCHEDULE', target_object_id=str(daily_schedule.daily_schedule_id) if daily_schedule else 'N/A', outcome='ERROR', response=error_message, school=requesting_account.school)

        return {'error': error_message}


@database_sync_to_async
def create_group_timetable(user, role, details):
    try:
        group_timetable = None  # Initialize group timetable as None to prevent issues in error handling
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = users_utilities.get_account_and_linked_school(user, role)

        # Check if the user has permission to create a group schedule
        if role != 'PRINCIPAL' and not permissions_utilities.has_permission(requesting_account, 'CREATE', 'GROUP_TIMETABLE'):
            response = 'Could not process your request, you do not have the necessary permissions to create group timetables.'
            audits_utilities.log_audit(actor=requesting_account, action='CREATE', target_model='GROUP_TIMETABLE', outcome='DENIED', response=response, school=requesting_account.school)

            return {'error': response}

        grade = Grade.objects.get(grade_id=details.get('grade'), school=requesting_account.school)
        details['grade'] = grade.pk

        serializer = StudentGroupScheduleCreationSerializer(data=details)
        if serializer.is_valid():
            with transaction.atomic():
                group_timetable = StudentGroupTimetable.objects.create(**serializer.validated_data)
                response = 'You can now add individual daily schedules and subscribe students in the grade to the group timetable for a shared weekly schedule.'
            
                audits_utilities.log_audit(actor=requesting_account, action='CREATE', target_model='GROUP_TIMETABLE', target_object_id=str(group_timetable.group_timetable_id), outcome='CREATED', response=response, school=requesting_account.school,)

            return {'message': response}

        error_response = '; '.join([f"{key}: {', '.join(value)}" for key, value in serializer.errors.items()])
        audits_utilities.log_audit(actor=requesting_account, action='CREATE', target_model='GROUP_TIMETABLE', target_object_id=str(group_timetable.group_timetable_id) if group_timetable else 'N/A', outcome='ERROR', response=f'Validation failed: {error_response}', school=requesting_account.school)

        return {"error": error_response}

    except Grade.DoesNotExist:
        # Handle the case where the requested grade does not exist.
        return {'error': 'A grade in your school with the provided credentials does not exist. Please check the grade details and try again.'}

    except ValidationError as e:
        error_message = e.messages[0].lower() if isinstance(e.messages, list) and e.messages else str(e).lower()
        audits_utilities.log_audit(actor=requesting_account, action='CREATE', target_model='GROUP_TIMETABLE', target_object_id=str(group_timetable.group_timetable_id) if group_timetable else 'N/A', outcome='ERROR', response=error_message, school=requesting_account.school)

        return {"error": error_message}

    except Exception as e:
        error_message = str(e)
        audits_utilities.log_audit(actor=requesting_account, action='CREATE', target_model='GROUP_TIMETABLE', target_object_id=str(group_timetable.group_timetable_id) if group_timetable else 'N/A', outcome='ERROR', response=error_message, school=requesting_account.school)

        return {'error': error_message}


@database_sync_to_async
def delete_group_schedule(user, role, details):
    try:
        group_timtable = None  # Initialize group timtable as None to prevent issues in error handling
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = users_utilities.get_account_and_linked_school(user, role)

        # Check if the user has permission to create a group schedule
        if role != 'PRINCIPAL' and not permissions_utilities.has_permission(requesting_account, 'DELETE', 'GROUP_TIMETABLE'):
            response = 'could not process your request, you do not have the necessary permissions to delete group timetables.'
            audits_utilities.log_audit(actor=requesting_account, action='DELETE', target_model='GROUP_TIMETABLE', outcome='DENIED', response=response, school=requesting_account.school)

            return {'error': response}

        group_timtable = StudentGroupTimetable.objects.select_related('grade').get(group_timetable_id=details.get('group_schedule'), grade__school=requesting_account.school)
        
        with transaction.atomic():
            response = f'grade {group_timtable.grade.grade} group timetable {group_timtable.group_name} has been successfully deleted'
            audits_utilities.log_audit(actor=requesting_account,action='DELETE', target_model='GROUP_TIMETABLE', target_object_id=str(group_timtable.group_timetable_id), outcome='DELETED', response=response, school=requesting_account.school)

            group_timtable.delete()

        return {'message': response}

    except StudentGroupTimetable.DoesNotExist:
        # Handle case where group schedule does not exist
        return {'error': 'a group timetable for your school with the provided credentials does not exist, please check the group details and try again'}

    except ValidationError as e:
        error_message = e.messages[0].lower() if isinstance(e.messages, list) and e.messages else str(e).lower()
        audits_utilities.log_audit(actor=requesting_account, action='DELETE', target_model='GROUP_TIMETABLE', target_object_id=str(group_timtable.group_timetable_id) if group_timtable else 'N/A', outcome='ERROR', response=error_message, school=requesting_account.school)

        return {"error": error_message}

    except Exception as e:
        error_message = str(e)
        audits_utilities.log_audit(actor=requesting_account, action='DELETE', target_model='GROUP_TIMETABLE', target_object_id=str(group_timtable.group_timetable_id) if group_timtable else 'N/A', outcome='ERROR', response=error_message, school=requesting_account.school)

        return {'error': error_message}


@database_sync_to_async
def announce(user, role, details):
    try:
        announcement = None  # Initialize requested_account as None to prevent issues in error handling
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = users_utilities.get_account_and_linked_school(user, role)

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
    