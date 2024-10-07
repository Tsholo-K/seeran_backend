# channels
from channels.db import database_sync_to_async

# django
from django.db import transaction
from django.core.exceptions import ValidationError

# models 
from accounts.models import BaseAccount, Student
from permission_groups.models import AdminPermissionGroup, TeacherPermissionGroup
from grades.models import Grade
from terms.models import Term
from subjects.models import Subject
from classrooms.models import Classroom
from assessments.models import Assessment
from topics.models import Topic
from student_group_timetables.models import StudentGroupTimetable

# serilializers
from permission_groups.serializers import AdminPermissionGroupUpdatenSerializer, TeacherPermissionGroupUpdateSerializer
from grades.serializers import UpdateGradeSerializer, GradeDetailsSerializer
from schools.serializers import UpdateSchoolAccountSerializer, SchoolDetailsSerializer
from terms.serializers import UpdateTermSerializer, TermSerializer
from subjects.serializers import UpdateSubjectSerializer, SubjectDetailsSerializer
from classrooms.serializers import UpdateClassroomSerializer, ClassroomDetailsSerializer
from assessments.serializers import DueAssessmentUpdateSerializer, CollectAssessmentUpdateSerializer, GradesReleasedAssessmentUpdateSerializer
from assessment_transcripts.serializers import TranscriptUpdateSerializer
from student_group_timetables.serializers import StudentGroupTimetableDetailsSerializer, StudentGroupTimetableUpdateSerializer

# checks
from accounts.checks import permission_checks

# mappings
from accounts.mappings import serializer_mappings

# utility functions 
from accounts import utils as accounts_utilities
from account_permissions import utils as permissions_utilities
from audit_logs import utils as audits_utilities

# tasks
from assessments.tasks import release_grades_task


@database_sync_to_async
def update_school_account_details(user, role, details):
    try:
        school = None  # Initialize requested_account as None to prevent issues in error handling
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = accounts_utilities.get_account_and_linked_school(user, role)
        
        school = requesting_account.school

        # Check if the user has permission to update classrooms
        if role != 'PRINCIPAL' and not permissions_utilities.has_permission(requesting_account, 'UPDATE', 'ACCOUNT'):
            response = f'could not proccess your request, you do not have the necessary permissions to update account details.'
            audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='ACCOUNT', outcome='DENIED', server_response=response, school=school)

            return {'error': response}

        # Initialize the serializer with the existing school instance and incoming data
        serializer = UpdateSchoolAccountSerializer(school, data=details)
        # Validate the incoming data
        if serializer.is_valid():
            # Use an atomic transaction to ensure the database is updated safely
            with transaction.atomic():
                serializer.save()
                    
                response = f"School account details have been successfully updated. The following information has been changed: {', '.join(details.keys())}."
                audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='ACCOUNT', target_object_id=str(school.school_id), outcome='UPDATED', server_response=response, school=school)

            # Serialize the grade
            serialized_school = SchoolDetailsSerializer(school).data

            return {'school': serialized_school, "message": response}
            
        # Return serializer errors if the data is not valid, format it as a string
        error_response = '; '.join([f"{key}: {', '.join(value)}" for key, value in serializer.errors.items()])
        audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='ACCOUNT', target_object_id=str(school.school_id), outcome='ERROR', server_response=f'Validation failed: {error_response}', school=school)
        return {"error": error_response}

    except ValidationError as e:
        error_message = e.messages[0].lower() if isinstance(e.messages, list) and e.messages else str(e).lower()
        audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='ACCOUNT', target_object_id=str(school.school_id), outcome='ERROR', server_response=error_message, school=school)
        return {"error": error_message}

    except Exception as e:
        error_message = str(e)
        audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='ACCOUNT', target_object_id=str(school.school_id), outcome='ERROR', server_response=error_message, school=school)
        return {'error': error_message}


@database_sync_to_async
def update_permission_group_details(account, role, details):
    try:
        permission_group = None  # Initialize permission group as None to prevent issues in error handling

        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = accounts_utilities.get_account_and_linked_school(account, role)

        # Check if the user has permission to update classrooms
        if role != 'PRINCIPAL' and not permissions_utilities.has_permission(requesting_account, 'UPDATE', 'PERMISSION'):
            response = f'could not proccess your request, you do not have the necessary permissions to update classroom details.'
            audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='PERMISSION', outcome='DENIED', server_response=response, school=requesting_account.school)

            return {'error': response}

        if not {'permission_group', 'group'}.issubset(details) or details['group'] not in ['admins', 'teachers']:
            response = f'Could not proccess your request, the provided information is invalid for the action you are trying to perform. Please make sure to provide a valid group ID and group filter (admin or teacher) for which to filter the permission groups and try again'
            audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='PERMISSION', outcome='ERROR', server_response=response, school=requesting_account.school)
            return {'error': response}
        
        # Determine the group type based on the role
        if details['group'] == 'admins':
            permission_group = requesting_account.school.admin_permission_groups.get(permission_group_id=details['permission_group'])
            serializer = AdminPermissionGroupUpdatenSerializer(permission_group, data=details)
      
        else:
            permission_group = requesting_account.school.teacher_permission_groups.get(permission_group_id=details['permission_group'])
            serializer = TeacherPermissionGroupUpdateSerializer(permission_group, data=details)

        # Validate the incoming data
        if serializer.is_valid():
            with transaction.atomic():
                serializer.save()
                
                response = f"Accounts successfully {'unsubscribed from' if details.get('subscribe') else 'subscribed to'} the permission group"
                audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='PERMISSION', target_object_id=str(permission_group.permission_group_id), outcome='UPDATED', server_response=response, school=requesting_account.school,)

            return {"message": response}
        
        # Return serializer errors if the data is not valid, format it as a string
        error_response = '; '.join([f"{key}: {', '.join(value)}" for key, value in serializer.errors.items()])
        audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='PERMISSION', target_object_id=str(permission_group.permission_group_id), outcome='ERROR', server_response=f'Validation failed: {error_response}', school=requesting_account.school)

        return {"error": error_response}

    except AdminPermissionGroup.DoesNotExist:
        # Handle the case where the provided grade ID does not exist
        return { 'error': 'Could not process your request, a admin permission group in your school with the provided credentials does not exist. Please review the group details and try again.'}
    
    except TeacherPermissionGroup.DoesNotExist:
        # Handle the case where the provided grade ID does not exist
        return { 'error': 'Could not process your request, a teacher permission group  in your school with the provided credentials does not exist. Please review the group details and try again.'}

    except ValidationError as e:
        error_message = e.messages[0].lower() if isinstance(e.messages, list) and e.messages else str(e).lower()
        audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='PERMISSION', target_object_id=str(permission_group.permission_group_id), outcome='ERROR', server_response=error_message, school=requesting_account.school)

        return {"error": error_message}

    except Exception as e:
        error_message = str(e)
        audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='PERMISSION', target_object_id=str(permission_group.permission_group_id), outcome='ERROR', server_response=error_message, school=requesting_account.school)

        return {'error': error_message}


