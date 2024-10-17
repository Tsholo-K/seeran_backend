# channels
from channels.db import database_sync_to_async

# django
from django.db import transaction
from django.core.exceptions import ValidationError

# models 
from accounts.models import Principal, Admin, Teacher, Student
from permission_groups.models import AdminPermissionGroup, TeacherPermissionGroup
from grades.models import Grade
from terms.models import Term
from subjects.models import Subject
from classrooms.models import Classroom
from assessments.models import Assessment
from student_group_timetables.models import StudentGroupTimetable
from timetables.models import Timetable

# checks
from accounts.checks import permission_checks

# utility functions 
from accounts import utils as accounts_utilities
from account_permissions import utils as permissions_utilities
from audit_logs import utils as audits_utilities

# tasks
from term_subject_performances import tasks as  term_subject_performances_tasks
from classroom_performances import tasks as  classroom_performances_tasks



@database_sync_to_async
def delete_school_account(account, role):
    try:
        school = None  # Initialize school as None to prevent issues in error handling
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = accounts_utilities.get_account_and_linked_school(account, role)

        if role not in ['PRINCIPAL']:
            response = f'could not proccess your request, you do not have the necessary permissions to delete your schools account. only the principal can delete the schools account from the system.'
            audits_utilities.log_audit(actor=requesting_account, action='DELETE', target_model='ACCOUNT', outcome='DENIED', server_response=response, school=requesting_account.school)

            return {'error': response}
        
        school = requesting_account.school

        with transaction.atomic():
            # Delete the School instance
            school.delete()

        # Return a success message
        return {"message": "school account deleted successfully, it was nice while it lasted"}

    except ValidationError as e:
        error_message = e.messages[0].lower() if isinstance(e.messages, list) and e.messages else str(e).lower()
        audits_utilities.log_audit(actor=requesting_account, action='DELETE', target_model='ACCOUNT', target_object_id=str(school.school_id), outcome='ERROR', server_response=error_message, school=requesting_account.school)
        return {"error": error_message}

    except Exception as e:
        error_message = str(e)
        audits_utilities.log_audit(actor=requesting_account, action='DELETE', target_model='ACCOUNT', target_object_id=str(school.school_id), outcome='ERROR', server_response=error_message, school=requesting_account.school)
        return {'error': error_message}


@database_sync_to_async
def delete_permission_group(account, role, details):
    try:
        permission_group = None
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = accounts_utilities.get_account_and_linked_school(account, role)

        # Check if the user has permission to create an assessment
        if role != 'PRINCIPAL' and not permissions_utilities.has_permission(requesting_account, 'DELETE', 'PERMISSION'):
            response = f'Could not proccess your request, you do not have the necessary permissions to view permission group details. Please contact your administrators to adjust you permissions for viewing permissions.'
            audits_utilities.log_audit(actor=requesting_account, action='DELETE', target_model='PERMISSION', outcome='DENIED', server_response=response, school=requesting_account.school)
            return {'error': response}
        
        if not {'permission_group', 'group'}.issubset(details) or details['group'] not in ['admins', 'teachers']:
            response = f'Could not proccess your request, the provided information is invalid for the action you are trying to perform. Please make sure to provide a valid group ID and group (admin or teacher) for which to filter the permission groups and try again'
            audits_utilities.log_audit(actor=requesting_account, action='DELETE', target_model='PERMISSION', outcome='ERROR', server_response=response, school=requesting_account.school)
            return {'error': response}
        
        # Determine the group type based on the role
        if details['group'] == 'admins':
            permission_group = requesting_account.school.admin_permission_groups.get(permission_group_id=details['permission_group'])
      
        else:
            permission_group = requesting_account.school.teacher_permission_groups.get(permission_group_id=details['permission_group'])

        with transaction.atomic():
            response = f"Permission group, {permission_group.group_name}, with permission group ID: {permission_group.permission_group_id}, has been successfully deleted from you schools system. All accounts subscribed to it will lose all permissions that were attached to it, effective immediately."
            audits_utilities.log_audit(actor=requesting_account, action='DELETE', target_model='PERMISSION', target_object_id=str(permission_group.permission_group_id), outcome='DELETED', server_response=response, school=requesting_account.school)
            
            permission_group.delete()

        return {"message": response}
    
    except AdminPermissionGroup.DoesNotExist:
        # Handle the case where the provided grade ID does not exist
        return { 'error': 'Could not process your request, a admin permission group in your school with the provided credentials does not exist. Please review the group details and try again'}
    
    except TeacherPermissionGroup.DoesNotExist:
        # Handle the case where the provided grade ID does not exist
        return { 'error': 'Could not process your request, a teacher permission group  in your school with the provided credentials does not exist. Please review the group details and try again'}

    except ValidationError as e:
        error_message = e.messages[0].lower() if isinstance(e.messages, list) and e.messages else str(e).lower()
        audits_utilities.log_audit(actor=requesting_account, action='DELETE', target_model='PERMISSION', target_object_id=str(permission_group.permission_group_id), outcome='ERROR', server_response=error_message, school=requesting_account.school)
        return {"error": error_message}

    except Exception as e:
        error_message = str(e)
        audits_utilities.log_audit(actor=requesting_account, action='DELETE', target_model='PERMISSION', target_object_id=str(permission_group.permission_group_id), outcome='ERROR', server_response=error_message, school=requesting_account.school)
        return {'error': error_message}


