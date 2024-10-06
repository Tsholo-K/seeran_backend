# python
import base64
import zlib
import json

# django
from django.db import models
from django.utils import timezone

# channels
from channels.db import database_sync_to_async

# models
from permission_groups.models import AdminPermissionGroup, TeacherPermissionGroup
from grades.models import Grade
from subjects.models import Subject
from classrooms.models import Classroom
from assessments.models import Assessment
from assessment_submissions.models import AssessmentSubmission
from student_group_timetables.models import StudentGroupTimetable

# serilializers
from accounts.serializers.general_serializers import SourceAccountSerializer
from accounts.serializers.teachers.serializers import TeacherAccountSerializer
from accounts.serializers.students.serializers import StudentSourceAccountSerializer
from terms.serializers import FormTermsSerializer
from assessments.serializers import AssessmentUpdateFormDataSerializer
from assessment_transcripts.serializers import TranscriptFormSerializer

# utility functions 
from accounts import utils as users_utilities
from account_permissions import utils as permissions_utilities
from audit_logs import utils as audits_utilities


@database_sync_to_async
def form_data_for_subscribing_accounts_to_permission_group(user, role, details):
    try:
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = users_utilities.get_account_and_linked_school(user, role)

        # Check if the user has permission to create an assessment
        if role != 'PRINCIPAL' and not permissions_utilities.has_permission(requesting_account, 'UPDATE', 'PERMISSION'):
            response = f'could not proccess your request, you do not have the necessary permissions to view permission group subscribers. please contact your principal to adjust you permissions for viewing permissions.'
            audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='PERMISSION', outcome='DENIED', response=response, school=requesting_account.school)
            return {'error': response}
        
        if not {'permission_group', 'group'}.issubset(details) or details['group'] not in ['admins', 'teachers']:
            response = f'could not proccess your request, the provided information is invalid for the action you are trying to perform. please make sure to provide a valid group ID and group (admin or teacher) for which to filter the permission groups and try again'
            audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='PERMISSION', outcome='ERROR', response=response, school=requesting_account.school)
            return {'error': response}
        
        # Determine the group type based on the role
        if details['group'] == 'admins':
            permission_group = requesting_account.school.admin_permission_groups.prefetch_related('subscribers').get(permission_group_id=details['permission_group'])
            accounts = requesting_account.school.admins.exclude(id__in=permission_group.subscribers.values_list('id', flat=True))
      
        elif details['group'] == 'teachers':
            permission_group = requesting_account.school.teacher_permission_groups.prefetch_related('subscribers').get(permission_group_id=details['permission_group'])
            accounts = requesting_account.school.teachers.exclude(id__in=permission_group.subscribers.values_list('id', flat=True))

        serialized_accounts = SourceAccountSerializer(accounts, many=True).data

        # Compress the serialized data
        compressed_accounts = zlib.compress(json.dumps(serialized_accounts).encode('utf-8'))

        # Encode compressed data as base64 for safe transport
        encoded_accounts = base64.b64encode(compressed_accounts).decode('utf-8')

        return {"accounts": encoded_accounts}
    
    except AdminPermissionGroup.DoesNotExist:
        # Handle the case where the provided grade ID does not exist
        return { 'error': 'Could not process your request, a admin permission group in your school with the provided credentials does not exist. Please review the group details and try again'}
    
    except TeacherPermissionGroup.DoesNotExist:
        # Handle the case where the provided grade ID does not exist
        return { 'error': 'Could not process your request, a teacher permission group  in your school with the provided credentials does not exist. Please review the group details and try again'}

    except Exception as e:
        # Handle any unexpected errors with a general error message
        return {'error': str(e)}


