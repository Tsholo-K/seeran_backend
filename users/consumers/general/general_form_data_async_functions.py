# python 

# httpx

# channels
from channels.db import database_sync_to_async

# django
from django.utils import timezone
from django.utils.translation import gettext as _

# simple jwt

# models 
from users.models import BaseUser, Principal, Admin, Teacher
from classes.models import Classroom
from attendances.models import Attendance

# serializers
from users.serializers.students.students_serializers import StudentSourceAccountSerializer
from terms.serializers import FormTermsSerializer

# mappings
from users.maps import role_specific_maps

# utlity functions
from permissions.utils import has_permission
from audit_logs.utils import log_audit


@database_sync_to_async
def form_data_for_assessment_setting(user, role, details):

    try:
        if role not in ['PRINCIPAL', 'ADMIN', 'TEACHER']:
            return {"error": 'could not proccess your request.. your account either has insufficient permissions or is invalid for the action you are trying to perform'}

        # Get the appropriate model for the requesting user's role from the mapping.
        Model = role_specific_maps.account_access_control_mapping[role]

        # Build the queryset for the requesting account with the necessary related fields.
        requesting_account = Model.objects.select_related('school').get(account_id=user)

        # Check if the user has permission to create an assessment
        if role != 'PRINCIPAL' and not has_permission(requesting_account, 'CREATE', 'ASSESSMENT'):
            response = f'could not proccess your request, you do not have the necessary permissions to create assessments.'

            log_audit(
                actor=requesting_account,
                action='CREATE',
                target_model='ASSESSMENT',
                outcome='DENIED',
                response=response,
                school=requesting_account.school
            )

            return {'error': response}

        if details.get('classroom'):
            classroom = requesting_account.school.classes.select_related('grade', 'teacher').prefetch_related('grade__terms').filter(grade_id=details.get('classroom'))
            if not classroom:
                response = f'could not proccess your request, you can not set assessments for classrooms that are not assigned to you.'

                log_audit(
                    actor=requesting_account,
                    action='CREATE',
                    target_model='ASSESSMENT',
                    outcome='DENIED',
                    response=response,
                    school=requesting_account.school
                )

                return {'error': response}

            if role == 'TEACHER' and requesting_account != classroom.teaccher:
                response = f'could not proccess your request, you can not set assessments for classrooms that are not assigned to you.'

                log_audit(
                    actor=requesting_account,
                    action='CREATE',
                    target_model='ASSESSMENT',
                    outcome='DENIED',
                    response=response,
                    school=requesting_account.school
                )

                return {'error': response}
            
            terms = classroom.grade.terms.all()

        elif details.get('grade'):
            if role not in ['PRINCIPAL', 'ADMIN']:
                response = f'could not proccess your request, you do not have the necessary permissions to create grade wide assessments.'

                log_audit(
                    actor=requesting_account,
                    action='CREATE',
                    target_model='ASSESSMENT',
                    outcome='DENIED',
                    response=response,
                    school=requesting_account.school
                )

                return {'error': response}
            
            grade = requesting_account.school.grades.prefetch_related('terms').filter(grade_id=details.get('grade'))
            if not grade:
                response = f'could not proccess your request, a grade for your school with the provided credentials does not exist. please check the grades information and try again.'

                log_audit(
                    actor=requesting_account,
                    action='CREATE',
                    target_model='ASSESSMENT',
                    outcome='ERROR',
                    response=response,
                    school=requesting_account.school
                )

                return {'error': response}

            terms = grade.terms.all()

        else:
            response = f'could not proccess your request, invalid assessment creation details were provided. please check the provided details and try again.'

            log_audit(
                actor=requesting_account,
                action='CREATE',
                target_model='ASSESSMENT',
                outcome='ERROR',
                response=response,
                school=requesting_account.school
            )

            return {'error': response}
        
        serialized_terms = FormTermsSerializer(terms, many=True).data

        return {"terms": serialized_terms}
               
    except Principal.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'a principal account with the provided credentials does not exist, please check your account details and try again'}
                   
    except Admin.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'an admin account with the provided credentials does not exist, please check your account details and try again'}
                   
    except Teacher.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'a teacher account with the provided credentials does not exist, please check your account details and try again'}
    
    except Exception as e:
        error_message = str(e)

        log_audit(
            actor=requesting_account,
            action='CREATE',
            target_model='ASSESSMENT',
            outcome='ERROR',
            response=error_message,
            school=requesting_account.school
        )

        return {'error': error_message}
    

@database_sync_to_async
def form_data_for_attendance_register(user, role, details):

    try:
        if role not in ['PRINCIPAL', 'ADMIN', 'TEACHER']:
            return {"error": 'could not proccess your request.. your account either has insufficient permissions or is invalid for the action you are trying to perform'}

        # Get the appropriate model for the requesting user's role from the mapping.
        Model = role_specific_maps.account_access_control_mapping[role]

        # Build the queryset for the requesting account with the necessary related fields.
        requesting_account = Model.objects.select_related('school').prefetch_related('school__teachers__taught_classes').get(account_id=user)

        if details.get('class') == 'requesting my own classes data':
            classroom = Classroom.objects.get(teacher=requesting_account, register_class=True, school=requesting_account.school)

        elif details.get('class') and role in ['ADMIN', 'PRINCIPAL']:
            classroom = Classroom.objects.get(class_id=details.get('class'), register_class=True, school=requesting_account.school)

        else:
            return { "error" : 'unauthorized request.. only the class teacher or school admin can submit the attendance register for a class' }

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
    
    except BaseUser.DoesNotExist:
        return { 'error': 'account with the provided credentials does not exist' }
            
    except Classroom.DoesNotExist:
        return { 'error': 'class with the provided credentials does not exist' }

    except Exception as e:
        return { 'error': str(e) }