@database_sync_to_async
def delete_account(account, role, details):
    try:
        if details.get('role') not in ['ADMIN', 'TEACHER', 'STUDENT']:
            return {"error": 'could not proccess your request, the provided account role is invalid'}

        requested_account = None  # Initialize requested_account as None to prevent issues in error handling
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = accounts_utilities.get_account_and_permission_check_attr(account, role)

        if details['role'] == 'ADMIN' and role == 'ADMIN':
            response = f'could not proccess your request, your accounts role does not have enough permissions to perform this action.'
            audits_utilities.log_audit(actor=requesting_account, action='DELETE', target_model='ACCOUNT', outcome='DENIED', server_response=response, school=requesting_account.school)
            return {'error': response}

        # Check if the user has permission to create a grade
        elif role != 'PRINCIPAL' and not permissions_utilities.has_permission(requesting_account, 'DELETE', 'ACCOUNT'):
            response = f'could not proccess your request, you do not have the necessary permissions to delete accounts'
            audits_utilities.log_audit(actor=requesting_account, action='DELETE', target_model='ACCOUNT', outcome='DENIED', server_response=response, school=requesting_account.school)
            return {'error': response}

        elif details['role'] in ['ADMIN', 'TEACHER', 'STUDENT']:
            # Retrieve the requesting users account and related school in a single query using select_related
            requested_account = accounts_utilities.get_account_and_permission_check_attr(details.get('account'), details['role'])

            # Check if the requesting user has permission to update the requested user's account.
            permission_error = permission_checks.view_account(requesting_account, requested_account)
            if permission_error:
                return permission_error

            with transaction.atomic():
                response = f"Account with account ID: {requested_account.account_id} and role, {details['role'].lower()}, has been successfully deleted and removed from your schools system. The account and all it's related related data will be purged from the system, effective immediately."
                audits_utilities.log_audit(actor=requesting_account, action='DELETE', target_model='ACCOUNT', target_object_id=str(requested_account.account_id), outcome='DELETED', server_response=response, school=requesting_account.school)
                requested_account.delete()

            return {"message" : response}

        response = 'could not proccess your request, the provided account role is invalid'
        audits_utilities.log_audit(actor=requesting_account, action='DELETE', target_model='ACCOUNT', target_object_id=str(requested_account.account_id), outcome='DENIED', server_response=response, school=requesting_account.school)
        return {'error': response}

    except ValidationError as e:
        error_message = e.messages[0].lower() if isinstance(e.messages, list) and e.messages else str(e).lower()
        audits_utilities.log_audit(actor=requesting_account, action='DELETE', target_model='ACCOUNT', target_object_id=str(requested_account.account_id), outcome='ERROR', server_response=error_message, school=requesting_account.school)

        return {"error": error_message}

    except Exception as e:
        error_message = str(e)
        audits_utilities.log_audit(actor=requesting_account, action='DELETE', target_model='ACCOUNT', target_object_id=str(requested_account.account_id), outcome='ERROR', server_response=error_message, school=requesting_account.school)

        return {'error': error_message}