@database_sync_to_async
def update_permission_group_subscribers(account, role, details):
    try:
        subscribers_list = details.get('subscribers', '').split(', ')
        if not subscribers_list or subscribers_list == ['']:
            return {'error': 'your request could not be proccessed.. no subscribers were provided'}
        
        permission_group = None  # Initialize permission group as None to prevent issues in error handling

        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = accounts_utilities.get_account_and_linked_school(account, role)

        # Check if the user has permission to update classrooms
        if role != 'PRINCIPAL' and not permissions_utilities.has_permission(requesting_account, 'UPDATE', 'PERMISSION'):
            response = f'could not proccess your request, you do not have the necessary permissions to update classroom details.'
            audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='PERMISSION', outcome='DENIED', server_response=response, school=requesting_account.school)

            return {'error': response}

        if not {'permission_group', 'group'}.issubset(details) or details['group'] not in ['admins', 'teachers']:
            response = f'Could not proccess your request, the provided information is invalid for the action you are trying to perform. Please make sure to provide a valid group ID and group filter (admin or teacher) for which to filter the permission groups and try again'
            audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='PERMISSION', outcome='ERROR', server_response=response, school=requesting_account.school)
            return {'error': response}
        
        # Determine the group type based on the role
        if details['group'] == 'admins':
            permission_group = requesting_account.school.admin_permission_groups.get(permission_group_id=details['permission_group'])
      
        else:
            permission_group = requesting_account.school.teacher_permission_groups.get(permission_group_id=details['permission_group'])

        with transaction.atomic():
            # Check for validation errors and perform student updates
            permission_group.update_subscribers(subscribers_list=subscribers_list, subscribe=details.get('subscribe'))
            
            response = f"The provided {'teacher' if details['group'] == 'admins' else 'admin'} {'accounts have' if len(subscribers_list) > 1 else 'account has'} been successfully {'subscribed to' if details.get('subscribe') else 'unsubscribed from'} the permission group. {'Accounts' if len(subscribers_list) > 1 else 'Account'} with the following accound {'IDs' if len(subscribers_list) > 1 else 'ID'}: {', '.join(subscribers_list)} will {'gain' if details.get('subscribe') else 'lose'} all permissions attached to this permission group, effactive immediately."
            audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='PERMISSION', target_object_id=str(permission_group.permission_group_id) if permission_group else 'N/A', outcome='UPDATED', server_response=response, school=requesting_account.school,)

        return {"message": response}
    
    except AdminPermissionGroup.DoesNotExist:
        # Handle the case where the provided grade ID does not exist
        return { 'error': 'Could not process your request, a admin permission group in your school with the provided credentials does not exist. Please review the group details and try again.'}
    
    except TeacherPermissionGroup.DoesNotExist:
        # Handle the case where the provided grade ID does not exist
        return { 'error': 'Could not process your request, a teacher permission group  in your school with the provided credentials does not exist. Please review the group details and try again.'}

    except ValidationError as e:
        error_message = e.messages[0].lower() if isinstance(e.messages, list) and e.messages else str(e).lower()
        audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='PERMISSION', target_object_id=str(permission_group.permission_group_id) if permission_group else 'N/A', outcome='ERROR', server_response=error_message, school=requesting_account.school)

        return {"error": error_message}

    except Exception as e:
        error_message = str(e)
        audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='PERMISSION', target_object_id=str(permission_group.permission_group_id) if permission_group else 'N/A', outcome='ERROR', server_response=error_message, school=requesting_account.school)

        return {'error': error_message}


