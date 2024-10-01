# channels
from channels.db import database_sync_to_async

# django
from django.utils.translation import gettext as _
from django.db.models import Q

# models 
from accounts.models import Teacher
from classrooms.models import Classroom
from school_attendances.models import SchoolAttendance

# serilializers
from accounts.serializers.students.serializers import StudentSourceAccountSerializer, LeastAccountDetailsSerializer
from classrooms.serializers import TeacherClassesSerializer
from assessments.serializers import DueAssessmentsSerializer, CollectedAssessmentsSerializer
from student_activities.serializers import ActivitiesSerializer
from timetables.serializers import DailyScheduleSerializer

# checks
from accounts.checks import permission_checks

# utility functions 
from accounts import utils as users_utilities
from account_permissions import utils as permissions_utilities
from audit_logs import utils as audits_utilities
from school_attendances import utils as attendances_utilities


@database_sync_to_async
def search_assessments(user, details):
    try:
        # Build the queryset for the requesting account with the necessary related fields.
        requesting_account = Teacher.objects.select_related('school').get(account_id=user)
        
        # Check if the user has permission to create an assessment
        if not permissions_utilities.has_permission(requesting_account, 'VIEW', 'ASSESSMENTS'):
            response = f'could not proccess your request, you do not have the necessary permissions to view assessments. please contact your administrators to adjust you permissions for viewing assessments.'
            audits_utilities.log_audit(actor=requesting_account, action='VIEW', target_model='ASSESSMENTS', outcome='DENIED', response=response, school=requesting_account.school)

            return {'error': response}
        
        # Fetch the specific classroom based on classroom_id and school
        classroom = requesting_account.taught_classes.get(classroom_id=details['classroom'])
        assessments = classroom.assessments.filter(collected=details.get('collected'), grades_released=False)
        
        if not assessments:
            return {"assessments": []}

        # Serialize and return the assessments data
        serialized_assessments = CollectedAssessmentsSerializer(assessments, many=True).data if details.get('collected') else DueAssessmentsSerializer(assessments, many=True).data

        return {"assessments": serialized_assessments}

    except Classroom.DoesNotExist:
        # Handle case where the classroom does not exist
        return {'error': _('A classroom in your school with the provided details does not exist. Please check the classroom details and try again.')}
    
    except Exception as e:
        # Handle any other unexpected errors
        return {'error': str(e)}


@database_sync_to_async
def search_month_attendance_records(user, details):
    try:
        # Build the queryset for the requesting account with the necessary related fields.
        requesting_account = Teacher.objects.select_related('school').get(account_id=user)

        classroom = requesting_account.taught_classes.filter(register_class=True).first()
        if not classroom:
            return {"error": _("could not proccess your request. the account making the request has no register class assigned to it")}
        
        start_date, end_date = attendances_utilities.get_month_dates(details.get('month_name'))

        # Query for the Absent instances where absentes is True
        absents = SchoolAttendance.objects.prefetch_related('absent_students').filter(Q(date__gte=start_date) & Q(date__lt=end_date) & Q(classroom=classroom) & Q(absentes=True))

        # For each absent instance, get the corresponding Late instance
        attendance_records = []
        for absent in absents:
            late = SchoolAttendance.objects.prefetch_related('late_students').filter(date__date=absent.date.date(), classroom=classroom).first()
            record = {
                'date': absent.date.isoformat(),
                'absent_students': LeastAccountDetailsSerializer(absent.absent_students.all(), many=True).data,
                'late_students': LeastAccountDetailsSerializer(late.late_students.all(), many=True).data if late else [],
            }
            attendance_records.append(record)

        return {'records': attendance_records}
               
    except Teacher.DoesNotExist:
        # Handle the case where the requested teacher account does not exist.
        return {'error': 'A teacher account with the provided credentials does not exist, please check the account details and try again'}
    
    except Classroom.DoesNotExist:
        return { 'error': 'a classroom in your school with the provided credentials does not exist' }

    except Exception as e:
        return { 'error': str(e) }


@database_sync_to_async
def search_teacher_classes(user):
    try:
        requesting_account = Teacher.objects.prefetch_related('taught_classes').get(account_id=user)
        classes = requesting_account.taught_classes.exclude(register_class=True)

        serializer = TeacherClassesSerializer(classes, many=True)

        return {"classes": serializer.data}
               
    except Teacher.DoesNotExist:
        # Handle the case where the requested teacher account does not exist.
        return {'error': 'A teacher account with the provided credentials does not exist, please check the account details and try again'}
    
    except Exception as e:
        return { 'error': str(e) }


@database_sync_to_async
def search_teacher_schedule_schedules(user, role, details):
    try:
        teacher = Teacher.objects.prefetch_related('teacher_schedule__schedules').get(account_id=user)

        # Check if the teacher has a schedule
        if hasattr(teacher, 'teacher_schedule'):
            schedules = teacher.teacher_schedule.schedules.all()

        else:
            return {'schedules': []}
        
        # Serialize the schedules to return them in the response
        serialized_schedules = DailyScheduleSerializer(schedules, many=True).data

        return {"schedules": serialized_schedules}
               
    except Teacher.DoesNotExist:
        # Handle the case where the requested teacher account does not exist.
        return {'error': 'A teacher account with the provided credentials does not exist, please check the account details and try again'}
    
    except Exception as e:
        # Handle any other unexpected errors
        return {'error': str(e)}


@database_sync_to_async
def search_student_class_card(user, role, details):
    try:
        # Retrieve the requesting users account and related attr
        requesting_account = users_utilities.get_account_and_attr(user, role)

        # Retrieve the requested users account and related attr
        requested_account = users_utilities.get_account_and_attr(user, role)

        # Check permissions
        permission_error = permission_checks.check_profile_or_details_view_permissions(requesting_account, requested_account)
        if permission_error:
            return permission_error
        
        # Determine the classroom based on the request details
        if details.get('class') == 'requesting my own class data':
            # Fetch the classroom where the user is the teacher and it is a register class
            classroom = requesting_account.taught_classes.filter(register_class=True).first()
            if classroom is None:
                return {"error": _("could not proccess your request. the account making the request has no register class assigned to it")}

        else:
            # Fetch the specific classroom based on class_id and school
            classroom = Classroom.objects.get(classroom_id=details.get('classroom'), school=requesting_account.school)

        # retrieve the students activities 
        activities = requested_account.my_activities.filter(classroom=classroom)
        
        serialized_student = StudentSourceAccountSerializer(instance=requested_account).data
        serialized_activities = ActivitiesSerializer(activities, many=True).data

        return {"user": serialized_student, 'activities': serialized_activities}

    except Classroom.DoesNotExist:
        # Handle case where the classroom does not exist
        return {'error': 'a classroom in your school with the provided credentials does not exist. please check the classroom details and try again.'}

    except Exception as e:
        # Handle any other unexpected errors
        return {'error': str(e)}