@database_sync_to_async
def form_data_for_creating_classroom(user, role, details):
    try:
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = users_utilities.get_account_and_linked_school(user, role)

        # Check if the user has permission to create classrooms
        if role != 'PRINCIPAL' and not permissions_utilities.has_permission(requesting_account, 'CREATE', 'CLASSROOM'):
            response = f'could not proccess your request, you do not have the necessary permissions to create assessments.'
            audits_utilities.log_audit(actor=requesting_account, action='CREATE', target_model='CLASSROOM', outcome='DENIED', response=response, school=requesting_account.school)

            return {'error': response}

        if not 'reason' in details or details['reason'] not in ['subject classroom', 'register classroom']:
            response = f'could not proccess your request, the provided information is invalid for the action you are trying to perform. please make sure to provide valid reason for classroom creation and try again'
            audits_utilities.log_audit(actor=requesting_account, action='VIEW', target_model='CLASSROOM', outcome='ERROR', server_response=response, school=requesting_account.school)
            return {'error': response}

        # Determine the query based on the reason for retrieving teachers
        if details.get('reason') == 'register classroom':
            # Retrieve teachers not currently teaching a register class
            teachers = requesting_account.school.teachers.exclude(taught_classrooms__register_classroom=True)

        else:
            # Retrieve the subject and validate it against the grade
            subject = requesting_account.school.subjects.get(subject_id=details['subject'])

            # Retrieve all teachers in the user's school who are not teaching the specified subject
            teachers = requesting_account.school.teachers.exclude(taught_classrooms__subject=subject)

        # Serialize the list of teachers
        serialized_teachers = TeacherAccountSerializer(teachers, many=True).data

        return {"teachers": serialized_teachers}
        
    except Subject.DoesNotExist:
        return {'error': 'a subject in your school with the provided credentials does not exist, please check the subject details and try again'}

    except Exception as e:
        # Handle any other unexpected errors
        return {'error': str(e)}


@database_sync_to_async
def form_data_for_updating_classroom_teacher(account, role, details):
    try:
        classroom = None  # Initialize classroom as None to prevent issues in error handling
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = users_utilities.get_account_and_linked_school(account, role)

        # Check if the user has permission to update classrooms
        if role != 'PRINCIPAL' and not permissions_utilities.has_permission(requesting_account, 'UPDATE', 'CLASSROOM'):
            response = f'could not proccess your request, you do not have the necessary permissions to create assessments.'
            audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='CLASSROOM', outcome='DENIED', response=response, school=requesting_account.school)
            return {'error': response}

        if not 'classroom' in details:
            response = f'could not proccess your request, the provided information is invalid for the action you are trying to perform. please make sure to provide valid classroom ID and try again'
            audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='CLASSROOM', outcome='ERROR', server_response=response, school=requesting_account.school)
            return {'error': response}

        classroom = requesting_account.school.classrooms.select_related('subject', 'teacher').get(classroom_id=details['classroom'])

        # Determine the query based on the classroom type
        if classroom.subject:
            teachers = requesting_account.school.teachers.all().exclude(taught_classrooms__subject=classroom.subject)

        else:
            teachers = requesting_account.school.teachers.all().exclude(taught_classrooms__register_classroom=True)

        if classroom.teacher:
            teachers = teachers.exclude(account_id=classroom.teacher.account_id)
        
        # serialize them
        serialized_teachers = TeacherAccountSerializer(teachers, many=True).data
        classroom_teacher = TeacherAccountSerializer(classroom.teacher).data if classroom.teacher else None

        return {'classroom_teacher': classroom_teacher, "teachers": serialized_teachers}
    
    except Classroom.DoesNotExist:
        # Handle case where the classroom does not exist
        return {'error': 'a classroom in your school with the provided credentials does not exist. Please check the classroom details and try again.'}
    
    except Exception as e:
        # Handle any other unexpected errors
        return {'error': str(e)}


