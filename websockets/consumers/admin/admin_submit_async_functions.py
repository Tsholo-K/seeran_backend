# channels
from channels.db import database_sync_to_async

# django
from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ValidationError

# models 
from accounts.models import BaseAccount, Student
from classrooms.models import Classroom
from school_attendances.models import SchoolAttendance
from assessments.models import Assessment
from assessment_submissions.models import AssessmentSubmission
from assessment_transcripts.models import Transcript

# serilializers
from assessment_transcripts.serializers import TranscriptCreationSerializer

# utility functions 
from accounts import utils as users_utilities
from account_permissions import utils as permissions_utilities
from audit_logs import utils as audits_utilities


@database_sync_to_async
def submit_assessment_submissions(user, role, details):
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
            submissions.append(AssessmentSubmission(assessment=assessment, student=student))

        with transaction.atomic():
            # Bulk create Submission objects
            AssessmentSubmission.objects.bulk_create(submissions)

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


@database_sync_to_async
def submit_student_transcript_score(user, role, details):
    try:
        assessment = None  # Initialize assessment as None to prevent issues in error handling
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = users_utilities.get_account_and_linked_school(user, role)

        # Check if the user has permission to create an assessment
        if role != 'PRINCIPAL' and not permissions_utilities.has_permission(requesting_account, 'GRADE', 'ASSESSMENT'):
            response = f'could not proccess your request, you do not have the necessary permissions to grade assessments.'
            audits_utilities.log_audit(actor=requesting_account, action='GRADE', target_model='ASSESSMENT', outcome='DENIED', response=response, school=requesting_account.school)

            return {'error': response}
                
        if not {'student', 'assessment'}.issubset(details):
            response = f'could not proccess your request, the provided information is invalid for the action you are trying to perform. please make sure to provide valid account and assessnt IDs and try again'
            audits_utilities.log_audit(actor=requesting_account, action='GRADE', target_model='ACCOUNT', outcome='ERROR', response=response, school=requesting_account.school)

            return {'error': response}

        # Fetch the assessment from the requesting user's school
        assessment = requesting_account.school.assessments.select_related('assessor','moderator').get(assessment_id=details['assessment'])
        
        # Check if the user has permission to grade the assessment
        if (assessment.assessor and user != assessment.assessor.account_id) and (assessment.moderator and user != assessment.moderator.account_id):
            response = f'could not proccess your request, you do not have the necessary permissions to grade this assessment. only the assessments assessor or moderator can assign scores to the assessment.'
            audits_utilities.log_audit(actor=requesting_account, action='GRADE', target_model='ASSESSMENT', target_object_id=str(assessment.assessment_id) if assessment else 'N/A', outcome='DENIED', response=response, school=requesting_account.school)

            return {'error': response}

        student = requesting_account.school.students.get(account_id=details['student'])
        
        details['student'] = student.pk
        details['assessment'] = assessment.pk

        # Initialize the serializer with the prepared data
        serializer = TranscriptCreationSerializer(data=details)
        if serializer.is_valid():
            with transaction.atomic():
                Transcript.objects.create(**serializer.validated_data)

                response = f"student graded for assessment {assessment.title}."
                audits_utilities.log_audit(actor=requesting_account, action='GRADE', target_model='ASSESSMENT', target_object_id=str(assessment.assessment_id) if assessment else 'N/A', outcome='GRADED', response=response, school=assessment.school)

            return {"message": response}

        error_response = '; '.join([f"{key}: {', '.join(value)}" for key, value in serializer.errors.items()])
        audits_utilities.log_audit(actor=requesting_account, action='GRADE', target_model='ASSESSMENT', target_object_id=str(assessment.assessment_id) if assessment else 'N/A', outcome='ERROR', response=f'Validation failed: {error_response}', school=requesting_account.school)

        return {"error": error_response}

    except Assessment.DoesNotExist:
        # Handle the case where the provided assessment ID does not exist
        return {'error': 'an assessment in your school with the provided credentials does not exist, please check the assessment details and try again'}

    except Student.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'a student account with the provided credentials does not exist, please check the accounts details and try again'}

    except ValidationError as e:
        error_message = e.messages[0].lower() if isinstance(e.messages, list) and e.messages else str(e).lower()
        audits_utilities.log_audit(actor=requesting_account, action='GRADE', target_model='ASSESSMENT', target_object_id=str(assessment.assessment_id) if assessment else 'N/A', outcome='ERROR', response=error_message, school=requesting_account.school)

        return {"error": error_message}

    except Exception as e:
        error_message = str(e)
        audits_utilities.log_audit(actor=requesting_account, action='GRADE', target_model='ASSESSMENT', target_object_id=str(assessment.assessment_id) if assessment else 'N/A', outcome='ERROR', response=error_message, school=requesting_account.school)

        return {'error': error_message}
    

