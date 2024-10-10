# channels
from channels.db import database_sync_to_async

# django
from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _

# models 
from accounts.models import BaseAccount, Teacher, Student
from classrooms.models import Classroom
from school_attendances.models import ClassroomAttendanceRegister
from assessments.models import Assessment
from assessment_transcripts.models import AssessmentTranscript
from topics.models import Topic
from student_activities.models import StudentActivity

# serilializers
from assessments.serializers import AssessmentCreationSerializer
from student_activities.serializers import ActivityCreationSerializer

# utility functions 
from accounts import utils as accounts_utilities
from account_permissions import utils as permissions_utilities
from audit_logs import utils as audits_utilities



@database_sync_to_async
def submit_attendance_register(account, role, details):
    try:
        classroom = None  # Initialize classroom as None to prevent issues in error handling

        requesting_user = BaseAccount.objects.get(account_id=account)
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = accounts_utilities.get_account_and_linked_school(account, role)

        # Check if the user has permission to create an assessment
        if not permissions_utilities.has_permission(requesting_account, 'SUBMIT', 'ATTENDANCE'):
            response = f'could not proccess your request, you do not have the necessary permissions to grade assessments.'
            audits_utilities.log_audit(actor=requesting_account, action='SUBMIT', target_model='ATTENDANCE', outcome='DENIED', server_response=response, school=requesting_account.school)
            return {'error': response}
        
        if not {'classroom'}.issubset(details):
            response = f'could not proccess your request, the provided information is invalid for the action you are trying to perform. please make sure to provide a valid classroom ID and try again'
            audits_utilities.log_audit(actor=requesting_account, action='SUBMIT', target_model='ATTENDANCE', outcome='ERROR', server_response=response, school=requesting_account.school)
            return {'error': response}

        classroom = requesting_account.taught_classrooms.get(classroom_id=details['classroom'], register_classroom=True)
        
        today = timezone.localdate()
        
        with transaction.atomic():
            # Check if an Absent instance exists for today and the given class
            attendance_register, created = classroom.attendances.get_or_create(timestamp__date=today, defaults={'attendance_taker': requesting_user, 'classroom': classroom, 'school': requesting_account.school})
            students = details.get('students', '').split(', ')

            if created:
                if not students or students == ['']:
                    students = None
                absent = True
                response = 'attendance register successfully taken for today'

            else:                    
                if not students or students == ['']:
                    return {'error': 'Could not process your request, no students were provided.'}
                
                absent = False
                response = 'students marked as late, attendance register successfully updated'
            
            attendance_register.update_attendance_register(students=students, absent=absent)
            audits_utilities.log_audit(actor=requesting_account, action='SUBMIT', target_model='ATTENDANCE', target_object_id=str(classroom.classroom_id) if classroom else 'N/A', outcome='SUBMITTED', server_response=response, school=requesting_account.school,)

        return {'message': response}

    except BaseAccount.DoesNotExist:
        # Handle case where the user or teacher account does not exist
        return {'error': 'The account with the provided credentials does not exist. Please check the account details and try again.'}
    
    except Classroom.DoesNotExist:
        return { 'error': 'class with the provided credentials does not exist' }
    
    except ClassroomAttendanceRegister.DoesNotExist:
        return { 'error': 'class with the provided credentials does not exist' }

    except ValidationError as e:
        error_message = e.messages[0].lower() if isinstance(e.messages, list) and e.messages else str(e).lower()
        audits_utilities.log_audit(actor=requesting_account, action='SUBMIT', target_model='ATTENDANCE', target_object_id=str(classroom.classroom_id) if classroom else 'N/A', outcome='ERROR', server_response=error_message, school=requesting_account.school)

        return {"error": error_message}

    except Exception as e:
        error_message = str(e)
        audits_utilities.log_audit(actor=requesting_account, action='SUBMIT', target_model='ATTENDANCE', target_object_id=str(classroom.classroom_id) if classroom else 'N/A', outcome='ERROR', server_response=error_message, school=requesting_account.school)

        return {'error': error_message}