@database_sync_to_async
def update_account_details(user, role, details):
    try:
        if details.get('role') not in ['ADMIN', 'TEACHER', 'STUDENT', 'PARENT']:
            return {"error": 'could not proccess your request, the provided account role is invalid'}

        requested_account = None  # Initialize requested_account as None to prevent issues in error handling

        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = accounts_utilities.get_account_and_linked_school(user, role)

        # Check if the user has permission to update classrooms
        if role != 'PRINCIPAL' and not permissions_utilities.has_permission(requesting_account, 'UPDATE', 'ACCOUNT'):
            response = f'could not proccess your request, you do not have the necessary permissions to update classroom details.'
            audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='ACCOUNT', outcome='DENIED', response=response, school=requesting_account.school)

            return {'error': response}

        if details['role'] == 'ADMIN' and role == 'ADMIN':
            response = f'could not proccess your request, your accounts role does not have enough permissions to perform this action.'

            audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='ACCOUNT', outcome='DENIED', response=response, school=requesting_account.school)

            return {'error': response}

        # Retrieve the requested user's account and related attr for permission check
        requested_account = accounts_utilities.get_account_and_permission_check_attr(details['account'], details['role'])
        
        # Check if the requesting user has permission to view the requested user's profile.
        permission_error = permission_checks.check_update_details_permissions(requesting_account, requested_account)
        if permission_error:
            return permission_error
        
        # Get the appropriate serializer
        Serializer = serializer_mappings.account_update[details['role']]

        # Serialize the requested user's profile for returning in the response.
        serializer = Serializer(instance=requested_account, data=details['updates'])
        if serializer.is_valid():
            with transaction.atomic():
                serializer.save()
                        
                response = f'account details successfully updated'
                audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='ACCOUNT', target_object_id=str(requested_account.account_id) if requested_account else 'N/A', outcome='UPDATED', response=response, school=requesting_account.school,)
            
            # Get the appropriate serializer
            Serializer = accounts_utilities.account_details_serializer_mapping[details['role']]

            # Serialize the requested user's profile for returning in the response.
            serialized_user = Serializer(instance=requested_account).data

            return {"user" : serialized_user}

        # Return serializer errors if the data is not valid, format it as a string
        error_response = '; '.join([f"{key}: {', '.join(value)}" for key, value in serializer.errors.items()])
        audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='ACCOUNT', target_object_id=str(requested_account.account_id) if requested_account else 'N/A', outcome='ERROR', response=f'Validation failed: {error_response}', school=requesting_account.school)

        return {"error": error_response}

    except ValidationError as e:
        error_message = e.messages[0].lower() if isinstance(e.messages, list) and e.messages else str(e).lower()
        audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='ACCOUNT', target_object_id=str(requested_account.account_id) if requested_account else 'N/A', outcome='ERROR', response=error_message, school=requesting_account.school)

        return {"error": error_message}

    except Exception as e:
        error_message = str(e)
        audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='ACCOUNT', target_object_id=str(requested_account.account_id) if requested_account else 'N/A', outcome='ERROR', response=error_message, school=requesting_account.school)

        return {'error': error_message}


@database_sync_to_async
def update_grade_details(user, role, details):
    try:
        grade = None  # Initialize grade as None to prevent issues in error handling
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = accounts_utilities.get_account_and_linked_school(user, role)

        # Check if the user has permission to update grades
        if role != 'PRINCIPAL' and not permissions_utilities.has_permission(requesting_account, 'UPDATE', 'GRADE'):
            response = f'could not proccess your request, you do not have the necessary permissions to update grade details.'
            audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='GRADE', outcome='DENIED', server_response=response, school=requesting_account.school)

            return {'error': response}

        grade = Grade.objects.get(grade_id=details.get('grade'), school=requesting_account.school)

        # Initialize the serializer with the existing school instance and incoming data
        serializer = UpdateGradeSerializer(instance=grade, data=details)
        if serializer.is_valid():
            with transaction.atomic():
                serializer.save()
                    
                response = f"grade details have been successfully updated"
                audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='GRADE', target_object_id=str(grade.grade_id) if grade else 'N/A', outcome='UPDATED', server_response=response, school=requesting_account.school,)

            # Serialize the grade
            serialized_grade = GradeDetailsSerializer(grade).data
            
            # Return the serialized grade in a dictionary
            return {'grade': serialized_grade, "message": response}
            
        # Return serializer errors if the data is not valid, format it as a string
        error_response = '; '.join([f"{key}: {', '.join(value)}" for key, value in serializer.errors.items()])
        audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='GRADE', target_object_id=str(grade.grade_id) if grade else 'N/A', outcome='ERROR', server_response=f'Validation failed: {error_response}', school=requesting_account.school)

        return {"error": error_response}
                       
    except Grade.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'an grade for your school with the provided credentials does not exist, please check the grade details and try again'}

    except ValidationError as e:
        error_message = e.messages[0].lower() if isinstance(e.messages, list) and e.messages else str(e).lower()
        audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='GRADE', target_object_id=str(grade.grade_id) if grade else 'N/A', outcome='ERROR', server_response=error_message, school=requesting_account.school)

        return {"error": error_message}

    except Exception as e:
        error_message = str(e)
        audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='GRADE', target_object_id=str(grade.grade_id) if grade else 'N/A', outcome='ERROR', server_response=error_message, school=requesting_account.school)

        return {'error': error_message}