@database_sync_to_async
def delete_grade(account, role, details):
    try:
        grade = None  # Initialize requested_account as None to prevent issues in error handling
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = accounts_utilities.get_account_and_linked_school(account, role)

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
def delete_subject(account, role, details):
    try:
        subject = None  # Initialize subject as None to prevent issues in error handling
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = accounts_utilities.get_account_and_linked_school(account, role)

        # Check if the user has permission to create a grade
        if role != 'PRINCIPAL' and not permissions_utilities.has_permission(requesting_account, 'DELETE', 'SUBJECT'):
            response = f'could not proccess your request, you do not have the necessary permissions to delete a subject'
            audits_utilities.log_audit(actor=requesting_account, action='DELETE', target_model='SUBJECT', outcome='DENIED', server_response=response, school=requesting_account.school)
            return {'error': response}

        if 'subject' not in details:
            response = f'Could not proccess your request, the provided information is invalid for the action you are trying to perform. please make sure to provide a valid subject ID and try again.'
            audits_utilities.log_audit(actor=requesting_account, action='DELETE', target_model='SUBJECT', outcome='ERROR', server_response=response, school=requesting_account.school)
            return {'error': response}

        subject = requesting_account.school.subjects.get(subject_id=details['subject'])

        # Create the grade within a transaction to ensure atomicity
        with transaction.atomic():
            response = f"A subject in your school with the subject ID: {subject.subject_id}, has been successfully deleted. All it's associated data will be purged from the system, effective immedialtely."
            audits_utilities.log_audit(actor=requesting_account, action='DELETE', target_model='SUBJECT', target_object_id=str(subject.subject_id) if subject else 'N/A', outcome='DELETED', server_response=response, school=requesting_account.school,)
            
            subject.delete()

        return {'message' : response}
    
    except Subject.DoesNotExist:
        # Handle the case where the provided grade ID does not exist
        return {'error': 'a subject in your school with the provided credentials does not exist. please check the subject details and try again.'}

    except ValidationError as e:
        error_message = e.messages[0].lower() if isinstance(e.messages, list) and e.messages else str(e).lower()
        audits_utilities.log_audit(actor=requesting_account, action='DELETE', target_model='SUBJECT', target_object_id=str(subject.subject_id) if subject else 'N/A', outcome='ERROR', server_response=error_message, school=requesting_account.school)
        return {"error": error_message}

    except Exception as e:
        error_message = str(e)
        audits_utilities.log_audit(actor=requesting_account, action='DELETE', target_model='SUBJECT', target_object_id=str(subject.subject_id) if subject else 'N/A', outcome='ERROR', server_response=error_message, school=requesting_account.school)
        return {'error': error_message}


