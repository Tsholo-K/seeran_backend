# python
import base64
import zlib
import json

# channels
from channels.db import database_sync_to_async

# django
from django.db import models, transaction
from django.utils.translation import gettext as _

# models 
from accounts.models import Student
from classrooms.models import Classroom
from terms.models import Term
from assessment_transcripts.models import AssessmentTranscript
from timetables.models import Timetable
from student_activities.models import StudentActivity
from student_group_timetables.models import StudentGroupTimetable

# serilializers
from accounts.serializers.students.serializers import StudentBasicAccountDetailsEmailSerializer
from accounts.serializers.parents.serializers import ParentAccountSerializer
from student_subject_performances.serializers import StudentPerformanceSerializer
from school_announcements.serializers import AnnouncementSerializer
from terms.serializers import  TermsSerializer
from classrooms.serializers import ClassroomSerializer, ClassroomsSerializer
from school_attendances.serializers import StudentAttendanceSerializer
from assessment_transcripts.serializers import DetailedTranscriptSerializer
from timetables.serializers import TimetableSerializer
from student_group_timetables.serializers import StudentGroupTimetablesSerializer
from student_activities.serializers import ActivitiesSerializer, ActivitySerializer
from timetable_sessions.serializers import SessoinsSerializer

# checks
from accounts.checks import permission_checks

# mappings
from accounts.mappings import serializer_mappings

# utility functions 
from accounts import utils as accounts_utilities
from audit_logs import utils as audits_utilities


@database_sync_to_async
def search_parents(account, role, details):
    try:
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = accounts_utilities.get_account_and_linked_school(account, role)

        if 'account' not in details:
            response = f'could not proccess your request, the provided information is invalid for the action you are trying to perform. please make sure to provide a valid account ID and try again'
            return {'error': response}

        requested_account = requesting_account.school.students.select_related('school').prefetch_related('parents').get(account_id=details['account'])
    
        # Check if the requesting user has permission to view the requested user's profile or details.
        permission_error = permission_checks.view_account(requesting_account, requested_account)
        if permission_error:
            # Return an error message if the requesting user does not have the necessary permissions.
            return permission_error

        parents = requested_account.parents

        # Serialize the parents to return them in the response
        serialized_parents = ParentAccountSerializer(parents, many=True).data

        # Compress the serialized data
        compressed_parents = zlib.compress(json.dumps(serialized_parents).encode('utf-8'))
        # Encode compressed data as base64 for safe transport
        encoded_parents = base64.b64encode(compressed_parents).decode('utf-8')

        return {"parents": encoded_parents}
                       
    except Student.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'Could not process your request, a student account with the provided credentials in your school does not exist. Please review the account details and try again.'}

    except Exception as e:
        # Handle any other unexpected errors and return the error message.
        return {'error': str(e)}


@database_sync_to_async
def search_account(account, role, details):
    try:
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = accounts_utilities.get_account_and_linked_school(account, role)

        if not {'account', 'role', 'reason'}.issubset(details) or details['reason'] not in ['details', 'profile'] or details['role'] not in ['PRINCIPAL', 'ADMIN', 'TEACHER', 'STUDENT', 'PARENT']:
            response = f'could not proccess your request, the provided information is invalid for the action you are trying to perform. please make sure to provide a valid account ID, role and reason and try again'
            return {'error': response}

        # Build the queryset for the requested account with the necessary related fields.
        requested_account = accounts_utilities.get_account_and_permission_check_attr(details['account'], details['role'])

        # Check if the requesting user has permission to view the requested user's profile or details.
        permission_error = permission_checks.view_account(requesting_account, requested_account)
        if permission_error:
            # Return an error message if the requesting user does not have the necessary permissions.
            return permission_error

        # Handle the request based on the reason provided (either 'details' or 'profile').
        if details['reason'] == 'profile':
            # Get the appropriate serializer for the requested user's role.
            Serializer = serializer_mappings.account_profile[details['role']]
            # Serialize the requested user's details and return the serialized data.
            serialized_account = Serializer(instance=requested_account).data

        else:
            # Get the appropriate serializer for the requested user's role.
            Serializer = serializer_mappings.account_details[details['role']]
            # Serialize the requested user's details and return the serialized data.
            serialized_account = Serializer(instance=requested_account).data

        # Compress the serialized data
        compressed_account = zlib.compress(json.dumps(serialized_account).encode('utf-8'))
        # Encode compressed data as base64 for safe transport
        encoded_account = base64.b64encode(compressed_account).decode('utf-8')

        # Return the serialized user data if everything is successful.
        return {"account": encoded_account}
    
    except Exception as e:
        # Handle any other unexpected errors and return the error message.
        return {'error': str(e)}


