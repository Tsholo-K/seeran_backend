# python 

# httpx

# channels
from channels.db import database_sync_to_async

# django
from django.utils import timezone
from django.utils.translation import gettext as _

# simple jwt

# models 
from users.models import BaseUser
from classes.models import Classroom
from attendances.models import Absent

# serializers
from users.serializers import AccountSerializer

# utility functions 

# checks


@database_sync_to_async
def form_data_for_assessment_setting(user, details):

    try:
        account = BaseUser.objects.get(account_id=user)

        if details.get('class_id') == 'requesting_my_own_class':
            classroom = Classroom.objects.select_related('school').get(teacher=account, register_class=True)

            if account.role != 'TEACHER' or classroom.school != account.school:
                return {"error": "unauthorized access. the account making the request has an invalid role or the classroom you are trying to access is not from your school"}

        else:
            if account.role not in ['ADMIN', 'PRINCIPAL']:
                return { "error" : 'unauthorized request.. only the class teacher or school admin can submit the attendance register for a class' }

            classroom = Classroom.objects.get(class_id=details.get('class_id'), register_class=True, school=account.school)
        
        # Get today's date
        today = timezone.localdate()
            
        # Check if an Absent instance exists for today and the given class
        attendance = Absent.objects.filter(date__date=today, classroom=classroom).first()

        if attendance:
            students = attendance.absent_students.all()
            attendance_register_taken = True

        else:
            students = classroom.students.all()
            attendance_register_taken = False

        serializer = AccountSerializer(students, many=True)

        return {"students": serializer.data, "attendance_register_taken" : attendance_register_taken}
    
    except BaseUser.DoesNotExist:
        return { 'error': 'account with the provided credentials does not exist' }
            
    except Classroom.DoesNotExist:
        return { 'error': 'class with the provided credentials does not exist' }

    except Exception as e:
        return { 'error': str(e) }
    

@database_sync_to_async
def form_data_for_attendance_register(user, details):

    try:
        account = BaseUser.objects.get(account_id=user)

        if details.get('class_id') == 'requesting_my_own_class':
            classroom = Classroom.objects.select_related('school').get(teacher=account, register_class=True)

            if account.role != 'TEACHER' or classroom.school != account.school:
                return {"error": "unauthorized access. the account making the request has an invalid role or the classroom you are trying to access is not from your school"}

        else:
            if account.role not in ['ADMIN', 'PRINCIPAL']:
                return { "error" : 'unauthorized request.. only the class teacher or school admin can submit the attendance register for a class' }

            classroom = Classroom.objects.get(class_id=details.get('class_id'), register_class=True, school=account.school)
        
        # Get today's date
        today = timezone.localdate()
            
        # Check if an Absent instance exists for today and the given class
        attendance = Absent.objects.filter(date__date=today, classroom=classroom).first()

        if attendance:
            students = attendance.absent_students.all()
            attendance_register_taken = True

        else:
            students = classroom.students.all()
            attendance_register_taken = False

        serializer = AccountSerializer(students, many=True)

        return {"students": serializer.data, "attendance_register_taken" : attendance_register_taken}
    
    except BaseUser.DoesNotExist:
        return { 'error': 'account with the provided credentials does not exist' }
            
    except Classroom.DoesNotExist:
        return { 'error': 'class with the provided credentials does not exist' }

    except Exception as e:
        return { 'error': str(e) }

