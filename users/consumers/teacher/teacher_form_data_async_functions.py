# channels
from channels.db import database_sync_to_async

# django
from django.utils import timezone
from django.utils.translation import gettext as _

# models 
from users.models import Teacher
from classes.models import Classroom
from attendances.models import Attendance

# serializers
from users.serializers.students.students_serializers import StudentSourceAccountSerializer
from terms.serializers import FormTermsSerializer

# utility functions 
from permissions import utils as permissions_utilities
from audit_logs import utils as audits_utilities


@database_sync_to_async
def form_data_for_assessment_setting(user, details):

    try:
        classroom = None  # Initialize classroom as None to prevent issues in error handling
        requesting_account = Teacher.objects.select_related('school').get(account_id=user)

        # Check if the user has permission to create an assessment
        if not permissions_utilities.has_permission(requesting_account, 'CREATE', 'ASSESSMENT'):
            response = f'could not proccess your request, you do not have the necessary permissions to create assessments.'
            audits_utilities.log_audit(actor=requesting_account, action='CREATE', target_model='ASSESSMENT', outcome='DENIED', response=response, school=requesting_account.school)

            return {'error': response}

        classroom = requesting_account.taught_classes.select_related('grade', 'teacher').prefetch_related('grade__terms').filter(classroom_id=details.get('classroom')).first()
        if not classroom:
            response = f'could not proccess your request, you can not set assessments for classrooms that are not assigned to you.'
            audits_utilities.log_audit(actor=requesting_account, action='CREATE', target_model='ASSESSMENT', outcome='DENIED', response=response, school=requesting_account.school)

            return {'error': response}
        
        terms = classroom.grade.terms.all()
        
        serialized_terms = FormTermsSerializer(terms, many=True).data

        return {"terms": serialized_terms}
                   
    except Teacher.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'a teacher account with the provided credentials does not exist, please check your account details and try again'}

    except Exception as e:
        error_message = str(e)
        audits_utilities.log_audit(actor=requesting_account, action='CREATE', target_model='ASSESSMENT', target_object_id=str(classroom.classroom_id) if classroom else 'N/A', outcome='ERROR', response=error_message, school=requesting_account.school)

        return {'error': error_message}
    

@database_sync_to_async
def form_data_for_attendance_register(user, details):
    try:
        classroom = None  # Initialize classroom as None to prevent issues in error handling
        requesting_account = Teacher.objects.select_related('school').get(account_id=user)

        classroom = requesting_account.taught_classes.get(classroom_id=details.get('classroom'), register_class=True).first()
        if not classroom:
            response = f'could not proccess your request, you do not seem to be assigned to a register class.'
            audits_utilities.log_audit(actor=requesting_account, action='CREATE', target_model='ASSESSMENT', outcome='DENIED', response=response, school=requesting_account.school)

            return {'error': response}

        # Get today's date
        today = timezone.localdate()
            
        # Check if an Absent instance exists for today and the given class
        attendance = Attendance.objects.prefetch_related('absent_students').filter(date__date=today, classroom=classroom).first()

        if attendance:
            students = attendance.absent_students.all()
            attendance_register_taken = True

        else:
            students = classroom.students.all()
            attendance_register_taken = False

        serialized_students = StudentSourceAccountSerializer(students, many=True).data

        return {"students": serialized_students, "attendance_register_taken" : attendance_register_taken}
                   
    except Teacher.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'a teacher account with the provided credentials does not exist, please check your account details and try again'}
            
    except Classroom.DoesNotExist:
        return { 'error': 'class with the provided credentials does not exist' }

    except Exception as e:
        error_message = str(e)
        audits_utilities.log_audit(actor=requesting_account, action='CREATE', target_model='ASSESSMENT', target_object_id=str(classroom.classroom_id) if classroom else 'N/A', outcome='ERROR', response=error_message, school=requesting_account.school)

        return {'error': error_message}