@database_sync_to_async
def set_assessment(user, details):
    try:
        assessment = None  # Initialize assessment as None to prevent issues in error handling
        # Retrieve the user and related school in a single query using select_related
        requesting_account = Teacher.objects.select_related('school').get(account_id=user)

        # Check if the user has permission to create an assessment
        if not permissions_utilities.has_permission(requesting_account, 'CREATE', 'ASSESSMENT'):
            response = f'could not proccess your request, you do not have the necessary permissions to create assessments.'
            audits_utilities.log_audit(actor=requesting_account, action='CREATE', target_model='ASSESSMENT', outcome='DENIED', response=response, school=requesting_account.school)

            return {'error': response}

        classroom = requesting_account.taught_classes.select_related('grade', 'subject').prefetch_related('grade__terms').filter(classroom_id=details.get('classroom')).first()
        term = classroom.grade.terms.filter(term_id=details.get('term')).first()
        subject = classroom.subject.pk
        
        if not classroom:
            response = "the provided classroom is either not assigned to you or does not exist. please check the classroom details and try again"
            audits_utilities.log_audit(actor=requesting_account, action='CREATE', target_model='ASSESSMENT', outcome='DENIED', response=response, school=requesting_account.school)

            return {'error': response}
        
        elif not term:
            response = "a term for your school with the provided credentials does not exist. please check the term details and try again"
            audits_utilities.log_audit(actor=requesting_account, action='CREATE', target_model='ASSESSMENT', outcome='ERROR', response=response, school=requesting_account.school)

            return {'error': response}
        
        elif not subject:
            response = "a subject for your school with the provided credentials does not exist. please check the subject details and try again"
            audits_utilities.log_audit(actor=requesting_account, action='CREATE', target_model='ASSESSMENT', outcome='ERROR', response=response, school=requesting_account.school)

            return {'error': response}

        details['classroom'] = classroom.pk
        details['grade'] = classroom.grade.pk
        details['assessor'] = requesting_account.pk
        details['school'] = requesting_account.school.pk
        details['term'] = term.pk
        details['subject'] = subject.pk

        # Serialize the details for assessment creation
        serializer = AssessmentCreationSerializer(data=details)
        if serializer.is_valid():
            # Create the assessment within a transaction to ensure atomicity
            with transaction.atomic():
                assessment = Assessment.objects.create(**serializer.validated_data)

                if details.get('topics'):
                    topics = []
                    for name in details['topics']:
                        topic, _ = Topic.objects.get_or_create(name=name)
                        topics.append(topic)

                    assessment.topics.set(topics)
                    
                response = f'assessment {assessment.unique_identifier} has been successfully created, and will become accessible to all the students being assessed and their parents'
                audits_utilities.log_audit(actor=requesting_account, action='CREATE', target_model='ASSESSMENT', target_object_id=str(assessment.assessment_id), outcome='CREATED', response=response, school=requesting_account.school,)

            return {"message": response}
        
        # Return serializer errors if the data is not valid, format it as a string
        error_response = '; '.join([f"{key}: {', '.join(value)}" for key, value in serializer.errors.items()])
        audits_utilities.log_audit(actor=requesting_account, action='CREATE', target_model='ASSESSMENT', target_object_id=str(assessment.assessment_id) if assessment else 'N/A', outcome='ERROR', response=f'Validation failed: {error_response}', school=requesting_account.school)

        return {"error": error_response}
                   
    except Teacher.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'a teacher account with the provided credentials does not exist, please check your account details and try again'}

    except ValidationError as e:
        error_message = e.messages[0].lower() if isinstance(e.messages, list) and e.messages else str(e).lower()
        audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='ACCOUNT', target_object_id=str(assessment.assessment_id) if assessment else 'N/A', outcome='ERROR', response=error_message, school=requesting_account.school)

        return {"error": error_message}

    except Exception as e:
        error_message = str(e)
        audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='ACCOUNT', target_object_id=str(assessment.assessment_id) if assessment else 'N/A', outcome='ERROR', response=error_message, school=requesting_account.school)

        return {'error': error_message}