@database_sync_to_async
def search_school_announcement(account, role, details):
    try:
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = accounts_utilities.get_account_and_linked_school(account, role)
        
        if not 'announcement' in details:
            response = f'could not proccess your request, the provided information is invalid for the action you are trying to perform. please make sure to provide a valid announcement ID and try again'
            return {'error': response}

        # Retrieve the specified announcement
        announcement = requesting_account.announcements.get(announcement_id=details.get('announcement'))

        # Check if the user is already in the reached list and add if not
        if not announcement.accounts_reached.filter(id=requesting_account.id).exists():
            with transaction.atomic():
                announcement.reached(account)

        # Serialize and return the announcement data
        serialized_announcement = AnnouncementSerializer(announcement).data

        return {'announcement': serialized_announcement}
    
    except Exception as e:
        # Handle any other unexpected errors
        return {'error': str(e)}


@database_sync_to_async
def search_grade_terms(account, role, details):
    try:
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = accounts_utilities.get_account(account, role)

        if not 'classroom' in details:
            response = f'could not proccess your request, the provided information is invalid for the action you are trying to perform. please make sure to provide valid classroom ID and try again'
            return {'error': response}

        # Fetch the specific classroom based on class_id and school
        classroom = Classroom.objects.get(classroom_id=details['classroom'], students__id__in=requesting_account.children.values_list('id', flat=True))

        # Prefetch related school terms to minimize database hits
        grade_terms = classroom.grade.terms.only('term_name', 'weight', 'start_date', 'end_date', 'term_id')
        serialized_terms = TermsSerializer(grade_terms, many=True).data
        
        # Return the serialized terms in a dictionary
        return {'terms': serialized_terms}
    
    except Classroom.DoesNotExist:
        # Handle case where the classroom does not exist
        return {'error': _('Could not process your request, a classroom with the provided details does not exist. Please review the classroom details and try again.')}

    except Exception as e:
        # Handle any unexpected errors with a general error message
        return {'error': str(e)}


@database_sync_to_async
def search_classroom(account, role, details):
    try:
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = accounts_utilities.get_account_and_linked_school(account, role)

        if not 'classroom' in details:
            response = f'could not proccess your request, the provided information is invalid for the action you are trying to perform. please make sure to provide valid classroom ID and try again'
            return {'error': response}

        # Fetch the specific classroom based on class_id and school
        classroom = requesting_account.enrolled_classrooms.get(classroom_id=details['classroom'])
        serialized_classroom = ClassroomSerializer(classroom).data

        return {"classroom": serialized_classroom}
    
    except Classroom.DoesNotExist:
        # Handle case where the classroom does not exist
        return {'error': _('Could not process your request, a classroom with the provided details does not exist. Please review the classroom details and try again.')}
    
    except Exception as e:
        # Handle any other unexpected errors
        return {'error': str(e)}


@database_sync_to_async
def search_student_classrooms(account, role, details):
    try:
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = accounts_utilities.get_account(account, role)

        if not {'account'}.issubset(details):
            response = f'could not proccess your request, the provided information is invalid for the action you are trying to perform. please make sure to provide valid account ID and try again'
            return {'error': response}

        # Fetch the specific classroom based on class_id and school
        child = requesting_account.children.get(account_id=details['account'])

        serialized_child = StudentBasicAccountDetailsEmailSerializer(child).data
        serialized_child_classrooms = ClassroomsSerializer(child.enrolled_classrooms, many=True).data
        
        # Return the serialized terms in a dictionary
        return {'student' : serialized_child, 'classrooms': serialized_child_classrooms}
                   
    except Student.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'Could not process your request, a student account with the provided credentials does not exist. Please review your account details and try again.'}

    except Exception as e:
        # Handle any unexpected errors with a general error message
        return {'error': str(e)}