@database_sync_to_async
def update_subject_details(user, role, details):
    try:
        subject = None  # Initialize subject as None to prevent issues in error handling
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = accounts_utilities.get_account_and_linked_school(user, role)

        # Check if the user has permission to update classrooms
        if role != 'PRINCIPAL' and not permissions_utilities.has_permission(requesting_account, 'UPDATE', 'SUBJECT'):
            response = f'could not proccess your request, you do not have the necessary permissions to update subject details.'
            audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='SUBJECT', outcome='DENIED', server_response=response, school=requesting_account.school)

            return {'error': response}

        if 'subject' not in details:
            response = f'Could not proccess your request, the provided information is invalid for the action you are trying to perform. please make sure to provide a valid subject ID and try again.'
            audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='SUBJECT', outcome='ERROR', server_response=response, school=requesting_account.school)
            return {'error': response}

        subject = requesting_account.school.subjects.get(subject_id=details['subject'])

        # Initialize the serializer with the existing school instance and incoming data
        serializer = UpdateSubjectSerializer(instance=subject, data=details)
        # Validate the incoming data
        if serializer.is_valid():
            # Use an atomic transaction to ensure the database is updated safely
            with transaction.atomic():
                serializer.save()
                    
                response = f"The details of a subject in your school with subject ID: {subject.subject_id}, have been successfully updated."
                audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='SUBJECT', target_object_id=str(subject.subject_id) if subject else 'N/A', outcome='UPDATED', server_response=response, school=requesting_account.school,)
            
            # Serialize the subject
            serialized_subject = SubjectDetailsSerializer(subject).data

            # Return the serialized grade in a dictionary
            return {'subject': serialized_subject, "message": response}
            
        # Return serializer errors if the data is not valid, format it as a string
        error_response = '; '.join([f"{key}: {', '.join(value)}" for key, value in serializer.errors.items()])
        audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='SUBJECT', target_object_id=str(subject.subject_id) if subject else 'N/A', outcome='ERROR', server_response=f'Validation failed: {error_response}', school=requesting_account.school)

        return {"error": error_response}
        
    except Subject.DoesNotExist:
        # Handle case where the subject does not exist
        return {'error': 'a subject in your school with the provided credentials does not exist.'}

    except ValidationError as e:
        error_message = e.messages[0].lower() if isinstance(e.messages, list) and e.messages else str(e).lower()
        audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='SUBJECT', target_object_id=str(subject.subject_id) if subject else 'N/A', outcome='ERROR', server_response=error_message, school=requesting_account.school)
        return {"error": error_message}

    except Exception as e:
        error_message = str(e)
        audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='SUBJECT', target_object_id=str(subject.subject_id) if subject else 'N/A', outcome='ERROR', server_response=error_message, school=requesting_account.school)
        return {'error': error_message}


@database_sync_to_async
def update_term_details(user, role, details):
    try:
        term = None  # Initialize term as None to prevent issues in error handling
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = accounts_utilities.get_account_and_linked_school(user, role)

        # Check if the user has permission to update terms
        if role != 'PRINCIPAL' and not permissions_utilities.has_permission(requesting_account, 'UPDATE', 'TERM'):
            response = f'could not proccess your request, you do not have the necessary permissions to update term details.'
            audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='TERM', outcome='DENIED', response=response, school=requesting_account.school)

            return {'error': response}

        term = Term.objects.get(term_id=details.get('term'), school=requesting_account.school)

        # Initialize the serializer with the existing school instance and incoming data
        serializer = UpdateTermSerializer(instance=term, data=details)
        # Validate the incoming data
        if serializer.is_valid():
            # Use an atomic transaction to ensure the database is updated safely
            with transaction.atomic():
                serializer.save()
                    
                response = f"school term details have been successfully updated"
                audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='TERM', target_object_id=str(term.term_id) if term else 'N/A', outcome='UPDATED', response=response, school=requesting_account.school,)

            # Serialize the school terms
            serialized_term = TermSerializer(term).data

            return {'term': serialized_term, "message": response}
            
        # Return serializer errors if the data is not valid, format it as a string
        error_response = '; '.join([f"{key}: {', '.join(value)}" for key, value in serializer.errors.items()])
        audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='TERM', target_object_id=str(term.term_id) if term else 'N/A', outcome='ERROR', response=f'Validation failed: {error_response}', school=requesting_account.school)

        return {"error": error_response}
                       
    except Term.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'a term for your school with the provided credentials does not exist, please check the term details and try again'}

    except ValidationError as e:
        error_message = e.messages[0].lower() if isinstance(e.messages, list) and e.messages else str(e).lower()
        audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='TERM', target_object_id=str(term.term_id) if term else 'N/A', outcome='ERROR', response=error_message, school=requesting_account.school)

        return {"error": error_message}

    except Exception as e:
        error_message = str(e)
        audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='TERM', target_object_id=str(term.term_id) if term else 'N/A', outcome='ERROR', response=error_message, school=requesting_account.school)

        return {'error': error_message}


@database_sync_to_async
def update_classroom_details(account, role, details):
    try:
        classroom = None  # Initialize classroom as None to prevent issues in error handling
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = accounts_utilities.get_account_and_linked_school(account, role)

        # Check if the user has permission to update classrooms
        if role != 'PRINCIPAL' and not permissions_utilities.has_permission(requesting_account, 'UPDATE', 'CLASSROOM'):
            response = f'could not proccess your request, you do not have the necessary permissions to update classroom details.'
            audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='CLASSROOM', outcome='DENIED', response=response, school=requesting_account.school)

            return {'error': response}

        if not 'classroom' in details:
            response = f'could not proccess your request, the provided information is invalid for the action you are trying to perform. please make sure to provide valid classroom ID and try again'
            audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='CLASSROOM', outcome='ERROR', server_response=response, school=requesting_account.school)
            return {'error': response}

        classroom = requesting_account.school.classrooms.get(classroom_id=details['classroom'])

        serializer = UpdateClassroomSerializer(classroom, data=details.get('updates'))
        if serializer.is_valid():
            with transaction.atomic():
                serializer.save()
                    
                response = f'A classroom in your school with classroom ID: {classroom.classroom_id}, has had it\'s details successfully updated.'
                audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='CLASSROOM', target_object_id=str(classroom.classroom_id) if classroom else 'N/A', outcome='UPDATED', server_response=response, school=requesting_account.school,)
            
            serialized_classroom = ClassroomDetailsSerializer(classroom).data

            return {"message": response, 'classroom': serialized_classroom}
            
        # Return serializer errors if the data is not valid, format it as a string
        error_response = '; '.join([f"{key}: {', '.join(value)}" for key, value in serializer.errors.items()])
        audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='CLASSROOM', target_object_id=str(classroom.classroom_id) if classroom else 'N/A', outcome='ERROR', server_response=f'Validation failed: {error_response}', school=requesting_account.school)
        return {"error": error_response}
    
    except Classroom.DoesNotExist:
        # Handle case where the classroom does not exist
        return {'error': 'a classroom in your school with the provided credentials does not exist. please check the classroom details and try again.'}

    except ValidationError as e:
        error_message = e.messages[0].lower() if isinstance(e.messages, list) and e.messages else str(e).lower()
        audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='CLASSROOM', target_object_id=str(classroom.classroom_id) if classroom else 'N/A', outcome='ERROR', server_response=error_message, school=requesting_account.school)
        return {"error": error_message}

    except Exception as e:
        error_message = str(e)
        audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='CLASSROOM', target_object_id=str(classroom.classroom_id) if classroom else 'N/A', outcome='ERROR', server_response=error_message, school=requesting_account.school)
        return {'error': error_message}


