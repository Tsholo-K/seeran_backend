# python 
from datetime import datetime

# channels
from channels.db import database_sync_to_async

# django
from django.db.models import Prefetch
from django.utils.translation import gettext as _
from django.db.models import Q

# models 
from users.models import Teacher
from schools.models import School
from grades.models import Grade
from terms.models import Term
from subjects.models import Subject
from classes.models import Classroom
from attendances.models import Attendance
from student_group_timetables.models import StudentGroupTimetable

# serilializers
from users.serializers.principals.principals_serializers import PrincipalAccountSerializer
from users.serializers.students.students_serializers import StudentSourceAccountSerializer, LeastAccountDetailsSerializer
from users.serializers.admins.admins_serializers import AdminAccountSerializer
from users.serializers.teachers.teachers_serializers import TeacherAccountSerializer
from schools.serializers import SchoolDetailsSerializer
from audit_logs.serializers import AuditEntriesSerializer, AuditEntrySerializer
from grades.serializers import GradeSerializer, GradesSerializer, GradeDetailsSerializer
from terms.serializers import  TermsSerializer, TermSerializer, ClassesSerializer
from subjects.serializers import SubjectSerializer, SubjectDetailsSerializer
from classes.serializers import TeacherClassesSerializer
from assessments.serializers import DueAssessmentsSerializer, CollectedAssessmentsSerializer
from activities.serializers import ActivitiesSerializer
from daily_schedules.serializers import DailyScheduleSerializer

# checks
from users.checks import permission_checks

# utility functions 
from users import utils as users_utilities
from permissions import utils as permissions_utilities
from audit_logs import utils as audits_utilities
from attendances import utils as attendances_utilities
    
    
@database_sync_to_async
def search_school_details(user, role):
    try:
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = users_utilities.get_account_and_linked_school(user, role)

        # Serialize the school object into a dictionary
        serialized_school = SchoolDetailsSerializer(requesting_account.school).data
        
        return {"school": serialized_school}

    except School.DoesNotExist:
        # Handle the case where the provided school ID does not exist
        return {"error": "a school with the provided credentials does not exist"}

    except Exception as e:
        # Handle any unexpected errors with a general error message
        return {'error': str(e)}


@database_sync_to_async
def search_audit_entries(user, role, details):
    try:
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = users_utilities.get_account_and_linked_school(user, role)

        # Check if the user has permission to create an assessment
        if role != 'PRINCIPAL' and not permissions_utilities.has_permission(requesting_account, 'VIEW', 'AUDIT_ENTRIES'):
            response = f'could not proccess your request, you do not have the necessary permissions to view audit entries. please contact your administrator to adjust you permissions for viewing audit entries.'
            audits_utilities.log_audit(actor=requesting_account, action='VIEW', target_model='AUDIT_ENTRIES', outcome='DENIED', response=response, school=requesting_account.school)

            return {'error': response}
        
        entries = requesting_account.school.audit_logs.only('actor', 'actor__name', 'actor__surname', 'outcome', 'target_model', 'timestamp', 'audit_id').filter(action=details.get('action'))
        serialized_entries = AuditEntriesSerializer(instance=entries, many=True).data

        return {"entries": serialized_entries}

    except Exception as e:
        # Handle any unexpected errors with a general error message
        return {'error': str(e)}


@database_sync_to_async
def search_audit_entry(user, role, details):
    try:
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = users_utilities.get_account_and_linked_school(user, role)

        # Check if the user has permission to create an assessment
        if role != 'PRINCIPAL' and not permissions_utilities.has_permission(requesting_account, 'VIEW', 'AUDIT_ENTRIES'):
            response = f'could not proccess your request, you do not have the necessary permissions to view audit entries. please contact your administrator to adjust you permissions for viewing audit entries.'
            audits_utilities.log_audit(actor=requesting_account, action='VIEW', target_model='AUDIT_ENTRIES', outcome='DENIED', response=response, school=requesting_account.school)

            return {'error': response}
        
        entries = requesting_account.school.audit_logs.only('actor', 'outcome', 'target_model', 'response', 'timestamp').get(audit_id=details.get('entry'))
        serialized_entry = AuditEntrySerializer(instance=entries).data

        return {"entry": serialized_entry}

    except Exception as e:
        # Handle any unexpected errors with a general error message
        return {'error': str(e)}