@database_sync_to_async
def delete_assessment(user, details):
    try:
        assessment = None  # Initialize assessment as None to prevent issues in error handling

        # Retrieve the user and related school in a single query using select_related
        requesting_account = Teacher.objects.select_related('school').get(account_id=user)

        # Check if the user has permission to create an assessment
        if not permissions_utilities.has_permission(requesting_account, 'DELETE', 'ASSESSMENT'):
            response = f'could not proccess your request, you do not have the necessary permissions to delete assessments.'
            audits_utilities.log_audit(actor=requesting_account, action='DELETE', target_model='ASSESSMENT', outcome='DENIED', response=response, school=requesting_account.school)

            return {'error': response}

        assessment = Assessment.objects.select_related('assessor').get(assessment_id=details.get('assessment'), school=requesting_account.school)

        # Ensure only authorized users can delete
        if assessment.assessor != requesting_account:
            response = f'could not proccess your request, you do not have the necessary permissions to delete assessments that are not assessed by you.'
            audits_utilities.log_audit(actor=requesting_account, action='DELETE', target_model='ASSESSMENT', outcome='DENIED', response=response, school=requesting_account.school)

            return {'error': response}

        with transaction.atomic():
            response = f"assessment with assessment ID {assessment.assessment_id} has been successfully deleted, along with it's associated data"
            audits_utilities.log_audit(actor=requesting_account, action='DELETE', target_model='ASSESSMENT', target_object_id=str(assessment.assessment_id), outcome='DELETED', response=response, school=requesting_account.school,)

        return {"message": response}
                   
    except Teacher.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'a teacher account with the provided credentials does not exist, please check your account details and try again'}

    except ValidationError as e:
        error_message = e.messages[0].lower() if isinstance(e.messages, list) and e.messages else str(e).lower()
        audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='ACCOUNT', target_object_id=str(assessment.assessment_id) if assessment else 'N/A', outcome='ERROR', response=error_message, school=requesting_account.school)

        return {"error": error_message}

    except Exception as e:
        error_message = str(e)
        audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='ACCOUNT', target_object_id=str(assessment.assessment_id) if assessment else 'N/A', outcome='ERROR', response=error_message, school=requesting_account.school)

        return {'error': error_message}


@database_sync_to_async
def grade_student(user, details):
    try:
        assessment = None  # Initialize assessment as None to prevent issues in error handling
        # Retrieve the user and related school in a single query using select_related
        requesting_account = Teacher.objects.select_related('school').get(account_id=user)

        # Check if the user has permission to create an assessment
        if not permissions_utilities.has_permission(requesting_account, 'GRADE', 'ASSESSMENT'):
            response = f'could not proccess your request, you do not have the necessary permissions to grade assessments.'
            audits_utilities.log_audit(actor=requesting_account, action='GRADE', target_model='ASSESSMENT', outcome='DENIED', response=response, school=requesting_account.school)

            return {'error': response}

        assessment = Assessment.objects.select_related('assessor').get(assessment_id=details.get('assessment'), school=requesting_account.school)

        # Ensure only authorized users can delete
        if assessment.assessor != requesting_account:
            response = f'could not proccess your request, you do not have the necessary permissions to grade assessments that are not assessed by you.'
            audits_utilities.log_audit(actor=requesting_account, action='GRADE', target_model='ASSESSMENT', outcome='DENIED', response=response, school=requesting_account.school)

            return {'error': response}
        
        student = Student.objects.get(student_id=details.get('student'))
        
        with transaction.atomic():
            transcript = AssessmentTranscript.objects.create(student=student, score=details.get('student'), assessment=assessment)
            response = f"student graded for assessment {assessment.unique_identifier}."
            audits_utilities.log_audit(actor=requesting_account, action='GRADE', target_model='ASSESSMENT', target_object_id=str(transcript.transcript_id), outcome='GRADED', response=response, school=requesting_account.school,)

        return {"message": response}
               
    except Teacher.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'a teacher account with the provided credentials does not exist, please check your account details and try again'}

    except Student.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'a student account with the provided credentials does not exist, please check the accounts details and try again'}

    except Assessment.DoesNotExist:
        # Handle the case where the provided assessment ID does not exist
        return {'error': 'an assessment in your school with the provided credentials does not exist, please check the assessment details and try again'}

    except ValidationError as e:
        error_message = e.messages[0].lower() if isinstance(e.messages, list) and e.messages else str(e).lower()
        audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='ACCOUNT', target_object_id=str(assessment.assessment_id) if assessment else 'N/A', outcome='ERROR', response=error_message, school=requesting_account.school)

        return {"error": error_message}

    except Exception as e:
        error_message = str(e)
        audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='ACCOUNT', target_object_id=str(assessment.assessment_id) if assessment else 'N/A', outcome='ERROR', response=error_message, school=requesting_account.school)

        return {'error': error_message}
    