@database_sync_to_async
def form_data_for_adding_students_to_classroom(user, role, details):
    try:
        classroom = None  # Initialize classroom as None to prevent issues in error handling
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = users_utilities.get_account_and_linked_school(user, role)

        # Check if the user has permission to update classrooms
        if role != 'PRINCIPAL' and not permissions_utilities.has_permission(requesting_account, 'UPDATE', 'CLASSROOM'):
            response = f'Could not proccess your request, you do not have the necessary permissions to create assessments.'
            audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='CLASSROOM', outcome='DENIED', server_response=response, school=requesting_account.school)

            return {'error': response}

        if not 'classroom' in details or not 'reason' in details and details['reason'] not in ['subject classroom', 'register classroom']:
            response = f'Could not proccess your request, the provided information is invalid for the action you are trying to perform. please make sure to provide valid classroom ID and reason and then try again'
            audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='CLASSROOM', outcome='ERROR', server_response=response, school=requesting_account.school)
            return {'error': response}

        # Retrieve the classroom with the provided class ID and related data using `select_related`
        classroom = requesting_account.school.classrooms.select_related('grade', 'subject').get(classroom_id=details['classroom'])

        # Determine the reason for fetching students and apply the appropriate filtering logic
        if details.get('reason') == 'subject classroom':
            # Check if the classroom has a subject linked to it
            if not classroom.subject:
                return {"error": "Could not proccess your request, the provided classroom has no subject linked to it."}

            # Exclude students who are already enrolled in any class with the same subject as the classroom
            students = requesting_account.school.students.filter(grade=classroom.grade).exclude(enrolled_classrooms__subject=classroom.subject)

        elif details.get('reason') == 'register classroom':
            # Check if the classroom is a register class
            if not classroom.register_classroom:
                return {"error": "Could not proccess your request, the provided classroom is not a register classroom."}

            # Exclude students who are already enrolled in a register class in the same grade
            students = requesting_account.school.students.filter(grade=classroom.grade).exclude(enrolled_classrooms__register_classroom=True)

        else:
            # Return an error if the reason provided is not valid
            response = "Could not proccesses your request, invalid reason provided."
            audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='CLASSROOM', target_object_id=str(classroom.classroom_id) if classroom else 'N/A', outcome='ERROR', server_response=response, school=requesting_account.school)
            return {'error': response}

        # Serialize the list of students to return them in the response
        serialized_students = StudentSourceAccountSerializer(students, many=True).data

        # Compress the serialized data
        compressed_students = zlib.compress(json.dumps(serialized_students).encode('utf-8'))

        # Encode compressed data as base64 for safe transport
        encoded_students = base64.b64encode(compressed_students).decode('utf-8')

        return {"students": encoded_students}
    
    except Classroom.DoesNotExist:
        # Handle case where the classroom does not exist
        return {'error': 'Could not proccess your request, a classroom in your school with the provided credentials does not exist. Please check the classroom details and try again.'}
    
    except Exception as e:
        # Handle any other unexpected errors
        return {'error': str(e)}
    

@database_sync_to_async
def form_data_for_classroom_attendance_register(user, role, details):
    try:
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = users_utilities.get_account_and_linked_school(user, role)

        # Check if the user has permission to create an assessment
        if role != 'PRINCIPAL' and not permissions_utilities.has_permission(requesting_account, 'SUBMIT', 'ATTENDANCE'):
            response = f'could not proccess your request, you do not have the necessary permissions to submit classroom attendance register. please contact your principal to adjust you permissions for submitting classroom data.'
            audits_utilities.log_audit(actor=requesting_account, action='SUBMIT', target_model='CLASSROOM', outcome='DENIED', server_response=response, school=requesting_account.school)
            return {'error': response}
        
        if not {'classroom'}.issubset(details):
            response = f'could not proccess your request, the provided information is invalid for the action you are trying to perform. please make sure to provide a valid classroom ID and try again'
            audits_utilities.log_audit(actor=requesting_account, action='SUBMIT', target_model='ATTENDANCE', outcome='ERROR', server_response=response, school=requesting_account.school)
            return {'error': response}
        
        classroom = requesting_account.school.classrooms.get(classroom_id=details['classroom'], register_classroom=True)

        # Get today's date
        today = timezone.now()
            
        # Check if an Absent instance exists for today and the given class
        attendance = requesting_account.school.school_attendances.prefetch_related('absent_students').filter(timestamp__date=today, classroom=classroom).first()

        if attendance:
            students = attendance.absent_students
            attendance_register_taken = True

        else:
            students = classroom.students
            attendance_register_taken = False

        serialized_students = StudentSourceAccountSerializer(students, many=True).data

        # Compress the serialized data
        compressed_students = zlib.compress(json.dumps(serialized_students).encode('utf-8'))

        # Encode compressed data as base64 for safe transport
        encoded_students = base64.b64encode(compressed_students).decode('utf-8')

        return {"students": encoded_students, "attendance_register_taken" : attendance_register_taken}
            
    except Classroom.DoesNotExist:
        return {'error': 'Could not proccess your request, a classroom in your school with the provided credentials does not exist. Please review the classroom details and try again.'}

    except Exception as e:
        return { 'error': str(e) }