@database_sync_to_async
def delete_term(user, role, details):
    try:
        term = None  # Initialize term as None to prevent issues in error handling
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = accounts_utilities.get_account_and_linked_school(user, role)

        # Check if the user has permission to create a grade
        if role != 'PRINCIPAL' and not permissions_utilities.has_permission(requesting_account, 'DELETE', 'TERM'):
            response = f'Could not proccess your request, you do not have the necessary permissions to delete a grade'
            audits_utilities.log_audit(actor=requesting_account, action='DELETE', target_model='TERM', outcome='DENIED', server_response=response, school=requesting_account.school)

            return {'error': response}

        if not {'term'}.issubset(details):
            response = f'Could not proccess your request, the provided information is invalid for the action you are trying to perform. please make sure to provide valid term and subject IDs and try again'
            audits_utilities.log_audit(actor=requesting_account, action='VIEW', target_model='TERM', outcome='ERROR', server_response=response, school=requesting_account.school)
            return {'error': response}

        term = requesting_account.school.terms.get(term_id=details['term'])

        # Create the grade within a transaction to ensure atomicity
        with transaction.atomic():
            response = f"A term in your school with the term ID {term.term_id} has been successfully deleted. The term and all it's associated data will be purged from the system, effective immediately."
            audits_utilities.log_audit(actor=requesting_account, action='DELETE', target_model='TERM', target_object_id=str(term.term_id), outcome='DELETED', server_response=response, school=requesting_account.school,)
            term.delete()

        return {'message' : response}
    
    except Term.DoesNotExist:
        # Handle the case where the provided grade ID does not exist
        return {'error': 'Could not proccess your request, a term in your school with the provided credentials does not exist. Please check the term details and try again.'}

    except ValidationError as e:
        error_message = e.messages[0].lower() if isinstance(e.messages, list) and e.messages else str(e).lower()
        audits_utilities.log_audit(actor=requesting_account, action='DELETE', target_model='TERM', target_object_id=str(term.term_id), outcome='ERROR', server_response=error_message, school=requesting_account.school)
        return {"error": error_message}

    except Exception as e:
        error_message = str(e)
        audits_utilities.log_audit(actor=requesting_account, action='DELETE', target_model='TERM', target_object_id=str(term.term_id), server_response=error_message, school=requesting_account.school)
        return {'error': error_message}
    
    
@database_sync_to_async
def delete_classroom(account, role, details):
    try:
        classroom = None  # Initialize classroom as None to prevent issues in error handling
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = accounts_utilities.get_account_and_linked_school(account, role)

        # Check if the user has permission to create a grade
        if role != 'PRINCIPAL' and not permissions_utilities.has_permission(requesting_account, 'DELETE', 'CLASSROOM'):
            response = f'could not proccess your request, you do not have the necessary permissions to delete a classroom'
            audits_utilities.log_audit(actor=requesting_account, action='DELETE', target_model='CLASSROOM', outcome='DENIED', server_response=response, school=requesting_account.school)

            return {'error': response}

        if not 'classroom' in details:
            response = f'could not proccess your request, the provided information is invalid for the action you are trying to perform. please make sure to provide valid classroom ID and try again'
            audits_utilities.log_audit(actor=requesting_account, action='DELETE', target_model='CLASSROOM', outcome='ERROR', server_response=response, school=requesting_account.school)
            return {'error': response}

        classroom = requesting_account.school.classrooms.select_related('grade').only('grade__grade').get(classroom_id=details['classroom'])
        
        with transaction.atomic():
            response = f"grade {classroom.grade.grade} classroom deleted successfully, the classroom will no longer be accessible or available in your schools data"
            audits_utilities.log_audit(actor=requesting_account, action='DELETE', target_model='CLASSROOM', target_object_id=str(classroom.classroom_id) if classroom else 'N/A', outcome='DELETED', server_response=response, school=requesting_account.school,)

            classroom.delete()

        return {'message': response}

    except Classroom.DoesNotExist:
        # Handle case where the grade does not exist
        return {'error': 'Could not proccess your request, a classroom in your school with the provided credentials does not exist. Please check the term details and try again.'}

    except ValidationError as e:
        error_message = e.messages[0].lower() if isinstance(e.messages, list) and e.messages else str(e).lower()
        audits_utilities.log_audit(actor=requesting_account, action='DELETE', target_model='CLASSROOM', target_object_id=str(classroom.classroom_id) if classroom else 'N/A', outcome='ERROR', server_response=error_message, school=requesting_account.school)

        return {"error": error_message}

    except Exception as e:
        error_message = str(e)
        audits_utilities.log_audit(actor=requesting_account, action='DELETE', target_model='CLASSROOM', target_object_id=str(classroom.classroom_id) if classroom else 'N/A', outcome='ERROR', server_response=error_message, school=requesting_account.school)

        return {'error': error_message}


