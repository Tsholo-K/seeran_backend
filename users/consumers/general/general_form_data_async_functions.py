# channels
from channels.db import database_sync_to_async

# django
from django.utils import timezone
from django.utils.translation import gettext as _

# models 
from users.models import BaseUser
from classrooms.models import Classroom
from attendances.models import Attendance

# serializers
from users.serializers.students.students_serializers import StudentSourceAccountSerializer

# mappings
from users.maps import role_specific_maps
    

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

