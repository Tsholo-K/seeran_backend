# python
import json

# django
from django.db.models import Q

# channels
from channels.db import database_sync_to_async

# models
from grades.models import Grade
from subjects.models import Subject
from classes.models import Classroom
from assessments.models import Assessment
from student_group_timetables.models import StudentGroupTimetable

# serilializers
from users.serializers.teachers.teachers_serializers import TeacherAccountSerializer
from users.serializers.students.students_serializers import StudentSourceAccountSerializer
from terms.serializers import FormTermsSerializer
from assessments.serializers import AssessmentUpdateSerializer, AssessmentUpdateFormDataSerializer

# utility functions 
from users import utils as users_utilities
from permissions import utils as permissions_utilities
from audit_logs import utils as audits_utilities


@database_sync_to_async
def form_data_for_creating_class(user, role, details):
    try:
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = users_utilities.get_account_and_linked_school(user, role)

        # Check if the user has permission to create classrooms
        if role != 'PRINCIPAL' and not permissions_utilities.has_permission(requesting_account, 'CREATE', 'CLASSROOM'):
            response = f'could not proccess your request, you do not have the necessary permissions to create assessments.'
            audits_utilities.log_audit(actor=requesting_account, action='CREATE', target_model='CLASSROOM', outcome='DENIED', response=response, school=requesting_account.school)

            return {'error': response}

        # Determine the query based on the reason for retrieving teachers
        if details.get('reason') == 'subject class':
            # Retrieve the subject and validate it against the grade
            subject = Subject.objects.get(subject_id=details.get('subject'), grade__school=requesting_account.school)

            # Retrieve all teachers in the user's school who are not teaching the specified subject
            teachers = requesting_account.school.teachers.all().exclude(taught_classes__subject=subject)

        elif details.get('reason') == 'register class':
            # Retrieve teachers not currently teaching a register class
            teachers = requesting_account.school.teachers.all().exclude(taught_classes__register_class=True)

        else:
            response = "could not proccesses your request, invalid reason provided. expected 'subject class' or 'register class'."
            audits_utilities.log_audit(actor=requesting_account, action='CREATE', target_model='CLASSROOM', outcome='ERROR', response=response, school=requesting_account.school)

            return {'error': response}

        # Serialize the list of teachers
        serialized_teachers = TeacherAccountSerializer(teachers, many=True).data

        return {"teachers": serialized_teachers}
        
    except Subject.DoesNotExist:
        return {'error': 'a subject in your school with the provided credentials does not exist, please check the subject details and try again'}

    except Exception as e:
        # Handle any other unexpected errors
        return {'error': str(e)}


@database_sync_to_async
def form_data_for_updating_class(user, role, details):
    try:
        classroom = None  # Initialize classroom as None to prevent issues in error handling
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = users_utilities.get_account_and_linked_school(user, role)

        # Check if the user has permission to update classrooms
        if role != 'PRINCIPAL' and not permissions_utilities.has_permission(requesting_account, 'UPDATE', 'CLASSROOM'):
            response = f'could not proccess your request, you do not have the necessary permissions to create assessments.'
            audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='CLASSROOM', outcome='DENIED', response=response, school=requesting_account.school)

            return {'error': response}

        classroom = requesting_account.school.classrooms.select_related('subject', 'teacher').get(classroom_id=details.get('classroom'))

        # Determine the query based on the classroom type
        if classroom.subject:
            teachers = requesting_account.school.teachers.all().exclude(taught_classes__subject=classroom.subject)

        elif classroom.register_class:
            teachers = requesting_account.school.teachers.all().exclude(taught_classes__register_class=True)

        else:
            response = "could not proccesses your request, invalid classroom provided. the classroom in neither a register class or linked to a subject"
            audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='CLASSROOM', target_object_id=str(classroom.classroom_id) if classroom else 'N/A', outcome='ERROR', response=response, school=requesting_account.school)

            return {'error': response}

        if classroom.teacher:
            teachers = teachers.exclude(account_id=classroom.teacher.account_id)
        
        # serialize them
        serialized_teachers = TeacherAccountSerializer(teachers, many=True).data
        class_teacher = TeacherAccountSerializer(classroom.teacher).data if classroom.teacher else None

        return {'teacher': class_teacher, "teachers": serialized_teachers, 'group': classroom.group, 'classroom_identifier': classroom.classroom_number}
    
    except Classroom.DoesNotExist:
        # Handle case where the classroom does not exist
        return {'error': 'a classroom in your school with the provided credentials does not exist. Please check the classroom details and try again.'}
    
    except Exception as e:
        # Handle any other unexpected errors
        return {'error': str(e)}