@database_sync_to_async
def search_grades(user, role, details):
    try:
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = users_utilities.get_account_and_linked_school(user, role)
        
        if details.get('time_stamp'):
            # Convert the timestamp to a string in ISO format
            time_stamp = datetime.fromtimestamp((details['time_stamp'] + 1) / 1000).isoformat()
            # Filter grades created after the given timestamp
            grades = requesting_account.school.grades.filter(created__gt=time_stamp)            
        
        else:
            grades = requesting_account.school.grades.all()

        # Serialize the grade objects into a dictionary
        serialized_grades = GradesSerializer(grades, many=True).data

        return {'grades': serialized_grades}

    except Exception as e:
        # Handle any unexpected errors with a general error message
        return {'error': str(e)}
    

@database_sync_to_async
def search_grade(user, role, details):
    try:
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = users_utilities.get_account_and_linked_school(user, role)

        grade  = Grade.objects.get(grade_id=details.get('grade'), school=requesting_account.school)

        serialized_grade = GradeSerializer(instance=grade).data

        return {'grade' : serialized_grade}
    
    except Grade.DoesNotExist:
        # Handle the case where the provided grade ID does not exist
        return {'error': 'a grade in your school with the provided credentials does not exist, please check the grade details and try again'}

    except Exception as e:
        # Handle any unexpected errors with a general error message
        return {'error': str(e)}


@database_sync_to_async
def search_grade_details(user, role, details):
    try:
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = users_utilities.get_account_and_linked_school(user, role)

        grade = Grade.objects.get(grade_id=details.get('grade'), school=requesting_account.school)
        
        # Serialize the grade
        serialized_grade = GradeDetailsSerializer(grade).data
        
        # Return the serialized grade in a dictionary
        return {'grade': serialized_grade}
    
    except Grade.DoesNotExist:
        # Handle the case where the provided grade ID does not exist
        return {'error': 'a grade in your school with the provided credentials does not exist, please check the grade details and try again'}

    except Exception as e:
        # Handle any unexpected errors with a general error message
        return {'error': f'An unexpected error occurred: {str(e)}'}


@database_sync_to_async
def search_grade_terms(user, role, details):
    try:
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = users_utilities.get_account_and_linked_school(user, role)

        # Prefetch related school terms to minimize database hits
        grade_terms = requesting_account.school.terms.all()
        
        # Serialize the school terms
        serialized_terms = TermsSerializer(grade_terms, many=True).data
        
        # Return the serialized terms in a dictionary
        return {'terms': serialized_terms}
    
    except Grade.DoesNotExist:
        # Handle the case where the provided grade ID does not exist
        return {'error': 'a grade in your school with the provided credentials does not exist, please check the grade details and try again'}

    except Exception as e:
        # Handle any unexpected errors with a general error message
        return {'error': f'An unexpected error occurred: {str(e)}'}


@database_sync_to_async
def search_grade_register_classes(user, role, details):
    try:
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = users_utilities.get_account_and_linked_school(user, role)

        grade  = Grade.objects.prefetch_related(Prefetch('classes', queryset=Classroom.objects.filter(register_class=True))).get(grade_id=details.get('grade_id'), school=requesting_account.school)
        classes = grade.classes.all()

        serialized_classes = ClassesSerializer(classes, many=True).data

        return {"classes": serialized_classes}
    
    except Grade.DoesNotExist:
        # Handle the case where the provided grade ID does not exist
        return {'error': 'a grade in your school with the provided credentials does not exist, please check the grade details and try again'}

    except Exception as e:
        # Handle any unexpected errors with a general error message
        return {'error': str(e)}
    

@database_sync_to_async
def search_term_details(user, role, details):
    try:
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = users_utilities.get_account_and_linked_school(user, role)

        term = Term.objects.get(term_id=details.get('term'), school=requesting_account.school)
        
        # Serialize the school terms
        serialized_term = TermSerializer(term).data
        
        # Return the serialized terms in a dictionary
        return {'term': serialized_term}
    
    except Term.DoesNotExist:
        # Handle the case where the provided term ID does not exist
        return {'error': 'a term in your school with the provided credentials does not exist, please check the term details and try again'}

    except Exception as e:
        # Handle any unexpected errors with a general error message
        return {'error': f'An unexpected error occurred: {str(e)}'}