@database_sync_to_async
def submit_attendance(user, details):
    try:
        classroom = None
        requesting_user = BaseAccount.objects.get(account_id=user)

        # Build the queryset for the requesting account with the necessary related fields.
        requesting_account = Teacher.objects.prefetch_related('taught_classes').get(account_id=user)
        
        classroom = requesting_account.taught_classes.prefetch_related('attendances').filter(register_class=True).first()
        if not classroom:
            response = _("could not proccess your request. the account making the request has no register class assigned to it")
            audits_utilities.log_audit(actor=requesting_account, action='SUBMIT', target_model='ATTENDANCE', outcome='DENIED', response=response, school=requesting_account.school)

            return {'error': response}

        today = timezone.localdate()

        if details.get('absent'):
            if classroom.attendances.filter(date__date=today).exists():
                return {'error': 'attendance register for this class has already been subimitted today.. can not resubmit'}

            with transaction.atomic():
                register = ClassroomAttendanceRegister.objects.create(submitted_by=requesting_user, classroom=classroom)

                if details.get('students'):
                    register.absentes = True
                    for student in details['students'].split(', '):
                        register.absent_students.add(Student.objects.get(account_id=student))

                register.save()
            
            response =  {'message': 'attendance register successfully taken for today'}
            audits_utilities.log_audit(actor=requesting_account, action='SUBMIT', target_model='ATTENDANCE', target_object_id=str(classroom.classroom_id), outcome='SUBMITTED', response=response, school=requesting_account.school,)

        if details.get('late'):
            if not details.get('students'):
                return {"error" : 'invalid request.. no students were provided.. at least one student is needed to be marked as late'}

            absentes = classroom.attendances.prefetch_related('absent_students').filter(date__date=today).first()
            if not absentes:
                return {'error': 'attendance register for this class has not been submitted today.. can not submit late arrivals before the attendance register'}

            if not absentes.absent_students.exists():
                return {'error': 'todays attendance register for this class has all students accounted for'}

            register = ClassroomAttendanceRegister.objects.filter(date__date=today, classroom=classroom).first()
            
            with transaction.atomic():
                if not register:
                    register = ClassroomAttendanceRegister.objects.create(submitted_by=requesting_user, classroom=classroom)
                    
                for student in details['students'].split(', '):
                    student = Student.objects.get(account_id=student)
                    absentes.absent_students.remove(student)
                    register.late_students.add(student)

                absentes.save()
                register.save()

                response =  {'message': 'students marked as late, attendance register successfully updated'}
                audits_utilities.log_audit(actor=requesting_account, action='SUBMIT', target_model='ATTENDANCE', target_object_id=str(classroom.classroom_id), outcome='SUBMITtED', response=response, school=requesting_account.school,)

        return {"message": response}

    except BaseAccount.DoesNotExist:
        # Handle case where the user or teacher account does not exist
        return {'error': 'The account with the provided credentials does not exist. Please check the account details and try again.'}
    
    except Classroom.DoesNotExist:
        return { 'error': 'class with the provided credentials does not exist' }

    except ValidationError as e:
        error_message = e.messages[0].lower() if isinstance(e.messages, list) and e.messages else str(e).lower()
        audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='ACCOUNT', target_object_id=str(classroom.classroom_id) if classroom else 'N/A', outcome='ERROR', response=error_message, school=requesting_account.school)

        return {"error": error_message}

    except Exception as e:
        error_message = str(e)
        audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='ACCOUNT', target_object_id=str(classroom.classroom_id) if classroom else 'N/A', outcome='ERROR', response=error_message, school=requesting_account.school)

        return {'error': error_message}