@database_sync_to_async
def search_student_classroom_performance(account, role, details):
    try:
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = accounts_utilities.get_account(account, role)

        if not {'term', 'classroom', 'student'}.issubset(details):
            response = f'could not proccess your request, the provided information is invalid for the action you are trying to perform. please make sure to provide valid student, term and classroom IDs and try again'
            return {'error': response}

        student = requesting_account.children.get(account_id=details['student'])
        # Fetch the specific classroom based on class_id and school
        classroom = Classroom.objects.get(classroom_id=details['classroom'], register_classroom=False, students=student)
        term = classroom.grade.terms.get(term_id=details['term'])

        student_performance, created = student.subject_performances.only(
            'pass_rate', 'highest_score', 'lowest_score', 'average_score', 'median_score', 'completion_rate', 'mode_score', 'passed'
        ).get_or_create(term=term, subject=classroom.subject, grade=classroom.grade, defaults={'school': student.school, 'student': student})
        serialized_student_performance = StudentPerformanceSerializer(student_performance).data
        
        # Return the serialized terms in a dictionary
        return {'performance': serialized_student_performance}
    
    except Classroom.DoesNotExist:
        # Handle case where the subject does not exist
        return {'error': 'Could not process your request, a classroom in your school with the provided credentials does not exist, please review the classroom details and try again.'}
    
    except Term.DoesNotExist:
        # Handle the case where the provided term ID does not exist
        return {'error': 'Could not process your request, a term in your school with the provided credentials does not exist, please review the term details and try again.'}

    except Exception as e:
        # Handle any unexpected errors with a general error message
        return {'error': str(e)}


@database_sync_to_async
def search_student_attendance(account, role, details):
    try:
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = accounts_utilities.get_account(account, role)

        if not {'classroom', 'student'}.issubset(details):
            response = f'could not proccess your request, the provided information is invalid for the action you are trying to perform. please make sure to provide a valid student and classroom IDs and try again'
            return {'error': response}

        student = requesting_account.children.get(account_id=details['student'])
        classroom = student.enrolled_classrooms.get(classroom_id=details['classroom'], register_classroom=True)

        # Query for the Absent instances where absentes is True
        attendances = []
        attendances.extend(student.absences.all())
        days_absent = student.absences.count()
        attendances.extend(student.late_arrivals.all())

        # Now sort the combined attendances list by 'timestamp'
        sorted_attendances = sorted(attendances, key=lambda attendance: attendance.timestamp, reverse=True)

        # For each absent instance, get the corresponding Late instance
        attendance_records = StudentAttendanceSerializer(sorted_attendances, many=True, context={'student': student.id}).data

        # Compress the serialized data
        compressed_attendance_records = zlib.compress(json.dumps({'records': attendance_records, 'days_absent': days_absent}).encode('utf-8'))

        # Encode compressed data as base64 for safe transport
        encoded_attendance_records = base64.b64encode(compressed_attendance_records).decode('utf-8')

        return {'records': encoded_attendance_records}
    
    except Classroom.DoesNotExist:
        return {'error': 'Could not process your request, a classroom in your school with the provided credentials does not exist. Please check the classrooms details and try again.'}
                   
    except Student.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'Could not process your request, a student account with the provided credentials does not exist. Please review your account details and try again.'}

    except Exception as e:
        return {'error': str(e)}


@database_sync_to_async
def search_student_assessment_transcript(account, role, details):
    try:
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = accounts_utilities.get_account_and_permission_check_attr(account, role)

        if not {'term', 'classroom', 'assessment'}.issubset(details):
            response = f'could not proccess your request, the provided information is invalid for the action you are trying to perform. please make sure to provide valid term, classroom and assessment IDs and try again'
            return {'error': response}

        classroom = requesting_account.enrolled_classrooms.get(classroom_id=details['classroom'])

        assessment = requesting_account.school.assessments.get(models.Q(releasing_grades=True) | models.Q(grades_released=True), term__term_id=details['term'], assessment_id=details['assessment'], subject=classroom.subject, grade=classroom.grade,)
        transcript = assessment.transcripts.get(student=requesting_account)

        serialized_transcript = DetailedTranscriptSerializer(transcript).data 

        return {"transcript": serialized_transcript}

    except Classroom.DoesNotExist:
        # Handle case where the classroom does not exist
        return {'error': _('Could not process your request, classroom in your school with the provided details does not exist. Please review the classroom details and try again.')}

    except AssessmentTranscript.DoesNotExist:
        # Handle the case where the provided assessment ID does not exist
        return { 'error': 'Could not process your request, a transcript in your school with the provided credentials does not exist, please review the transcript details and try again.'}
        
    except Exception as e:
        # Handle any other unexpected errors
        return {'error': str(e)}