@database_sync_to_async
def delete_assessment(account, role, details):
    try:
        assessment = None  # Initialize assessment as None to prevent issues in error handling
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = accounts_utilities.get_account_and_linked_school(account, role)

        # Check if the user has permission to create an assessment
        if role != 'PRINCIPAL' and not permissions_utilities.has_permission(requesting_account, 'DELETE', 'ASSESSMENT'):
            response = f'could not proccess your request, you do not have the necessary permissions to delete assessments.'
            audits_utilities.log_audit( actor=requesting_account, action='DELETE', target_model='ASSESSMENT', outcome='DENIED', server_response=response, school=requesting_account.school)

            return {'error': response}
        
        if 'assessment' not in details:
            response = f'could not proccess your request, the provided information is invalid for the action you are trying to perform. please make sure to provide a valid assessment ID and try again'
            audits_utilities.log_audit(actor=requesting_account, action='DELETE', target_model='ASSESSMENT', outcome='ERROR', server_response=response, school=requesting_account.school)
            return {'error': response}

        assessment = requesting_account.school.assessments.get(assessment_id=details['assessment'])

        with transaction.atomic():
            response = f"assessment with assessment ID {assessment.assessment_id} has been successfully deleted, along with it's associated data"
            audits_utilities.log_audit(actor=requesting_account, action='DELETE', target_model='ASSESSMENT', target_object_id=str(assessment.assessment_id), outcome='DELETED', server_response=response, school=requesting_account.school)
            
            if assessment.classroom:
                classroom_performance, created = assessment.classroom.classroom_performances.get_or_create(term=assessment.term, defaults={'school': requesting_account.school})
                classroom = True
            else:
                term_performance, created = assessment.subject.termly_performances.get_or_create(term=assessment.term, defaults={'school': requesting_account.school})
                classroom = False

            assessment.delete()

        if classroom:
            classroom_performances_tasks.update_classroom_performance_metrics_task.delay(classroom_performance_id=classroom_performance.id)
        else:
            term_subject_performances_tasks.update_term_performance_metrics_task.delay(term_performance_id=term_performance.id)

        return {"message": response}

    except Assessment.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'an assessment in your school with the provided credentials does not exist, please check the assessment details and try again'}

    except ValidationError as e:
        error_message = e.messages[0].lower() if isinstance(e.messages, list) and e.messages else str(e).lower()
        audits_utilities.log_audit(actor=requesting_account, action='DELETE', target_model='ASSESSMENT', target_object_id=str(assessment.assessment_id) if assessment else 'N/A', outcome='ERROR', server_response=error_message, school=requesting_account.school)
        return {"error": error_message}

    except Exception as e:
        error_message = str(e)
        audits_utilities.log_audit(actor=requesting_account, action='DELETE', target_model='ASSESSMENT', target_object_id=str(assessment.assessment_id) if assessment else 'N/A', outcome='ERROR', server_response=error_message, school=requesting_account.school)
        return {'error': error_message}