@database_sync_to_async
def submit_school_attendance(user, role, details):
    try:
        classroom = None  # Initialize classroom as None to prevent issues in error handling

        requesting_user = BaseAccount.objects.get(account_id=user)
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = users_utilities.get_account_and_linked_school(user, role)

        # Check if the user has permission to create an assessment
        if role != 'PRINCIPAL' and not permissions_utilities.has_permission(requesting_account, 'SUBMIT', 'ATTENDANCE'):
            response = f'could not proccess your request, you do not have the necessary permissions to grade assessments.'
            audits_utilities.log_audit(actor=requesting_account, action='SUBMIT', target_model='ATTENDANCE', outcome='DENIED', response=response, school=requesting_account.school)

            return {'error': response}

        classroom = Classroom.objects.get(classroom_id=details.get('class'), school=requesting_account.school, register_class=True)
        
        today = timezone.localdate()

        if details.get('absent'):
            if classroom.attendances.filter(date__date=today).exists():
                return {'error': 'attendance register for this class has already been subimitted today.. can not resubmit'}

            with transaction.atomic():
                register = SchoolAttendance.objects.create(submitted_by=requesting_user, classroom=classroom)

                if details.get('students'):
                    register.absentes = True
                    for student in details['students'].split(', '):
                        register.absent_students.add(Student.objects.get(account_id=student))

                register.save()
            
                response = 'attendance register successfully taken for today'
                audits_utilities.log_audit(actor=requesting_account, action='SUBMIT', target_model='ATTENDANCE', target_object_id=str(student.account_id) if student else 'N/A', outcome='SUBMITTED', response=response, school=requesting_account.school,)

        if details.get('late'):
            if not details.get('students'):
                return {"error" : 'invalid request.. no students were provided.. at least one student is needed to be marked as late'}

            absentes = classroom.attendances.prefetch_related('absent_students').filter(date__date=today).first()
            if not absentes:
                return {'error': 'attendance register for this class has not been submitted today.. can not submit late arrivals before the attendance register'}

            if not absentes.absent_students.exists():
                return {'error': 'todays attendance register for this class has all students accounted for'}

            register = SchoolAttendance.objects.filter(date__date=today, classroom=classroom).first()
            
            with transaction.atomic():
                if not register:
                    register = SchoolAttendance.objects.create(submitted_by=requesting_user, classroom=classroom)
                    
                for student in details['students'].split(', '):
                    student = Student.objects.get(account_id=student)
                    absentes.absent_students.remove(student)
                    register.late_students.add(student)

                absentes.save()
                register.save()

                response = 'students marked as late, attendance register successfully updated'
                audits_utilities.log_audit(actor=requesting_account, action='SUBMIT', target_model='ATTENDANCE', target_object_id=str(student.account_id) if student else 'N/A', outcome='SUBMITTED', response=response, school=requesting_account.school,)

        return {'message': response}

    except BaseAccount.DoesNotExist:
        # Handle case where the user or teacher account does not exist
        return {'error': 'The account with the provided credentials does not exist. Please check the account details and try again.'}
    
    except Classroom.DoesNotExist:
        return { 'error': 'class with the provided credentials does not exist' }

    except ValidationError as e:
        error_message = e.messages[0].lower() if isinstance(e.messages, list) and e.messages else str(e).lower()
        audits_utilities.log_audit(actor=requesting_account, action='SUBMIT', target_model='ATTENDANCE', target_object_id=str(classroom.classroom_id) if classroom else 'N/A', outcome='ERROR', response=error_message, school=requesting_account.school)

        return {"error": error_message}

    except Exception as e:
        error_message = str(e)
        audits_utilities.log_audit(actor=requesting_account, action='SUBMIT', target_model='ATTENDANCE', target_object_id=str(classroom.classroom_id) if classroom else 'N/A', outcome='ERROR', response=error_message, school=requesting_account.school)

        return {'error': error_message}