# python 
from datetime import datetime

# channels
from channels.db import database_sync_to_async

# django
from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_time
from django.core.exceptions import ValidationError

# models 
from users.models import BaseUser, Principal, Admin, Teacher, Student, Parent
from permission_groups.models import AdminPermissionGroup, TeacherPermissionGroup
from permissions.models import AdminPermission, TeacherPermission
from announcements.models import Announcement
from grades.models import Grade
from terms.models import Term
from subjects.models import Subject
from classrooms.models import Classroom
from attendances.models import Attendance
from assessments.models import Assessment
from submissions.models import Submission
from transcripts.models import Transcript
from assessments.models import Topic
from activities.models import Activity
from daily_schedule_sessions.models import DailyScheduleSession
from student_group_timetables.models import StudentGroupTimetable
from teacher_timetables.models import TeacherTimetable
from daily_schedules.models import DailySchedule

# serilializers
from users.serializers.parents.parents_serializers import ParentAccountCreationSerializer
from permission_groups.serializers import AdminPermissionGroupCreationSerializer, TeacherPermissionGroupCreationSerializer
from grades.serializers import GradeCreationSerializer
from terms.serializers import  TermCreationSerializer
from subjects.serializers import  SubjectCreationSerializer
from classrooms.serializers import ClassCreationSerializer
from assessments.serializers import AssessmentCreationSerializer
from transcripts.serializers import TranscriptCreationSerializer
from activities.serializers import ActivityCreationSerializer
from student_group_timetables.serializers import StudentGroupScheduleCreationSerializer
from announcements.serializers import AnnouncementCreationSerializer

# checks
from users.checks import permission_checks

# mappings
from users.maps import role_specific_attr_maps

# utility functions 
from users import utils as users_utilities
from permissions import utils as permissions_utilities
from audit_logs import utils as audits_utilities


@database_sync_to_async
def submit_submissions(user, role, details):
    try:
        assessment = None  # Initialize assessment as None to prevent issues in error handling
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = users_utilities.get_account_and_linked_school(user, role)

        # Check if the user has permission to create an assessment
        if role != 'PRINCIPAL' and not permissions_utilities.has_permission(requesting_account, 'COLLECT', 'ASSESSMENT'):
            response = f'could not proccess your request, you do not have the necessary permissions to collect assessments.'
            audits_utilities.log_audit(actor=requesting_account, action='COLLECT', target_model='ASSESSMENT', outcome='DENIED', response=response, school=requesting_account.school)

            return {'error': response}
        
        student_ids = details['students'].split(', ')

        # Validate that all student IDs exist and are valid
        if not requesting_account.school.students.filter(account_id__in=student_ids).count() == len(student_ids):
            return {'error': 'one or more student account IDs are invalid. please check the provided students information and try again'}
        
        # Fetch the assessment from the requesting user's school
        assessment = requesting_account.school.assessments.get(assessment_id=details.get('assessment'))

        # Prepare the list of Submission objects, dynamically setting status based on the deadline
        submissions = []
        for student_id in student_ids:
            student = requesting_account.school.students.get(account_id=student_id)
            submissions.append(Submission(assessment=assessment, student=student))

        with transaction.atomic():
            # Bulk create Submission objects
            Submission.objects.bulk_create(submissions)

            response = f"assessment submission successfully collected from {len(student_ids)} students."
            audits_utilities.log_audit(actor=requesting_account, action='COLLECT', target_model='ASSESSMENT', target_object_id=str(assessment.assessment_id), outcome='COLLECTED', response=response, school=assessment.school)

        return {"message": response}

    except Assessment.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'an assessment in your school with the provided credentials does not exist, please check the assessment details and try again'}

    except ValidationError as e:
        error_message = e.messages[0].lower() if isinstance(e.messages, list) and e.messages else str(e).lower()
        audits_utilities.log_audit(actor=requesting_account, action='COLLECT', target_model='ASSESSMENT', target_object_id=str(assessment.assessment_id) if assessment else 'N/A', outcome='ERROR', response=error_message, school=requesting_account.school)

        return {"error": error_message}

    except Exception as e:
        error_message = str(e)
        audits_utilities.log_audit(actor=requesting_account, action='COLLECT', target_model='ASSESSMENT', target_object_id=str(assessment.assessment_id) if assessment else 'N/A', outcome='ERROR', response=error_message, school=requesting_account.school)

        return {'error': error_message}