@database_sync_to_async
def search_subject(user, role, details):
    try:
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = users_utilities.get_account_and_linked_school(user, role)

        # Retrieve the subject and its related grade
        subject = Subject.objects.get(subject_id=details.get('subject'), grade__school=requesting_account.school)

        # Serialize the subject data
        serialized_subject = SubjectSerializer(subject).data

        return {"subject": serialized_subject}
    
    except Subject.DoesNotExist:
        # Handle case where the subject does not exist
        return {'error': 'a subject in your school with the provided credentials does not exist, please check the subject details and try again'}

    except Exception as e:
        # Handle any unexpected errors with a general error message
        return {'error': str(e)}


@database_sync_to_async
def search_subject_details(user, role, details):
    try:
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = users_utilities.get_account_and_linked_school(user, role)

        subject = Subject.objects.get(subject_id=details.get('subject'), grade__school=requesting_account.school)
        
        # Serialize the subject
        serialized_subject = SubjectDetailsSerializer(subject).data
        
        # Return the serialized grade in a dictionary
        return {'subject': serialized_subject}
    
    except Subject.DoesNotExist:
        # Handle case where the subject does not exist
        return {'error': 'a subject in your school with the provided credentials does not exist, please check the subject details and try again'}

    except Exception as e:
        # Handle any unexpected errors with a general error message
        return {'error': f'An unexpected error occurred: {str(e)}'}


@database_sync_to_async
def search_assessments(user, role, details):
    try:
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = users_utilities.get_account_and_linked_school(user, role)
        
        # Check if the user has permission to create an assessment
        if role != 'PRINCIPAL' and not permissions_utilities.has_permission(requesting_account, 'VIEW', 'ASSESSMENTS'):
            response = f'could not proccess your request, you do not have the necessary permissions to view assessments. please contact your principal to adjust you permissions for viewing assessments.'
            audits_utilities.log_audit(actor=requesting_account, action='VIEW', target_model='ASSESSMENTS', outcome='DENIED', response=response, school=requesting_account.school)

            return {'error': response}
        
        # Determine the classroom based on the request details
        if details.get('grade') and  details.get('subject'):
            grade = requesting_account.school.grades.get(grade_id=details['grade'])
            subject = grade.subjects.get(subject_id=details['subject'])

            assessments = subject.assessments.filter(collected=details.get('collected'), grades_released=False)

        elif details.get('classroom'):
            # Fetch the specific classroom based on classroom_id and school
            classroom = requesting_account.school.classes.get(classroom_id=details['classroom'])
        
            assessments = classroom.assessments.filter(collected=details.get('collected'), grades_released=False)

        else:
            return {"error": 'invalid request'}
        
        if not assessments:
            return {"assessments": []}

        # Serialize and return the assessments data
        serialized_assessments = CollectedAssessmentsSerializer(assessments, many=True).data if details.get('collected') else DueAssessmentsSerializer(assessments, many=True).data

        return {"assessments": serialized_assessments}
        
    except Grade.DoesNotExist:
        # Handle the case where the provided grade ID does not exist
        return { 'error': 'a grade in your school with the provided credentials does not exist, please check the grade details and try again'}
    
    except Subject.DoesNotExist:
        # Handle case where the subject does not exist
        return {'error': 'a subject in your school with the provided credentials does not exist, please check the subject details and try again'}

    except Classroom.DoesNotExist:
        # Handle case where the classroom does not exist
        return {'error': _('A classroom in your school with the provided details does not exist. Please check the classroom details and try again.')}
    
    except Exception as e:
        # Handle any other unexpected errors
        return {'error': str(e)}


@database_sync_to_async
def search_accounts(user, role, details):
    try:
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = users_utilities.get_account_and_linked_school(user, role)

        if details.get('role') == 'admins':
            # Fetch all admin accounts in the school
            admins = requesting_account.school.admins.all().exclude(account_id=user)
            serialized_accounts = AdminAccountSerializer(admins, many=True).data

            # If the user is not a principal, exclude them from the results
            if role != 'PRINCIPAL':
                principal = requesting_account.school.principal
                if principal:
                    serialized_principal = PrincipalAccountSerializer(principal).data
                    serialized_accounts.append(serialized_principal)

        elif details.get('role') == 'teachers':
            # Fetch all teacher accounts in the school, excluding the current user
            teachers = requesting_account.school.teachers.all()
            serialized_accounts = TeacherAccountSerializer(teachers, many=True).data

        else:
            return {"error": "could not proccess your request, the role specified is invalid"}

        return {"users": serialized_accounts}

    except Exception as e:
        # Handle any unexpected errors with a general error message
        return {'error': str(e)} 
    