@database_sync_to_async
def update_classroom_teacher(account, role, details):
    try:
        classroom = None  # Initialize classroom as None to prevent issues in error handling
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = accounts_utilities.get_account_and_linked_school(account, role)

        # Check if the user has permission to update classrooms
        if role != 'PRINCIPAL' and not permissions_utilities.has_permission(requesting_account, 'UPDATE', 'CLASSROOM'):
            response = f'could not proccess your request, you do not have the necessary permissions to update classroom details.'
            audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='CLASSROOM', outcome='DENIED', server_responseserver_response=response, school=requesting_account.school)

            return {'error': response}

        if not 'classroom' in details or  not 'teacher' in details:
            response = f'could not proccess your request, the provided information is invalid for the action you are trying to perform. please make sure to provide valid classroom and teacher IDs and try again'
            audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='CLASSROOM', outcome='ERROR', server_response=response, school=requesting_account.school)
            return {'error': response}

        classroom = requesting_account.school.classrooms.get(classroom_id=details['classroom'])

        with transaction.atomic():
            if details['teacher'] == 'remove teacher':
                classroom.update_teacher(teacher=None)
            else:
                classroom.update_teacher(teacher=details['teacher'])
                
            response = f'Classroom teacher has been successfully updated.'
            audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='CLASSROOM', target_object_id=str(classroom.classroom_id) if classroom else 'N/A', outcome='UPDATED', server_response=response, school=requesting_account.school,)

        return {"message": response}
            
    except Classroom.DoesNotExist:
        # Handle case where the classroom does not exist
        return {'error': 'a classroom in your school with the provided credentials does not exist. please check the classroom details and try again.'}

    except ValidationError as e:
        error_message = e.messages[0].lower() if isinstance(e.messages, list) and e.messages else str(e).lower()
        audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='CLASSROOM', target_object_id=str(classroom.classroom_id) if classroom else 'N/A', outcome='ERROR', server_response=error_message, school=requesting_account.school)
        return {"error": error_message}

    except Exception as e:
        error_message = str(e)
        audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='CLASSROOM', target_object_id=str(classroom.classroom_id) if classroom else 'N/A', outcome='ERROR', server_response=error_message, school=requesting_account.school)
        return {'error': error_message}


@database_sync_to_async
def update_classroom_students(account, role, details):
    try:
        students = details.get('students', '').split(', ')
        if not students or students == ['']:
            return {'error': 'your request could not be proccessed.. no students were provided'}
        
        classroom = None  # Initialize assessment as None to prevent issues in error handling

        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = accounts_utilities.get_account_and_linked_school(account, role)

        # Check if the user has permission to update classrooms
        if role != 'PRINCIPAL' and not permissions_utilities.has_permission(requesting_account, 'UPDATE', 'CLASSROOM'):
            response = f'could not proccess your request, you do not have the necessary permissions to update classroom details.'
            audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='CLASSROOM', outcome='DENIED', server_response=response, school=requesting_account.school)
            return {'error': response}

        if not 'classroom' in details:
            response = f'could not proccess your request, the provided information is invalid for the action you are trying to perform. please make sure to provide valid classroom ID and try again'
            audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='CLASSROOM', outcome='ERROR', server_response=response, school=requesting_account.school)
            return {'error': response}

        classroom = requesting_account.school.classrooms.select_related('grade', 'subject').get(classroom_id=details['classroom'])

        with transaction.atomic():
            # Check for validation errors and perform student updates
            classroom.update_students(students=students, remove=details.get('remove'))

            response = f'{"Students" if len(students) > 1  else "Student"} with the following account {"IDs" if len(students) > 1  else "ID"}: {", ".join(students)}, {"have" if len(students) > 1  else "has"} been successfully {"removed from" if details.get("remove") else "added to"} the grade {classroom.grade.grade}, group {classroom.group} {"register" if classroom.register_classroom else classroom.subject.subject.lower()} classroom'
            audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='CLASSROOM', target_object_id=str(classroom.classroom_id) if classroom else 'N/A', outcome='UPDATED', server_response=response, school=requesting_account.school,)

        return {"message": response}
    
    except Classroom.DoesNotExist:
        # Handle case where the classroom does not exist
        return {'error': 'Could not process your request, a classroom in your school with the provided credentials does not exist. Please review the classroom details and try again.'}

    except ValidationError as e:
        error_message = e.messages[0].lower() if isinstance(e.messages, list) and e.messages else str(e).lower()
        audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='CLASSROOM', target_object_id=str(classroom.classroom_id) if classroom else 'N/A', outcome='ERROR', server_response=error_message, school=requesting_account.school)
        return {"error": error_message}

    except Exception as e:
        error_message = str(e)
        audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='CLASSROOM', target_object_id=str(classroom.classroom_id) if classroom else 'N/A', outcome='ERROR', server_response=error_message, school=requesting_account.school)
        return {'error': error_message}