@database_sync_to_async
def search_student_classroom_card(account, role, details):
    try:
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = accounts_utilities.get_account(account, role)

        if not {'account', 'classroom'}.issubset(details):
            response = f'could not proccess your request, the provided information is invalid for the action you are trying to perform. please make sure to provide valid account and classroom IDs and try again'
            return {'error': response}

        # Retrieve the requested users account and related school in a single query using select_related
        requested_account = requesting_account.children.get(account_id=details['account'])

        classroom = requested_account.enrolled_classrooms.get(classroom_id=details['classroom'])

        # retrieve the students activities 
        activities = requested_account.my_activities.filter(classroom=classroom)
        
        serialized_student = StudentBasicAccountDetailsEmailSerializer(instance=requested_account).data
        serialized_activities = ActivitiesSerializer(activities, many=True).data

        return {"student": serialized_student, 'activities': serialized_activities}

    except Classroom.DoesNotExist:
        # Handle case where the classroom does not exist
        return {'error': 'Could not process your request, a classroom in your school with the provided credentials does not exist. please review the classroom details and try again.'}
                   
    except Student.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'Could not process your request, a student account with the provided credentials does not exist. Please review your account details and try again.'}

    except Exception as e:
        # Handle any other unexpected errors
        return {'error': str(e)}



@database_sync_to_async
def search_student_activity(account, role, details):
    try:
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = accounts_utilities.get_account(account, role)

        if not {'activity'}.issubset(details):
            response = f'could not proccess your request, the provided information is invalid for the action you are trying to perform. please make sure to provide valid account and classroom IDs and try again'
            return {'error': response}

        # Retrieve the activity based on the provided activity_id
        activity = StudentActivity.objects.select_related('auditor', 'recipient', 'classroom', 'school').get(student_activity_id=details['activity'], recipient_id__in=requesting_account.children.values_list('id', flat=True))
        serialized_activity = ActivitySerializer(activity).data

        return {"activity": serialized_activity}

    except StudentActivity.DoesNotExist:
        # Handle case where the activity does not exist
        return {'error': 'Could not process your request, an activity in your school with the provided credentials does not exist. Please review the activity details and try again.'}

    except Exception as e:
        # Handle any other unexpected errors
        return {'error': str(e)}
    

@database_sync_to_async
def search_group_timetables(account, role):
    try:
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = accounts_utilities.get_account(account, role)
        
        # Retrieve all group schedules associated with the student
        if hasattr(requesting_account, 'timetables'):
            group_timetables = requesting_account.timetables
        else:
            return {"timetables": []}

        # Serialize the group schedules to return them in the response
        serialized_timetables = StudentGroupTimetablesSerializer(group_timetables, many=True).data

        return {"timetables": serialized_timetables}

    except Exception as e:
        # Handle any other unexpected errors
        return {'error': str(e)}


@database_sync_to_async
def search_group_timetable_timetables(account, role, details):
    try:
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = accounts_utilities.get_account(account, role)

        if 'group_timetable' not in details:
            response = f'could not proccess your request, the provided information is invalid for the action you are trying to perform. please make sure to provide a valid group timetable ID and try again'
            return {'error': response}

        # Retrieve the specified group schedule
        group_timetable = requesting_account.timetables.prefetch_related('timetables').get(group_timetable_id=details['group_timetable'])
        serialized_timetables = TimetableSerializer(group_timetable.timetables, many=True).data

        return {"timetables": serialized_timetables}
    
    except StudentGroupTimetable.DoesNotExist:
        # Handle case where the group schedule does not exist
        return {'error': 'Could not process your request, a group schedule with the provided credentials does not exist. Please check the group schedule details and try again.'}
    
    except Exception as e:
        # Handle any other unexpected errors
        return {'error': str(e)}


@database_sync_to_async
def search_timetable_sessions(account, role, details):
    try:
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = accounts_utilities.get_account_and_linked_school(account, role)

        if 'timetable' not in details:
            response = f'could not proccess your request, the provided information is invalid for the action you are trying to perform. please make sure to provide a valid timetable ID and try again'
            return {'error': response}

        timetable = requesting_account.school.timetables.prefetch_related('sessions').get(timetable_id=details['timetable'], student_group_timetable__subscribers=requesting_account)
        serialized_sessions = SessoinsSerializer(timetable.sessions, many=True).data
        
        return {"sessions": serialized_sessions}
    
    except Timetable.DoesNotExist:
        return {"error" : "a schedule with the provided credentials does not exist"}
    
    except Exception as e:
        return { 'error': str(e) }


