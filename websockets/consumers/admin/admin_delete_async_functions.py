# channels
from channels.db import database_sync_to_async

# django
from django.db import transaction
from django.core.exceptions import ValidationError

# models 
from accounts.models import Principal, Admin, Teacher, Student
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



@database_sync_to_async
def delete_school_account(user, role, details):
    try:
        school = None  # Initialize school as None to prevent issues in error handling
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = accounts_utilities.get_account_and_linked_school(user, role)

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
def delete_account(user, role, details):
    try:
        if details.get('role') not in ['ADMIN', 'TEACHER', 'STUDENT']:
            return {"error": 'could not proccess your request, the provided account role is invalid'}

        requested_account = None  # Initialize requested_account as None to prevent issues in error handling
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = accounts_utilities.get_account_and_attr(user, role)

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
            requested_account = accounts_utilities.get_account_and_attr(details.get('account'), details['role'])

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
def delete_grade(user, role, details):
    try:
        grade = None  # Initialize requested_account as None to prevent issues in error handling
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = accounts_utilities.get_account_and_linked_school(user, role)

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
def delete_term(user, role, details):
    try:
        term = None  # Initialize term as None to prevent issues in error handling
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = accounts_utilities.get_account_and_linked_school(user, role)

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
def delete_subject(user, role, details):
    try:
        subject = None  # Initialize subject as None to prevent issues in error handling
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = accounts_utilities.get_account_and_linked_school(user, role)

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
def delete_class(user, role, details):
    try:
        classroom = None  # Initialize classroom as None to prevent issues in error handling
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = accounts_utilities.get_account_and_linked_school(user, role)

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
def delete_assessment(user, role, details):
    try:
        assessment = None  # Initialize assessment as None to prevent issues in error handling
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = accounts_utilities.get_account_and_linked_school(user, role)

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
def delete_daily_schedule(user, role, details):
    try:
        daily_schedule = None  # Initialize schedule as None to prevent issues in error handling
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = accounts_utilities.get_account_and_linked_school(user, role)

        # Check if the user has permission to create a group schedule
        if role != 'PRINCIPAL' and not permissions_utilities.has_permission(requesting_account, 'DELETE', 'DAILY_SCHEDULE'):
            response = 'Could not process your request, you do not have the necessary permissions to delete daily schedules.'
            audits_utilities.log_audit(actor=requesting_account, action='DELETE', target_model='DAILY_SCHEDULE', outcome='DENIED', response=response, school=requesting_account.school)

            return {'error': response}

        if details.get('group'):
            daily_schedule = Timetable.objects.get(daily_schedule_id=details.get('schedule'), student_group_timetable__grade__school=requesting_account.school)
            response = 'the schedule has been successfully deleted from the group schedule and will be removed from schedules of all students subscribed to the group schedule'
            
        if details.get('teacher'):
            daily_schedule = Timetable.objects.get(daily_schedule_id=details.get('schedule'), teacher_timetable__teacher__school=requesting_account.school)
            response = 'the schedule has been successfully deleted from the teachers schedule and will no longer be available to the teacher'
            
        else:
            response = 'could not process your request, the provided type is invalid'

            audits_utilities.log_audit(actor=requesting_account, action='DELETE', target_model='DAILY_SCHEDULE', outcome='DENIED', response=response, school=requesting_account.school)

            return {"error": response}
        
        with transaction.atomic():
            audits_utilities.log_audit(actor=requesting_account, action='DELETE', target_model='DAILY_SCHEDULE', target_object_id=str(daily_schedule.daily_schedule_id), outcome='DELETED', response=response, school=requesting_account.school)

            daily_schedule.delete()

        return {'message': response}

    except Timetable.DoesNotExist:
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
def delete_group_schedule(user, role, details):
    try:
        group_timtable = None  # Initialize group timtable as None to prevent issues in error handling
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = accounts_utilities.get_account_and_linked_school(user, role)

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