@database_sync_to_async
def search_students(user, role, details):
    try:
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = users_utilities.get_account_and_linked_school(user, role)

        grade = Grade.objects.prefetch_related('students').get(grade_id=details.get('grade'), school=requesting_account.school.pk)
        serialized_students = StudentSourceAccountSerializer(grade.students.all(), many=True).data

        return {"students": serialized_students}
    
    except Grade.DoesNotExist:
        # Handle the case where the provided grade ID does not exist
        return { 'error': 'a grade in your school with the provided credentials does not exist, please check the grade details and try again'}

    except Exception as e:
        # Handle any unexpected errors with a general error message
        return {'error': str(e)}


@database_sync_to_async
def search_student_class_card(user, role, details):
    try:
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = users_utilities.get_account_and_attr(user, role)

        # Retrieve the requested users account and related school in a single query using select_related
        requested_account = users_utilities.get_account_and_attr(details.get('account'), 'STUDENT')

        # Check permissions
        permission_error = permission_checks.check_profile_or_details_view_permissions(requesting_account, requested_account)
        if permission_error:
            return permission_error
        
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


@database_sync_to_async
def search_subscribed_students(user, role, details):
    try:
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = users_utilities.get_account_and_linked_school(user, role)

        # Retrieve the group schedule
        group_schedule = StudentGroupTimetable.objects.prefetch_related('students').get(group_schedule_id=details.get('group_schedule_id'), grade__school=requesting_account.school)

        # Get all students subscribed to this group schedule
        students = group_schedule.students.all()
        serialized_students = StudentSourceAccountSerializer(students, many=True).data

        return {"students": serialized_students}
                
    except StudentGroupTimetable.DoesNotExist:
        return {'error': 'a group schedule in your school with the provided credentials does not exist. Please check the group schedule details and try again.'}

    except Exception as e:
        # Handle any unexpected errors with a general error message
        return {'error': str(e)}


@database_sync_to_async
def search_month_attendance_records(user, role, details):
    try:
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = users_utilities.get_account_and_linked_school(user, role)
 
        classroom = Classroom.objects.get(class_id=details.get('class'), school=requesting_account.school, register_class=True)
        
        start_date, end_date = attendances_utilities.get_month_dates(details.get('month_name'))

        # Query for the Absent instances where absentes is True
        absents = Attendance.objects.prefetch_related('absent_students').filter(Q(date__gte=start_date) & Q(date__lt=end_date) & Q(classroom=classroom) & Q(absentes=True))

        # For each absent instance, get the corresponding Late instance
        attendance_records = []
        for absent in absents:
            late = Attendance.objects.prefetch_related('late_students').filter(date__date=absent.date.date(), classroom=classroom).first()
            record = {
                'date': absent.date.isoformat(),
                'absent_students': LeastAccountDetailsSerializer(absent.absent_students.all(), many=True).data,
                'late_students': LeastAccountDetailsSerializer(late.late_students.all(), many=True).data if late else [],
            }
            attendance_records.append(record)

        return {'records': attendance_records}
    
    except Classroom.DoesNotExist:
        return { 'error': 'a classroom in your school with the provided credentials does not exist' }

    except Exception as e:
        return { 'error': str(e) }


@database_sync_to_async
def search_teacher_classes(user, role, details):
    try:
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = users_utilities.get_account_and_linked_school(user, role)

        teacher = Teacher.objects.prefetch_related('taught_classes').get(account_id=details.get('teacher'), school=requesting_account.school)
        classes = teacher.taught_classes

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
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = users_utilities.get_account_and_linked_school(user, role)

        teacher = Teacher.objects.prefetch_related('teacher_schedule__schedules').get(account_id=details.get('teacher'), school=requesting_account.school)

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