@database_sync_to_async
def form_data_for_setting_assessment(account, role, details):
    try:
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = users_utilities.get_account_and_linked_school(account, role)

        # Check if the user has permission to create an assessment
        if role != 'PRINCIPAL' and not permissions_utilities.has_permission(requesting_account, 'CREATE', 'ASSESSMENT'):
            response = f'could not proccess your request, you do not have the necessary permissions to create assessments.'
            audits_utilities.log_audit(actor=requesting_account, action='CREATE', target_model='ASSESSMENT', outcome='DENIED', response=response, school=requesting_account.school)

            return {'error': response}
        
        if not {'grade'}.issubset(details):
            response = f'could not proccess your request, the provided information is invalid for the action you are trying to perform. please make sure to provide a valid grade ID and try again'
            audits_utilities.log_audit(actor=requesting_account, action='CREATE', target_model='ASSESSMENT', outcome='ERROR', server_response=response, school=requesting_account.school)
            return {'error': response}

        grade = requesting_account.school.grades.prefetch_related('terms').get(grade_id=details['grade'])
        serialized_terms = FormTermsSerializer(grade.terms, many=True).data

        return {"terms": serialized_terms}
    
    except Grade.DoesNotExist:
        # Handle the case where the provided grade ID does not exist
        return {'error': 'Could not proccess your request, a grade in your school with the provided credentials does not exist. Please review the grade details and try again.'}

    except Exception as e:
        # Handle any other unexpected errors
        return {'error': str(e)}


@database_sync_to_async
def form_data_for_updating_assessment(user, role, details):
    try:
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = users_utilities.get_account_and_linked_school(user, role)

        # Check if the user has permission to create an assessment
        if role != 'PRINCIPAL' and not permissions_utilities.has_permission(requesting_account, 'UPDATE', 'ASSESSMENT'):
            response = f'could not proccess your request, you do not have the necessary permissions to update assessments.'
            audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='ASSESSMENT', outcome='DENIED', response=response, school=requesting_account.school)

            return {'error': response}

        assessment = requesting_account.school.assessments.select_related('grade', 'assessor', 'moderator').prefetch_related('grade__terms').get(assessment_id=details.get('assessment'))

        terms = assessment.grade.terms.all()        
        serialized_terms = FormTermsSerializer(terms, many=True).data

        serialized_assessment = AssessmentUpdateFormDataSerializer(assessment).data

        return {"terms": serialized_terms, "assessment": serialized_assessment}
    
    except Assessment.DoesNotExist:
        # Handle the case where the provided grade ID does not exist
        return { 'error': 'an assessment in your school with the provided credentials does not exist, please check the assessment details and try again'}

    except Exception as e:
        # Handle any other unexpected errors
        return {'error': str(e)}