@database_sync_to_async
def update_assessment(user, role, details):
    try:
        assessment = None  # Initialize assessment as None to prevent issues in error handling
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = accounts_utilities.get_account_and_linked_school(user, role)

        # Check if the user has permission to update an assessment
        if role != 'PRINCIPAL' and not permissions_utilities.has_permission(requesting_account, 'UPDATE', 'ASSESSMENT'):
            response = f'could not proccess your request, you do not have the necessary permissions to update assessments.'
            audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='ASSESSMENT', outcome='DENIED', server_response=response, school=requesting_account.school)

            return {'error': response}
        
        if 'assessment' not in details:
            response = f'could not proccess your request, the provided information is invalid for the action you are trying to perform. please make sure to provide a valid assessment ID and try again'
            audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='ASSESSMENT', outcome='ERROR', server_response=response, school=requesting_account.school)
            return {'error': response}

        assessment = requesting_account.school.assessments.get(assessment_id=details['assessment'])

        topics = None
        # Serialize the details for assessment creation
        if assessment.grades_released:
            serializer = GradesReleasedAssessmentUpdateSerializer(instance=assessment, data=details)
        else:
            if details.get('moderator'):
                if details['moderator'] == 'remove current moderator':
                    details['moderator'] = None
                else:
                    moderator = BaseAccount.objects.only('id').get(account_id=details['moderator'])
                    details['moderator'] = moderator.id

            if assessment.collected:
                serializer = CollectAssessmentUpdateSerializer(instance=assessment, data=details)
            else:
                serializer = DueAssessmentUpdateSerializer(instance=assessment, data=details)
                if details.get('topics'):
                    for name in details.get('topics'):
                        topic, _ = Topic.objects.get_or_create(name=name)
                        topics.append(topic)

        if serializer.is_valid():
            # Create the assessment within a transaction to ensure atomicity
            with transaction.atomic():
                serializer.save()
                if topics:
                    assessment.topics.set(topics)
                    
                response = f'assessment {assessment.assessment_id} has been successfully updated, the new updates will reflect imemdiately to all the students being assessed and their parents'
                audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='ASSESSMENT', target_object_id=str(assessment.assessment_id), outcome='UPDATED', server_response=response, school=requesting_account.school,)

            return {"message": response}
                
        # Return serializer errors if the data is not valid, format it as a string
        error_response = '; '.join([f"{key}: {', '.join(value)}" for key, value in serializer.errors.items()])
        audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='ASSESSMENT', target_object_id=str(assessment.assessment_id) if assessment else 'N/A', outcome='ERROR', server_response=f'Validation failed: {error_response}', school=requesting_account.school)
        return {"error": error_response}

    except Assessment.DoesNotExist:
        # Handle the case where the provided assessment ID does not exist
        return {'error': 'Could not process your request, an assessment in your school with the provided credentials does not exist, please check the assessment details and try again'}

    except BaseAccount.DoesNotExist:
        # Handle the case where the provided assessment ID does not exist
        return {'error': 'Could not process your request, an account with the provided credentials does not exist. please check the moderators account ID and try again.'}

    except ValidationError as e:
        error_message = e.messages[0].lower() if isinstance(e.messages, list) and e.messages else str(e).lower()
        audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='ASSESSMENT', target_object_id=str(assessment.assessment_id) if assessment else 'N/A', outcome='ERROR', server_response=error_message, school=requesting_account.school)
        return {"error": error_message}

    except Exception as e:
        error_message = str(e)
        audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='ASSESSMENT', target_object_id=str(assessment.assessment_id) if assessment else 'N/A', outcome='ERROR', server_response=error_message, school=requesting_account.school)
        return {'error': error_message}


@database_sync_to_async
def update_student_assessment_transcript(account, role, details):
    try:
        assessment = None  # Initialize assessment as None to prevent issues in error handling
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = accounts_utilities.get_account_and_linked_school(account, role)

        # Check if the user has permission to create an assessment
        if role != 'PRINCIPAL' and not permissions_utilities.has_permission(requesting_account, 'UPDATE', 'TRANSCRPIT'):
            response = f'could not proccess your request, you do not have the necessary permissions to update transcrpits.'
            audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='TRANSCRPIT', outcome='DENIED', response=response, school=requesting_account.school)

            return {'error': response}
                
        if not {'student', 'assessment'}.issubset(details):
            response = f'could not proccess your request, the provided information is invalid for the action you are trying to perform. please make sure to provide valid account and assessment IDs and try again'
            audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='TRANSCRPIT', outcome='ERROR', response=response, school=requesting_account.school)

            return {'error': response}

        # Fetch the assessment from the requesting user's school
        assessment = requesting_account.school.assessments.select_related('assessor','moderator').get(assessment_id=details['assessment'], grades_released=False)
        
        # Check if the user has permission to grade the assessment
        if (assessment.assessor and account != assessment.assessor.account_id) and (assessment.moderator and account != assessment.moderator.account_id):
            response = f'Could not proccess your request, you do not have the necessary permissions to update this transcrpit. only the assessments assessor or moderator can update scores of this transcrpit.'
            audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='TRANSCRPIT', target_object_id=str(assessment.assessment_id) if assessment else 'N/A', outcome='DENIED', response=response, school=requesting_account.school)
            return {'error': response}

        transcript = assessment.transcripts.get(student__account_id=details['student'])

        serializer = TranscriptUpdateSerializer(instance=transcript, data=details)
        if serializer.is_valid():
            with transaction.atomic():
                serializer.save()

                response = f"student graded for assessment {assessment.unique_identifier} has been successfully updated."
                audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='TRANSCRPIT', target_object_id=str(assessment.assessment_id) if assessment else 'N/A', outcome='GRADED', response=response, school=assessment.school)

            return {"message": response}

        error_response = '; '.join([f"{key}: {', '.join(value)}" for key, value in serializer.errors.items()])
        audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='TRANSCRPIT', target_object_id=str(assessment.assessment_id) if assessment else 'N/A', outcome='ERROR', response=f'Validation failed: {error_response}', school=requesting_account.school)
        return {"error": error_response}

    except Assessment.DoesNotExist:
        # Handle the case where the provided assessment ID does not exist
        return {'error': 'an assessment in your school with the provided credentials does not exist, please check the assessment details and try again'}

    except Student.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'a student account with the provided credentials does not exist, please check the accounts details and try again'}

    except ValidationError as e:
        error_message = e.messages[0].lower() if isinstance(e.messages, list) and e.messages else str(e).lower()
        audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='TRANSCRPIT', target_object_id=str(assessment.assessment_id) if assessment else 'N/A', outcome='ERROR', response=error_message, school=requesting_account.school)
        return {"error": error_message}

    except Exception as e:
        error_message = str(e)
        audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='TRANSCRPIT', target_object_id=str(assessment.assessment_id) if assessment else 'N/A', outcome='ERROR', response=error_message, school=requesting_account.school)
        return {'error': error_message}