@database_sync_to_async
def delete_timetable(account, role, details):
    try:
        timetable = None  # Initialize schedule as None to prevent issues in error handling
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = accounts_utilities.get_account_and_linked_school(account, role)

        # Check if the user has permission to create a group schedule
        if role != 'PRINCIPAL' and not permissions_utilities.has_permission(requesting_account, 'DELETE', 'TIMETABLE'):
            response = 'Could not process your request, you do not have the necessary permissions to delete daily schedules.'
            audits_utilities.log_audit(actor=requesting_account, action='DELETE', target_model='TIMETABLE', outcome='DENIED', server_response=response, school=requesting_account.school)

            return {'error': response}

        timetable = requesting_account.school.timetables.get(timetable_id=details.get('timetable'))
        
        if timetable.teacher_timetable.exists():
            linked_timetable = timetable.teacher_timetable
        else:
            linked_timetable = timetable.group_timetable

        with transaction.atomic():
            response = f"A timetable with timetable ID: {timetable.timetable_id}, has been successfully deleted from your schools system. All sessions linked to the timetable will also be purged from the system, effective immediately."
            audits_utilities.log_audit(actor=requesting_account, action='DELETE', target_model='TIMETABLE', target_object_id=str(timetable.timetable_id), outcome='DELETED', server_response=response, school=requesting_account.school)

            timetable.delete()

            linked_timetable.timetables_count = linked_timetable.timetables.count()
            linked_timetable.save()

        return {'message': response}

    except Timetable.DoesNotExist:
        # Handle the case where the provided schedule_id does not exist
        return {'error': 'Could not process your request, a timetable for your school with the provided credentials does not exist. please verify the details and try again.'}

    except ValidationError as e:
        error_message = e.messages[0].lower() if isinstance(e.messages, list) and e.messages else str(e).lower()
        audits_utilities.log_audit(actor=requesting_account, action='DELETE', target_model='TIMETABLE', target_object_id=str(timetable.timetable_id) if timetable else 'N/A', outcome='ERROR', server_response=error_message, school=requesting_account.school)

        return {"error": error_message}

    except Exception as e:
        error_message = str(e)
        audits_utilities.log_audit(actor=requesting_account, action='DELETE', target_model='TIMETABLE', target_object_id=str(timetable.timetable_id) if timetable else 'N/A', outcome='ERROR', server_response=error_message, school=requesting_account.school)

        return {'error': error_message}


@database_sync_to_async
def delete_group_timetable(user, role, details):
    try:
        group_timetable = None  # Initialize group timtable as None to prevent issues in error handling
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = accounts_utilities.get_account_and_linked_school(user, role)

        # Check if the user has permission to create a group schedule
        if role != 'PRINCIPAL' and not permissions_utilities.has_permission(requesting_account, 'DELETE', 'GROUP_TIMETABLE'):
            response = 'could not process your request, you do not have the necessary permissions to delete group timetables.'
            audits_utilities.log_audit(actor=requesting_account, action='DELETE', target_model='GROUP_TIMETABLE', outcome='DENIED', server_response=response, school=requesting_account.school)
            return {'error': response}

        if not {'group_timetable'}.issubset(details):
            response = f'could not proccess your request, the provided information is invalid for the action you are trying to perform. please make sure to provide valid group timetable ID and try again'
            audits_utilities.log_audit(actor=requesting_account, action='DELETE', target_model='GROUP_TIMETABLE', outcome='ERROR', server_response=response, school=requesting_account.school)
            return {'error': response}

        group_timetable = requesting_account.school.group_timetables.get(group_timetable_id=details['group_timetable'])
        
        with transaction.atomic():
            response = f'Group timetable with group timetable ID : {group_timetable.group_timetable_id}, has been deleted from your schools system. All data related to the group will be purged from the system effective immediately.'
            audits_utilities.log_audit(actor=requesting_account,action='DELETE', target_model='GROUP_TIMETABLE', target_object_id=str(group_timetable.group_timetable_id) if group_timetable else 'N/A', outcome='DELETED', server_response=response, school=requesting_account.school)

            group_timetable.delete()

        return {'message': response}

    except StudentGroupTimetable.DoesNotExist:
        # Handle case where group schedule does not exist
        return {'error': 'a group timetable for your school with the provided credentials does not exist, please check the group details and try again'}

    except ValidationError as e:
        error_message = e.messages[0].lower() if isinstance(e.messages, list) and e.messages else str(e).lower()
        audits_utilities.log_audit(
            actor=requesting_account, 
            action='DELETE', 
            target_model='GROUP_TIMETABLE', 
            target_object_id=str(group_timetable.group_timetable_id) if group_timetable else 'N/A', 
            outcome='ERROR', 
            server_response=error_message, 
            school=requesting_account.school
        )
        return {"error": error_message}

    except Exception as e:
        error_message = str(e)
        audits_utilities.log_audit(
            actor=requesting_account, 
            action='DELETE', 
            target_model='GROUP_TIMETABLE', 
            target_object_id=str(group_timetable.group_timetable_id) if group_timetable else 'N/A', 
            outcome='ERROR', 
            server_response=error_message, 
            school=requesting_account.school
        )
        return {'error': error_message}