@database_sync_to_async
def form_data_for_adding_students_to_class(user, role, details):
    try:
        classroom = None  # Initialize classroom as None to prevent issues in error handling
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = users_utilities.get_account_and_linked_school(user, role)

        # Check if the user has permission to update classrooms
        if role != 'PRINCIPAL' and not permissions_utilities.has_permission(requesting_account, 'UPDATE', 'CLASSROOM'):
            response = f'could not proccess your request, you do not have the necessary permissions to create assessments.'
            audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='CLASSROOM', outcome='DENIED', response=response, school=requesting_account.school)

            return {'error': response}

        # Retrieve the classroom with the provided class ID and related data using `select_related`
        classroom = requesting_account.school.classrooms.select_related('grade', 'subject').get(classroom_id=details.get('classroom'))

        # Determine the reason for fetching students and apply the appropriate filtering logic
        if details.get('reason') == 'subject class':
            # Check if the classroom has a subject linked to it
            if not classroom.subject:
                return {"error": "could not proccess your request. the provided classroom has no subject linked to it."}

            # Exclude students who are already enrolled in any class with the same subject as the classroom
            students = requesting_account.school.students.all().filter(grade=classroom.grade).exclude(enrolled_classes__subject=classroom.subject)

        elif details.get('reason') == 'register class':
            # Check if the classroom is a register class
            if not classroom.register_class:
                return {"error": "could not proccess your request. the provided classroom is not a register class."}

            # Exclude students who are already enrolled in a register class in the same grade
            students = requesting_account.school.students.all().filter(grade=classroom.grade).exclude(enrolled_classes__register_class=True)

        else:
            # Return an error if the reason provided is not valid
            response = "could not proccesses your request, invalid reason provided."
            audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='CLASSROOM', target_object_id=str(classroom.classroom_id) if classroom else 'N/A', outcome='ERROR', response=response, school=requesting_account.school)

            return {'error': response}

        # Serialize the list of students to return them in the response
        serialized_students = StudentSourceAccountSerializer(students, many=True).data

        return {"students": serialized_students}
    
    except Classroom.DoesNotExist:
        # Handle case where the classroom does not exist
        return {'error': 'a classroom in your school with the provided credentials does not exist. Please check the classroom details and try again.'}
    
    except Exception as e:
        # Handle any other unexpected errors
        return {'error': str(e)}


@database_sync_to_async
def form_data_for_assessment_setting(user, role, details):
    try:
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = users_utilities.get_account_and_linked_school(user, role)

        # Check if the user has permission to create an assessment
        if role != 'PRINCIPAL' and not permissions_utilities.has_permission(requesting_account, 'CREATE', 'ASSESSMENT'):
            response = f'could not proccess your request, you do not have the necessary permissions to create assessments.'
            audits_utilities.log_audit(actor=requesting_account, action='CREATE', target_model='ASSESSMENT', outcome='DENIED', response=response, school=requesting_account.school)

            return {'error': response}

        grade = requesting_account.school.grades.prefetch_related('terms').get(grade_id=details.get('grade'))

        terms = grade.terms.all()        
        serialized_terms = FormTermsSerializer(terms, many=True).data

        return {"terms": serialized_terms}
    
    except Grade.DoesNotExist:
        # Handle the case where the provided grade ID does not exist
        return { 'error': 'a grade in your school with the provided credentials does not exist, please check the grade details and try again'}

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
        return { 'error': 'an assessment in your school with the provided credentials does not exist, please check the grade details and try again'}

    except Exception as e:
        # Handle any other unexpected errors
        return {'error': str(e)}


@database_sync_to_async
def form_data_for_collecting_assessment_submissions(user, role, details):
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

        search_filters = Q()

        # Apply search filters if provided
        if 'search_query' in details:
            search_query = details.get('search_query')
            search_filters &= (Q(name__icontains=search_query) | Q(surname__icontains=search_query) | Q(account_id__icontains=search_query))

        # Apply cursor for pagination using the primary key (id)
        if 'cursor' in details and details['cursor'] is not None:
            cursor = details.get('cursor')
            search_filters &= Q(id__gt=cursor)

        if assessment.classroom:
            # Fetch students in the classroom who haven't submitted
            students = assessment.classroom.students.filter(search_filters).only('name', 'surname', 'id_number', 'passport_number', 'account_id', 'profile_picture').exclude(account_id__in=submitted_student_ids).order_by('id')[:4]
        elif assessment.grade:
            # Fetch students in the grade who haven't submitted
            students = assessment.grade.students.filter(search_filters).only('name', 'surname', 'id_number', 'passport_number', 'account_id', 'profile_picture').exclude(account_id__in=submitted_student_ids).order_by('id')[:4]
        else:
            return {'error': 'No valid classroom or grade found for the assessment.'}
        
        if not students:
            return {'students': [], 'cursor': None}
        
        # Serialize the student data
        serialized_students = StudentSourceAccountSerializer(students, many=True).data

        # Compress the serialized data
        compressed_students = users_utilities.compress_data(json.dumps(serialized_students))

        # Determine the next cursor (based on the primary key)
        next_cursor = students[len(students) - 1].id if students and len(students) > 3 else None

        return {'students': compressed_students, 'cursor': next_cursor}

    except Assessment.DoesNotExist:
        return {'error': 'No assessment found with the provided details in your school.'}

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


    