@database_sync_to_async
def update_assessment_as_collected(user, role, details):
    try:
        assessment = None  # Initialize assessment as None to prevent issues in error handling
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = accounts_utilities.get_account_and_linked_school(user, role)

        # Check if the user has permission to create an assessment
        if role != 'PRINCIPAL' and not permissions_utilities.has_permission(requesting_account, 'UPDATE', 'ASSESSMENT'):
            response = f'could not proccess your request, you do not have the necessary permissions to update assessments.'
            audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='ASSESSMENT', outcome='DENIED', server_response=response, school=requesting_account.school)
            return {'error': response}
        
        if 'assessment' not in details:
            response = f'could not proccess your request, the provided information is invalid for the action you are trying to perform. please make sure to provide a valid assessment ID and try again'
            audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='ASSESSMENT', outcome='ERROR', server_response=response, school=requesting_account.school)
            return {'error': response}

        assessment = requesting_account.school.assessments.get(assessment_id=details['assessment'])
        
        with transaction.atomic():
            assessment.mark_as_collected()

            response = f"An assessment in your school with the following assessment ID: {assessment.assessment_id}, has been successfully flagged as collected. the assessor and moderator (if any) can now grade student submissions. Any submissions collected from here on out will be flagged as late submissions."
            audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='ASSESSMENT', target_object_id=str(assessment.assessment_id), outcome='UPDATED', server_response=response, school=assessment.school)

        return {"message": response}

    except Assessment.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'an assessment in your school with the provided credentials does not exist, please check the assessment details and try again'}

    except ValidationError as e:
        error_message = e.messages[0].lower() if isinstance(e.messages, list) and e.messages else str(e).lower()
        audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='ASSESSMENT', target_object_id=str(assessment.assessment_id) if assessment else 'N/A', outcome='ERROR', server_response=error_message, school=requesting_account.school)
        return {"error": error_message}

    except Exception as e:
        error_message = str(e)
        audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='ASSESSMENT', target_object_id=str(assessment.assessment_id) if assessment else 'N/A', outcome='ERROR', server_response=error_message, school=requesting_account.school)
        return {'error': error_message}


@database_sync_to_async
def update_assessment_as_graded(account, role, details):
    try:
        assessment = None  # Initialize assessment as None to prevent issues in error handling
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = accounts_utilities.get_account_and_linked_school(account, role)

        # Check if the user has permission to create an assessment
        if role != 'PRINCIPAL' and not permissions_utilities.has_permission(requesting_account, 'UPDATE', 'ASSESSMENT'):
            response = f'could not proccess your request, you do not have the necessary permissions to update assessments.'
            audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='ASSESSMENT', outcome='DENIED', server_response=response, school=requesting_account.school)
            return {'error': response}
                
        if 'assessment' not in details:
            response = f'could not proccess your request, the provided information is invalid for the action you are trying to perform. please make sure to provide valid assessment ID and try again'
            audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='ASSESSMENT', outcome='ERROR', server_response=response, school=requesting_account.school)
            return {'error': response}

        # Fetch the assessment from the requesting user's school
        assessment = requesting_account.school.assessments.get(assessment_id=details['assessment'])
        release_grades_task.delay(assessment.id)

        with transaction.atomic():
            response = f"The grades release process for assessment with assessment ID {assessment.title} has been triggered, results will be made available once performance metrics have been calculated and updated."
            audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='ASSESSMENT', target_object_id=str(assessment.assessment_id), outcome='UPDATED', server_response=response, school=assessment.school)

        return {"message": response}

    except Assessment.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'an assessment in your school with the provided credentials does not exist, please check the assessment details and try again'}

    except ValidationError as e:
        error_message = e.messages[0].lower() if isinstance(e.messages, list) and e.messages else str(e).lower()
        audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='ASSESSMENT', target_object_id=str(assessment.assessment_id) if assessment else 'N/A', outcome='ERROR', server_response=error_message, school=requesting_account.school)

        return {"error": error_message}

    except Exception as e:
        error_message = str(e)
        audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='ASSESSMENT', target_object_id=str(assessment.assessment_id) if assessment else 'N/A', outcome='ERROR', server_response=error_message, school=requesting_account.school)

        return {'error': error_message}