@database_sync_to_async
def form_data_for_collecting_assessment_submissions(account, role, details):
    try:
        # Retrieve the requesting user's account and related school in a single query using select_related
        requesting_account = users_utilities.get_account_and_linked_school(account, role)

        # Check if the user has permission to collect assessment submissions
        if role != 'PRINCIPAL' and not permissions_utilities.has_permission(requesting_account, 'COLLECT', 'ASSESSMENT'):
            response = 'You do not have the necessary permissions to collect assessment submissions.'
            audits_utilities.log_audit(actor=requesting_account, action='COLLECT', target_model='ASSESSMENT', outcome='DENIED', server_response=response, school=requesting_account.school)
            return {'error': response}
        
        if not {'assessment'}.issubset(details):
            response = f'could not proccess your request, the provided information is invalid for the action you are trying to perform. please make sure to provide a valid assessment ID and try again.'
            audits_utilities.log_audit(actor=requesting_account, action='VIEW', target_model='ASSESSMENT', outcome='ERROR', server_response=response, school=requesting_account.school)
            return {'error': response}

        # Fetch the assessment from the requesting user's school
        assessment = requesting_account.school.assessments.select_related('classroom', 'grade').get(assessment_id=details['assessment'])

        # Get the list of students who have already submitted the assessment
        submitted_student_ids = assessment.submissions.values_list('student__id', flat=True)

        if assessment.classroom:
            # Fetch students in the classroom who haven't submitted
            students = assessment.classroom.students.only('name', 'surname', 'id_number', 'passport_number', 'account_id', 'profile_picture').exclude(id__in=submitted_student_ids)
        elif assessment.grade:
            # Fetch students in the grade who haven't submitted
            students = assessment.grade.students.only('name', 'surname', 'id_number', 'passport_number', 'account_id', 'profile_picture').exclude(id__in=submitted_student_ids)
        else:
            return {'error': 'No valid classroom or grade found for the assessment.'}
        
        # Serialize the student data
        serialized_students = StudentSourceAccountSerializer(students, many=True).data

        # Compress the serialized data
        compressed_students = zlib.compress(json.dumps(serialized_students).encode('utf-8'))

        # Encode compressed data as base64 for safe transport
        encoded_students = base64.b64encode(compressed_students).decode('utf-8')

        return {'students': encoded_students}
    
    except Assessment.DoesNotExist:
        # Handle the case where the provided grade ID does not exist
        return { 'error': 'an assessment in your school with the provided credentials does not exist, please check the assessment details and try again'}

    except Exception as e:
        return {'error': str(e)}


@database_sync_to_async
def form_data_for_assessment_submissions(user, role, details):
    try:
        # Retrieve the requesting user's account and related school in a single query using select_related
        requesting_account = users_utilities.get_account_and_linked_school(user, role)

        # Check if the user has permission to collect assessment submissions
        if role != 'PRINCIPAL' and not permissions_utilities.has_permission(requesting_account, 'COLLECT', 'ASSESSMENT'):
            response = 'You do not have the necessary permissions to collect assessment submissions.'
            audits_utilities.log_audit(actor=requesting_account, action='COLLECT', target_model='ASSESSMENT', outcome='DENIED', response=response, school=requesting_account.school)
            return {'error': response}

        # Fetch the assessment from the requesting user's school
        assessment = requesting_account.school.assessments.select_related('classroom', 'grade').get(assessment_id=details.get('assessment'))

        # Get the list of students who have already submitted the assessment
        submitted_student_ids = assessment.submissions.values_list('student__account_id', flat=True)

        search_filters = models.Q()

        # Apply search filters if provided
        if 'search_query' in details:
            search_query = details.get('search_query')
            search_filters &= (models.Q(name__icontains=search_query) | models.Q(surname__icontains=search_query) | models.Q(account_id__icontains=search_query))

        # Apply cursor for pagination using the primary key (id)
        if 'cursor' in details and details['cursor'] is not None:
            cursor = details.get('cursor')
            search_filters &= models.Q(id__gt=cursor)

        if assessment.classroom:
            # Fetch students in the classroom who haven't submitted
            students = assessment.classroom.students.filter(search_filters).only('name', 'surname', 'id_number', 'passport_number', 'account_id', 'profile_picture').filter(account_id__in=submitted_student_ids).order_by('id')[:10]
        elif assessment.grade:
            # Fetch students in the grade who haven't submitted
            students = assessment.grade.students.filter(search_filters).only('name', 'surname', 'id_number', 'passport_number', 'account_id', 'profile_picture').filter(account_id__in=submitted_student_ids).order_by('id')[:10]
        else:
            return {'error': 'No valid classroom or grade found for the assessment.'}
        
        if not students:
            return {'students': [], 'cursor': None}
        
        # Serialize the student data
        serialized_students = StudentSourceAccountSerializer(students, many=True).data

        # Compress the serialized data
        compressed_students = zlib.compress(json.dumps(serialized_students).encode('utf-8'))

        # Encode compressed data as base64 for safe transport
        encoded_students = base64.b64encode(compressed_students).decode('utf-8')

        # Determine the next cursor (based on the primary key)
        next_cursor = students[len(students) - 1].id if students and len(students) > 9 else None

        return {'students': encoded_students, 'cursor': next_cursor}
    
    except Assessment.DoesNotExist:
        # Handle the case where the provided grade ID does not exist
        return { 'error': 'an assessment in your school with the provided credentials does not exist, please check the assessment details and try again'}

    except Exception as e:
        return {'error': str(e)}