@database_sync_to_async
def log_activity(user, details):
    try:
        activity = None
        requesting_user = BaseAccount.objects.get(account_id=user)
        
        requesting_account = Teacher.objects.select_related('school').get(account_id=user)

        # Check if the user has permission to create activities
        if not permissions_utilities.has_permission(requesting_account, 'LOG', 'ACTIVITY'):
            response = f'could not proccess your request, you do not have the necessary permissions to log activities.'
            audits_utilities.log_audit(actor=requesting_account, action='LOG', target_model='ACTIVITY', outcome='DENIED', response=response, school=requesting_account.school)

            return {'error': response}

        # Determine the classroom based on the request details
        if details.get('classroom') == 'submitting my own classes data':
            # Fetch the classroom where the user is the teacher and it is a register class
            classroom = requesting_account.taught_classes.prefetch_related('taught_classes__students').filter(register_class=True).first()

        else:
            # Fetch the specific classroom based on class_id and school
            classroom = requesting_account.taught_classes.prefetch_related('taught_classes__students').filter(class_id=details.get('classroom')).first()

        if not classroom:
            return {"error": _("could not proccess your request. a classroom with the provided credentials assigned to you does not exist")}

        # Retrieve the student account
        requested_account = Student.objects.get(account_id=details.get('recipient'), school=requesting_account.school)

        if requested_account not in classroom.students.all():
            return {"error": "unauthorized access. you can only log activities for students you teach."}

        details['classroom'] = classroom.pk

        # Prepare the data for serialization
        details['recipient'] = requested_account.pk
        details['logger'] = requesting_user.pk
        details['school'] = requesting_account.school.pk

        # Initialize the serializer with the prepared data
        serializer = ActivityCreationSerializer(data=details)
        if serializer.is_valid():
            with transaction.atomic():
                activity = StudentActivity.objects.create(**serializer.validated_data)

                response = f'activity successfully logged. the activity is now available to everyone with access to the student\'s data.'
                audits_utilities.log_audit(actor=requesting_account, action='LOG', target_model='ACTIVITY', target_object_id=str(activity.activity_id), outcome='LOGGED', response=response, school=requesting_account.school,)

            return {"message": response}
                
        # Return serializer errors if the data is not valid, format it as a string
        error_response = '; '.join([f"{key}: {', '.join(value)}" for key, value in serializer.errors.items()])
        audits_utilities.log_audit(actor=requesting_account, action='LOG', target_model='ACTIVITY', target_object_id=str(activity.activity_id) if activity else 'N/A', outcome='ERROR', response=f'Validation failed: {error_response}', school=requesting_account.school)

        return {"error": error_response}

    except BaseAccount.DoesNotExist:
        # Handle case where the user or student account does not exist
        return {'error': 'an account with the provided credentials does not exist. Please check the account details and try again.'}

    except Teacher.DoesNotExist:
        # Handle the case where the requested teacher account does not exist.
        return {'error': 'a teacher account with the provided credentials does not exist, please check the account details and try again'}

    except ValidationError as e:
        error_message = e.messages[0].lower() if isinstance(e.messages, list) and e.messages else str(e).lower()
        audits_utilities.log_audit(actor=requesting_account, action='LOG', target_model='ACTIVITY', target_object_id=str(activity.activity_id) if activity else 'N/A', outcome='ERROR', response=error_message, school=requesting_account.school)

        return {"error": error_message}

    except Exception as e:
        error_message = str(e)
        audits_utilities.log_audit(actor=requesting_account, action='LOG', target_model='ACTIVITY', target_object_id=str(activity.activity_id) if activity else 'N/A', outcome='ERROR', response=error_message, school=requesting_account.school)

        return {'error': error_message}