@database_sync_to_async
def update_group_timetable_details(account, role, details):
    try:
        group_timetable = None
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = accounts_utilities.get_account_and_linked_school(account, role)

        if role != 'PRINCIPAL' and not permissions_utilities.has_permission(requesting_account, 'UPDATE', 'GROUP_TIMETABLE'):
            response = f'could not proccess your request, you do not have the necessary permissions to view group timetables. please contact your administrator to adjust you permissions for viewing group timetables.'
            audits_utilities.log_audit(actor=requesting_account, action='VIEW', target_model='GROUP_TIMETABLE', outcome='DENIED', server_response=response, school=requesting_account.school)
            return {'error': response}

        elif 'group_timetable' not in details:
            response = f'could not proccess your request, the provided information is invalid for the action you are trying to perform. please make sure to provide a valid group timetable ID and try again'
            audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='GROUP_TIMETABLE', outcome='ERROR', server_response=response, school=requesting_account.school)
            return {'error': response}

        # Retrieve the specified group schedule
        group_timetable = requesting_account.school.group_timetables.get(group_timetable_id=details['group_timetable'])

        serializer = StudentGroupTimetableUpdateSerializer(group_timetable, data=details)
        if serializer.is_valid():
            with transaction.atomic():
                serializer.save()

                response = f"Group timetable with group timetable ID: {group_timetable.group_timetable_id}, has been successfully updated."
                audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='GROUP_TIMETABLE', target_object_id=str(group_timetable.group_timetable_id) if group_timetable else 'N/A', outcome='UPDATED', server_response=response, school=requesting_account.school)

            serialized_group_timetable = StudentGroupTimetableDetailsSerializer(group_timetable).data

            return {'message' : response, "group_timetable": serialized_group_timetable}

        error_response = '; '.join([f"{key}: {', '.join(value)}" for key, value in serializer.errors.items()])
        audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='GROUP_TIMETABLE', target_object_id=str(group_timetable.group_timetable_id) if group_timetable else 'N/A', outcome='ERROR', server_response=f'Validation failed: {error_response}', school=requesting_account.school)
        return {"error": error_response}

    
    except StudentGroupTimetable.DoesNotExist:
        # Handle case where the group schedule does not exist
        return {'error': 'Could not process your request, a group schedule with the provided credentials does not exist. Please check the group schedule details and try again.'}

    except ValidationError as e:
        error_message = e.messages[0].lower() if isinstance(e.messages, list) and e.messages else str(e).lower()
        audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='GROUP_TIMETABLE', target_object_id=str(group_timetable.group_sgroup_timetable_idchedule_id) if group_timetable else 'N/A', outcome='ERROR', server_response=response, school=requesting_account.school)
        return {"error": error_message}

    except Exception as e:
        error_message = str(e)
        audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='GROUP_TIMETABLE', target_object_id=str(group_timetable.group_timetable_id) if group_timetable else 'N/A', outcome='ERROR', server_response=response, school=requesting_account.school)
        return {'error': error_message}


@database_sync_to_async
def update_group_timetable_subscribers(user, role, details):
    try:
        students_list = details.get('students', '').split(', ')
        if not students_list or students_list == ['']:
            return {'error': 'your request could not be proccessed.. no students were provided'}
        
        group_timetable = None  # Initialize assessment as None to prevent issues in error handling

        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = accounts_utilities.get_account_and_linked_school(user, role)

        # Check if the user has permission to update classrooms
        if role != 'PRINCIPAL' and not permissions_utilities.has_permission(requesting_account, 'UPDATE', 'GROUP_TIMETABLE'):
            response = f'could not proccess your request, you do not have the necessary permissions to update classroom details.'
            audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='CLASSROOM', outcome='DENIED', response=response, school=requesting_account.school)
            return {'error': response}

        elif 'group_timetable' not in details:
            response = f'could not proccess your request, the provided information is invalid for the action you are trying to perform. please make sure to provide a valid group timetable ID and try again'
            audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='GROUP_TIMETABLE', outcome='ERROR', server_response=response, school=requesting_account.school)
            return {'error': response}

        group_timetable = requesting_account.school.group_timetables.get(group_timetable_id=details['group_timetable'])

        with transaction.atomic():
            # Check for validation errors and perform student updates
            group_timetable.update_subscribers(students_list=students_list, subscribe=details.get('subscribe'))

            response = f"The provided list of student accounts has been {'subscribed to' if details.get('subscribe') else 'unsubscribed from'} the group timetable with the group timetable ID: {group_timetable.group_schedule_id}."
            audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='GROUP_TIMETABLE', target_object_id=str(group_timetable.group_timetable_id) if group_timetable else 'N/A', outcome='UPDATED', server_response=response, school=requesting_account.school)

        return {'message': response}
    
    except Classroom.DoesNotExist:
        # Handle case where the classroom does not exist
        return {'error': 'a classroom in your school with the provided credentials does not exist. please check the classroom details and try again.'}

    except ValidationError as e:
        error_message = e.messages[0].lower() if isinstance(e.messages, list) and e.messages else str(e).lower()
        audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='GROUP_TIMETABLE', target_object_id=str(group_timetable.group_timetable_id) if group_timetable else 'N/A', outcome='ERROR', server_response=error_message, school=requesting_account.school)
        return {"error": error_message}

    except Exception as e:
        error_message = str(e)
        audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='GROUP_TIMETABLE', target_object_id=str(group_timetable.group_timetable_id) if group_timetable else 'N/A', outcome='ERROR', server_response=error_message, school=requesting_account.school)
        return {'error': error_message}