@database_sync_to_async
def form_data_for_assessment_submission_details(user, role, details):
    try:
        # Retrieve the requesting user's account and related school in a single query using select_related
        requesting_account = users_utilities.get_account_and_linked_school(user, role)

        # Check if the user has permission to collect assessment submissions
        if role != 'PRINCIPAL' and not permissions_utilities.has_permission(requesting_account, 'GRADE', 'ASSESSMENT'):
            response = 'You do not have the necessary permissions to grade assessment submissions.'
            audits_utilities.log_audit(actor=requesting_account, action='GRADE', target_model='ASSESSMENT', outcome='DENIED', response=response, school=requesting_account.school)
            return {'error': response}
        
        if not {'student', 'assessment'}.issubset(details):
            response = f'could not proccess your request, the provided information is invalid for the action you are trying to perform. please make sure to provide valid account and assessnt IDs and try again'
            audits_utilities.log_audit(actor=requesting_account, action='GRADE', target_model='ACCOUNT', outcome='ERROR', response=response, school=requesting_account.school)

            return {'error': response}
        
        # Fetch the assessment from the requesting user's school
        assessment = requesting_account.school.assessments.get(assessment_id=details['assessment'])

        transcript = assessment.scores.select_related('student').filter(student__account_id=details['student']).first()
        if transcript:
            serialized_submission = TranscriptFormSerializer(transcript).data
        else:
            submission = assessment.submissions.select_related('student').get(student__account_id=details['student'])
            serialized_submission = {'student': StudentSourceAccountSerializer(submission.student).data}

        return {'submission': serialized_submission}
    
    except Assessment.DoesNotExist:
        # Handle the case where the provided grade ID does not exist
        return { 'error': 'an assessment in your school with the provided credentials does not exist, please check the assessment details and try again'}
    
    except AssessmentSubmission.DoesNotExist:
        # Handle the case where the provided submission ID does not exist
        return { 'error': 'a submission for the specified assessment in your school with the provided credentials does not exist, please make sure the student has submitted the assessment and try again'}

    except Exception as e:
        return {'error': str(e)}


@database_sync_to_async
def form_data_for_adding_students_to_group_schedule(user, role, details):
    try:
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = users_utilities.get_account_and_linked_school(user, role)
        
        # Retrieve the group schedule with the provided ID and related data
        group_schedule = StudentGroupTimetable.objects.select_related('grade').get(group_schedule_id=details.get('group_schedule_id'), grade__school=requesting_account.school)

        # Fetch all students in the same grade who are not already subscribed to the group schedule
        students = requesting_account.school.students.all().filter(grade=group_schedule.grade).exclude(my_group_schedule=group_schedule)
        serialized_students = StudentSourceAccountSerializer(students, many=True).data

        return {"students": serialized_students}
    
    except StudentGroupTimetable.DoesNotExist:
        # Handle case where the group schedule does not exist
        return {'error': 'a group schedule in your school with the provided credentials does not exist. Please check the group schedule details and try again.'}

    except Exception as e:
        # Handle any other unexpected errors
        return {'error': str(e)}


    