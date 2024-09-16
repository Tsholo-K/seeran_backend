# channels
from channels.db import database_sync_to_async

# django
from django.db import transaction
from django.core.exceptions import ValidationError

# models 
from users.models import BaseUser, Student
from grades.models import Grade
from terms.models import Term
from subjects.models import Subject
from classes.models import Classroom
from assessments.models import Assessment
from transcripts.models import Transcript
from assessments.models import Topic

# serilializers
from grades.serializers import UpdateGradeSerializer, GradeDetailsSerializer
from schools.serializers import UpdateSchoolAccountSerializer, SchoolDetailsSerializer
from terms.serializers import UpdateTermSerializer, TermSerializer
from subjects.serializers import UpdateSubjectSerializer, SubjectDetailsSerializer
from classes.serializers import UpdateClassSerializer
from assessments.serializers import AssessmentUpdateSerializer
from transcripts.serializers import TranscriptUpdateSerializer

# checks
from users.checks import permission_checks

# mappings
from users.maps import role_specific_maps

# utility functions 
from users import utils as users_utilities
from permissions import utils as permissions_utilities
from audit_logs import utils as audits_utilities


@database_sync_to_async
def update_school_account(user, role, details):
    try:
        school = None  # Initialize requested_account as None to prevent issues in error handling
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = users_utilities.get_account_and_linked_school(user, role)
        
        school = requesting_account.school

        # Check if the user has permission to update classrooms
        if role != 'PRINCIPAL' and not permissions_utilities.has_permission(requesting_account, 'UPDATE', 'ACCOUNT'):
            response = f'could not proccess your request, you do not have the necessary permissions to update account details.'
            audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='ACCOUNT', outcome='DENIED', response=response, school=school)

            return {'error': response}

        # Initialize the serializer with the existing school instance and incoming data
        serializer = UpdateSchoolAccountSerializer(instance=school, data=details)
        # Validate the incoming data
        if serializer.is_valid():
            # Use an atomic transaction to ensure the database is updated safely
            with transaction.atomic():
                serializer.save()
                    
                response = f"school account details have been successfully updated"
                audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='ACCOUNT', target_object_id=str(school.school_id) if school else 'N/A', outcome='UPDATED', response=response, school=requesting_account.school,)

            # Serialize the grade
            serialized_school = SchoolDetailsSerializer(school).data

            return {'school': serialized_school, "message": response}
            
        # Return serializer errors if the data is not valid, format it as a string
        error_response = '; '.join([f"{key}: {', '.join(value)}" for key, value in serializer.errors.items()])
        audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='ACCOUNT', target_object_id=str(school.school_id) if school else 'N/A', outcome='ERROR', response=f'Validation failed: {error_response}', school=school)

        return {"error": error_response}

    except ValidationError as e:
        error_message = e.messages[0].lower() if isinstance(e.messages, list) and e.messages else str(e).lower()
        audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='ACCOUNT', target_object_id=str(school.school_id) if school else 'N/A', outcome='ERROR', response=error_message, school=school)

        return {"error": error_message}

    except Exception as e:
        error_message = str(e)
        audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='ACCOUNT', target_object_id=str(school.school_id) if school else 'N/A', outcome='ERROR', response=error_message, school=school)

        return {'error': error_message}


@database_sync_to_async
def update_grade_details(user, role, details):
    try:
        grade = None  # Initialize grade as None to prevent issues in error handling
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = users_utilities.get_account_and_linked_school(user, role)

        # Check if the user has permission to update grades
        if role != 'PRINCIPAL' and not permissions_utilities.has_permission(requesting_account, 'UPDATE', 'GRADE'):
            response = f'could not proccess your request, you do not have the necessary permissions to update grade details.'
            audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='GRADE', outcome='DENIED', response=response, school=requesting_account.school)

            return {'error': response}

        grade = Grade.objects.get(grade_id=details.get('grade'), school=requesting_account.school)

        # Initialize the serializer with the existing school instance and incoming data
        serializer = UpdateGradeSerializer(instance=grade, data=details)
        if serializer.is_valid():
            with transaction.atomic():
                serializer.save()
                    
                response = f"grade details have been successfully updated"
                audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='GRADE', target_object_id=str(grade.grade_id) if grade else 'N/A', outcome='UPDATED', response=response, school=requesting_account.school,)

            # Serialize the grade
            serialized_grade = GradeDetailsSerializer(grade).data
            
            # Return the serialized grade in a dictionary
            return {'grade': serialized_grade, "message": response}
            
        # Return serializer errors if the data is not valid, format it as a string
        error_response = '; '.join([f"{key}: {', '.join(value)}" for key, value in serializer.errors.items()])
        audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='GRADE', target_object_id=str(grade.grade_id) if grade else 'N/A', outcome='ERROR', response=f'Validation failed: {error_response}', school=requesting_account.school)

        return {"error": error_response}
                       
    except Grade.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'an grade for your school with the provided credentials does not exist, please check the grade details and try again'}

    except ValidationError as e:
        error_message = e.messages[0].lower() if isinstance(e.messages, list) and e.messages else str(e).lower()
        audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='GRADE', target_object_id=str(grade.grade_id) if grade else 'N/A', outcome='ERROR', response=error_message, school=requesting_account.school)

        return {"error": error_message}

    except Exception as e:
        error_message = str(e)
        audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='GRADE', target_object_id=str(grade.grade_id) if grade else 'N/A', outcome='ERROR', response=error_message, school=requesting_account.school)

        return {'error': error_message}
    

@database_sync_to_async
def update_term_details(user, role, details):
    try:
        term = None  # Initialize term as None to prevent issues in error handling
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = users_utilities.get_account_and_linked_school(user, role)

        # Check if the user has permission to update terms
        if role != 'PRINCIPAL' and not permissions_utilities.has_permission(requesting_account, 'UPDATE', 'TERM'):
            response = f'could not proccess your request, you do not have the necessary permissions to update term details.'
            audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='TERM', outcome='DENIED', response=response, school=requesting_account.school)

            return {'error': response}

        term = Term.objects.get(term_id=details.get('term'), school=requesting_account.school)

        # Initialize the serializer with the existing school instance and incoming data
        serializer = UpdateTermSerializer(instance=term, data=details)
        # Validate the incoming data
        if serializer.is_valid():
            # Use an atomic transaction to ensure the database is updated safely
            with transaction.atomic():
                serializer.save()
                    
                response = f"school term details have been successfully updated"
                audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='TERM', target_object_id=str(term.term_id) if term else 'N/A', outcome='UPDATED', response=response, school=requesting_account.school,)

            # Serialize the school terms
            serialized_term = TermSerializer(term).data

            return {'term': serialized_term, "message": response}
            
        # Return serializer errors if the data is not valid, format it as a string
        error_response = '; '.join([f"{key}: {', '.join(value)}" for key, value in serializer.errors.items()])
        audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='TERM', target_object_id=str(term.term_id) if term else 'N/A', outcome='ERROR', response=f'Validation failed: {error_response}', school=requesting_account.school)

        return {"error": error_response}
                       
    except Term.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'a term for your school with the provided credentials does not exist, please check the term details and try again'}

    except ValidationError as e:
        error_message = e.messages[0].lower() if isinstance(e.messages, list) and e.messages else str(e).lower()
        audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='TERM', target_object_id=str(term.term_id) if term else 'N/A', outcome='ERROR', response=error_message, school=requesting_account.school)

        return {"error": error_message}

    except Exception as e:
        error_message = str(e)
        audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='TERM', target_object_id=str(term.term_id) if term else 'N/A', outcome='ERROR', response=error_message, school=requesting_account.school)

        return {'error': error_message}


@database_sync_to_async
def update_subject_details(user, role, details):
    try:
        subject = None  # Initialize subject as None to prevent issues in error handling
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = users_utilities.get_account_and_linked_school(user, role)

        # Check if the user has permission to update classrooms
        if role != 'PRINCIPAL' and not permissions_utilities.has_permission(requesting_account, 'UPDATE', 'SUBJECT'):
            response = f'could not proccess your request, you do not have the necessary permissions to update subject details.'
            audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='SUBJECT', outcome='DENIED', response=response, school=requesting_account.school)

            return {'error': response}

        subject = Subject.objects.get(subject_id=details.get('subject'), grade__school=requesting_account.school)

        # Initialize the serializer with the existing school instance and incoming data
        serializer = UpdateSubjectSerializer(instance=subject, data=details)
        # Validate the incoming data
        if serializer.is_valid():
            # Use an atomic transaction to ensure the database is updated safely
            with transaction.atomic():
                serializer.save()
                    
                response = f"subject details have been successfully updated"
                audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='SUBJECT', target_object_id=str(subject.subject_id) if subject else 'N/A', outcome='UPDATED', response=response, school=requesting_account.school,)
            
            # Serialize the subject
            serialized_subject = SubjectDetailsSerializer(subject).data

            # Return the serialized grade in a dictionary
            return {'subject': serialized_subject, "message": response}
            
        # Return serializer errors if the data is not valid, format it as a string
        error_response = '; '.join([f"{key}: {', '.join(value)}" for key, value in serializer.errors.items()])
        audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='SUBJECT', target_object_id=str(subject.subject_id) if subject else 'N/A', outcome='ERROR', response=f'Validation failed: {error_response}', school=requesting_account.school)

        return {"error": error_response}
        
    except Subject.DoesNotExist:
        # Handle case where the subject does not exist
        return {'error': 'a subject in your school with the provided credentials does not exist.'}

    except ValidationError as e:
        error_message = e.messages[0].lower() if isinstance(e.messages, list) and e.messages else str(e).lower()
        audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='SUBJECT', target_object_id=str(subject.subject_id) if subject else 'N/A', outcome='ERROR', response=error_message, school=requesting_account.school)

        return {"error": error_message}

    except Exception as e:
        error_message = str(e)
        audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='SUBJECT', target_object_id=str(subject.subject_id) if subject else 'N/A', outcome='ERROR', response=error_message, school=requesting_account.school)

        return {'error': error_message}
    

@database_sync_to_async
def update_account(user, role, details):
    try:
        if details.get('role') not in ['ADMIN', 'TEACHER', 'STUDENT', 'PARENT']:
            return {"error": 'could not proccess your request, the provided account role is invalid'}

        requested_account = None  # Initialize requested_account as None to prevent issues in error handling

        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = users_utilities.get_account_and_linked_school(user, role)

        # Check if the user has permission to update classrooms
        if role != 'PRINCIPAL' and not permissions_utilities.has_permission(requesting_account, 'UPDATE', 'ACCOUNT'):
            response = f'could not proccess your request, you do not have the necessary permissions to update classroom details.'
            audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='ACCOUNT', outcome='DENIED', response=response, school=requesting_account.school)

            return {'error': response}

        if details['role'] == 'ADMIN' and role == 'ADMIN':
            response = f'could not proccess your request, your accounts role does not have enough permissions to perform this action.'

            audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='ACCOUNT', outcome='DENIED', response=response, school=requesting_account.school)

            return {'error': response}

        # Retrieve the requested user's account and related attr for permission check
        requested_account = users_utilities.get_account_and_attr(details['account'], details['role'])
        
        # Check if the requesting user has permission to view the requested user's profile.
        permission_error = permission_checks.check_update_details_permissions(requesting_account, requested_account)
        if permission_error:
            return permission_error
        
        # Get the appropriate serializer
        Serializer = role_specific_maps.account_update_serializer_mapping[details['role']]

        # Serialize the requested user's profile for returning in the response.
        serializer = Serializer(instance=requested_account, data=details['updates'])
        if serializer.is_valid():
            with transaction.atomic():
                serializer.save()
                        
                response = f'account details successfully updated'
                audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='ACCOUNT', target_object_id=str(requested_account.account_id) if requested_account else 'N/A', outcome='UPDATED', response=response, school=requesting_account.school,)
            
            # Get the appropriate serializer
            Serializer = role_specific_maps.account_details_serializer_mapping[details['role']]

            # Serialize the requested user's profile for returning in the response.
            serialized_user = Serializer(instance=requested_account).data

            return {"user" : serialized_user}

        # Return serializer errors if the data is not valid, format it as a string
        error_response = '; '.join([f"{key}: {', '.join(value)}" for key, value in serializer.errors.items()])
        audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='ACCOUNT', target_object_id=str(requested_account.account_id) if requested_account else 'N/A', outcome='ERROR', response=f'Validation failed: {error_response}', school=requesting_account.school)

        return {"error": error_response}

    except ValidationError as e:
        error_message = e.messages[0].lower() if isinstance(e.messages, list) and e.messages else str(e).lower()
        audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='ACCOUNT', target_object_id=str(requested_account.account_id) if requested_account else 'N/A', outcome='ERROR', response=error_message, school=requesting_account.school)

        return {"error": error_message}

    except Exception as e:
        error_message = str(e)
        audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='ACCOUNT', target_object_id=str(requested_account.account_id) if requested_account else 'N/A', outcome='ERROR', response=error_message, school=requesting_account.school)

        return {'error': error_message}


@database_sync_to_async
def update_class(user, role, details):
    try:
        classroom = None  # Initialize classroom as None to prevent issues in error handling
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = users_utilities.get_account_and_linked_school(user, role)

        # Check if the user has permission to update classrooms
        if role != 'PRINCIPAL' and not permissions_utilities.has_permission(requesting_account, 'UPDATE', 'CLASSROOM'):
            response = f'could not proccess your request, you do not have the necessary permissions to update classroom details.'
            audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='CLASSROOM', outcome='DENIED', response=response, school=requesting_account.school)

            return {'error': response}

        classroom = Classroom.objects.get(classroom_id=details.get('class'), school=requesting_account.school)

        serializer = UpdateClassSerializer(instance=classroom, data=details.get('updates'))
        if serializer.is_valid():
            with transaction.atomic():
                serializer.save()

                if details['updates']['teacher']:
                    if details['updates']['teacher'] == 'remove teacher':
                        classroom.update_teacher(teacher=None)
                    else:
                        classroom.update_teacher(teacher=details['updates']['teacher'])
                    
                response = f'classroom details have been successfully updated'
                audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='CLASSROOM', target_object_id=str(classroom.classroom_id) if classroom else 'N/A', outcome='UPDATED', response=response, school=requesting_account.school,)

            return {"message": response}
            
        # Return serializer errors if the data is not valid, format it as a string
        error_response = '; '.join([f"{key}: {', '.join(value)}" for key, value in serializer.errors.items()])
        audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='CLASSROOM', target_object_id=str(classroom.classroom_id) if classroom else 'N/A', outcome='ERROR', response=f'Validation failed: {error_response}', school=requesting_account.school)

        return {"error": error_response}
    
    except Classroom.DoesNotExist:
        # Handle case where the classroom does not exist
        return {'error': 'a classroom in your school with the provided credentials does not exist. please check the classroom details and try again.'}

    except ValidationError as e:
        error_message = e.messages[0].lower() if isinstance(e.messages, list) and e.messages else str(e).lower()
        audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='CLASSROOM', target_object_id=str(classroom.classroom_id) if classroom else 'N/A', outcome='ERROR', response=error_message, school=requesting_account.school)

        return {"error": error_message}

    except Exception as e:
        error_message = str(e)
        audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='CLASSROOM', target_object_id=str(classroom.classroom_id) if classroom else 'N/A', outcome='ERROR', response=error_message, school=requesting_account.school)

        return {'error': error_message}


@database_sync_to_async
def update_class_students(user, role, details):
    try:
        students_list = details.get('students', '').split(', ')
        if not students_list or students_list == ['']:
            return {'error': 'your request could not be proccessed.. no students were provided'}
        
        classroom = None  # Initialize assessment as None to prevent issues in error handling

        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = users_utilities.get_account_and_linked_school(user, role)

        # Check if the user has permission to update classrooms
        if role != 'PRINCIPAL' and not permissions_utilities.has_permission(requesting_account, 'UPDATE', 'CLASSROOM'):
            response = f'could not proccess your request, you do not have the necessary permissions to update classroom details.'
            audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='CLASSROOM', outcome='DENIED', response=response, school=requesting_account.school)

            return {'error': response}

        classroom = Classroom.objects.select_related('grade', 'subject').get(classroom_id=details.get('class'), school=requesting_account.school)

        with transaction.atomic():
            # Check for validation errors and perform student updates
            error_message = classroom.update_students(students_list=students_list, remove=details.get('remove'))
            
        if error_message:
            audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='ASSESSMENT', target_object_id=str(classroom.classroom_id) if classroom else 'N/A', outcome='ERROR', response=error_message, school=requesting_account.school,)
            return {'error': error_message}
        
        response = f'Students successfully {"removed from" if details.get("remove") else "added to"} the grade {classroom.grade.grade}, group {classroom.group} {"register" if classroom.register_class else classroom.subject.subject} class'.lower()
        audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='ASSESSMENT', target_object_id=str(classroom.classroom_id) if classroom else 'N/A', outcome='UPDATED', response=response, school=requesting_account.school,)

        return {"message": response}
    
    except Classroom.DoesNotExist:
        # Handle case where the classroom does not exist
        return {'error': 'a classroom in your school with the provided credentials does not exist. please check the classroom details and try again.'}

    except ValidationError as e:
        error_message = e.messages[0].lower() if isinstance(e.messages, list) and e.messages else str(e).lower()
        audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='CLASSROOM', target_object_id=str(classroom.classroom_id) if classroom else 'N/A', outcome='ERROR', response=error_message, school=requesting_account.school)

        return {"error": error_message}

    except Exception as e:
        error_message = str(e)
        audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='CLASSROOM', target_object_id=str(classroom.classroom_id) if classroom else 'N/A', outcome='ERROR', response=error_message, school=requesting_account.school)

        return {'error': error_message}


@database_sync_to_async
def update_assessment(user, role, details):
    try:
        assessment = None  # Initialize assessment as None to prevent issues in error handling
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = users_utilities.get_account_and_linked_school(user, role)

        # Check if the user has permission to update an assessment
        if role != 'PRINCIPAL' and not permissions_utilities.has_permission(requesting_account, 'UPDATE', 'ASSESSMENT'):
            response = f'could not proccess your request, you do not have the necessary permissions to update assessments.'
            audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='ASSESSMENT', outcome='DENIED', response=response, school=requesting_account.school)

            return {'error': response}

        assessment = requesting_account.school.assessments.get(assessment_id=details.get('assessment'))

        if details.get('moderator'):
            if details['moderator'] == 'remove current moderator':
                details['moderator'] = None
            else:
                moderator = BaseUser.objects.only('pk').get(account_id=details['moderator'])
                details['moderator'] = moderator.pk

        # Serialize the details for assessment creation
        serializer = AssessmentUpdateSerializer(instance=assessment, data=details)
        if serializer.is_valid():
            # Create the assessment within a transaction to ensure atomicity
            with transaction.atomic():
                serializer.save()

                if details.get('topics'):
                    topics = []
                    for name in details.get('topics'):
                        topic, _ = Topic.objects.get_or_create(name=name)
                        topics.append(topic)

                    assessment.topics.set(topics)
                    
                response = f'assessment {assessment.unique_identifier} has been successfully updated, the new updates will reflect imemdiately to all the students being assessed and their parents'
                audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='ASSESSMENT', target_object_id=str(assessment.assessment_id), outcome='UPDATED', response=response, school=requesting_account.school,)

            return {"message": response}
                
        # Return serializer errors if the data is not valid, format it as a string
        error_response = '; '.join([f"{key}: {', '.join(value)}" for key, value in serializer.errors.items()])
        audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='ASSESSMENT', target_object_id=str(assessment.assessment_id) if assessment else 'N/A', outcome='ERROR', response=f'Validation failed: {error_response}', school=requesting_account.school)

        return {"error": error_response}

    except Assessment.DoesNotExist:
        # Handle the case where the provided assessment ID does not exist
        return {'error': 'an assessment in your school with the provided credentials does not exist, please check the assessment details and try again'}

    except BaseUser.DoesNotExist:
        # Handle the case where the provided assessment ID does not exist
        return {'error': 'an account with the provided credentials does not exist. please check the moderators account ID and try again.'}

    except ValidationError as e:
        error_message = e.messages[0].lower() if isinstance(e.messages, list) and e.messages else str(e).lower()
        audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='ASSESSMENT', target_object_id=str(assessment.assessment_id) if assessment else 'N/A', outcome='ERROR', response=error_message, school=requesting_account.school)

        return {"error": error_message}

    except Exception as e:
        error_message = str(e)
        audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='ASSESSMENT', target_object_id=str(assessment.assessment_id) if assessment else 'N/A', outcome='ERROR', response=error_message, school=requesting_account.school)

        return {'error': error_message}


@database_sync_to_async
def update_student_grade(user, role, details):
    try:
        assessment = None  # Initialize assessment as None to prevent issues in error handling
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = users_utilities.get_account_and_linked_school(user, role)

        # Check if the user has permission to create an assessment
        if role != 'PRINCIPAL' and not permissions_utilities.has_permission(requesting_account, 'UPDATE', 'TRANSCRPIT'):
            response = f'could not proccess your request, you do not have the necessary permissions to update transcrpits.'
            audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='TRANSCRPIT', outcome='DENIED', response=response, school=requesting_account.school)

            return {'error': response}
                
        if not {'student', 'assessment'}.issubset(details):
            response = f'could not proccess your request, the provided information is invalid for the action you are trying to perform. please make sure to provide valid account and assessnt IDs and try again'
            audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='ACCOUNT', outcome='ERROR', response=response, school=requesting_account.school)

            return {'error': response}

        # Fetch the assessment from the requesting user's school
        assessment = requesting_account.school.assessments.select_related('assessor','moderator').get(assessment_id=details['assessment'])
        
        # Check if the user has permission to grade the assessment
        if (assessment.assessor and user != assessment.assessor.account_id) and (assessment.moderator and user != assessment.moderator.account_id):
            response = f'could not proccess your request, you do not have the necessary permissions to update this transcrpit. only the assessments assessor or moderator can update scores of this transcrpit.'
            audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='TRANSCRPIT', target_object_id=str(assessment.assessment_id) if assessment else 'N/A', outcome='DENIED', response=response, school=requesting_account.school)

            return {'error': response}

        transcript = assessment.scores.get(student__account_id=details['student'])

        serializer = TranscriptUpdateSerializer(instance=transcript, data=details)
        if serializer.is_valid():
            with transaction.atomic():
                serializer.save()

                response = f"student graded for assessment {assessment.unique_identifier} has been successfully updated."
                audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='TRANSCRPIT', target_object_id=str(assessment.assessment_id) if assessment else 'N/A', outcome='GRADED', response=response, school=assessment.school)

            return {"message": response}

        error_response = '; '.join([f"{key}: {', '.join(value)}" for key, value in serializer.errors.items()])
        audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='TRANSCRPIT', target_object_id=str(assessment.assessment_id) if assessment else 'N/A', outcome='ERROR', response=f'Validation failed: {error_response}', school=requesting_account.school)

        return {"error": error_response}

    except Assessment.DoesNotExist:
        # Handle the case where the provided assessment ID does not exist
        return {'error': 'an assessment in your school with the provided credentials does not exist, please check the assessment details and try again'}

    except Student.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'a student account with the provided credentials does not exist, please check the accounts details and try again'}

    except ValidationError as e:
        error_message = e.messages[0].lower() if isinstance(e.messages, list) and e.messages else str(e).lower()
        audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='TRANSCRPIT', target_object_id=str(assessment.assessment_id) if assessment else 'N/A', outcome='ERROR', response=error_message, school=requesting_account.school)

        return {"error": error_message}

    except Exception as e:
        error_message = str(e)
        audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='TRANSCRPIT', target_object_id=str(assessment.assessment_id) if assessment else 'N/A', outcome='ERROR', response=error_message, school=requesting_account.school)

        return {'error': error_message}


@database_sync_to_async
def update_assessment_as_collected(user, role, details):
    try:
        assessment = None  # Initialize assessment as None to prevent issues in error handling
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = users_utilities.get_account_and_linked_school(user, role)

        # Check if the user has permission to create an assessment
        if role != 'PRINCIPAL' and not permissions_utilities.has_permission(requesting_account, 'UPDATE', 'ASSESSMENT'):
            response = f'could not proccess your request, you do not have the necessary permissions to update assessments.'
            audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='ASSESSMENT', outcome='DENIED', response=response, school=requesting_account.school)

            return {'error': response}

        # Fetch the assessment from the requesting user's school
        assessment = requesting_account.school.assessments.get(assessment_id=details.get('assessment'))
        
        with transaction.atomic():
            assessment.mark_as_collected()

            response = f"assessment {assessment.unique_identifier} has been flagged as collected, any submissions going further will be marked as late submissions on the system."
            audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='ASSESSMENT', target_object_id=str(assessment.assessment_id), outcome='COLLECTED', response=response, school=assessment.school)

        return {"message": response}

    except Assessment.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'an assessment in your school with the provided credentials does not exist, please check the assessment details and try again'}

    except ValidationError as e:
        error_message = e.messages[0].lower() if isinstance(e.messages, list) and e.messages else str(e).lower()
        audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='ASSESSMENT', target_object_id=str(assessment.assessment_id) if assessment else 'N/A', outcome='ERROR', response=error_message, school=requesting_account.school)

        return {"error": error_message}

    except Exception as e:
        error_message = str(e)
        audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='ASSESSMENT', target_object_id=str(assessment.assessment_id) if assessment else 'N/A', outcome='ERROR', response=error_message, school=requesting_account.school)

        return {'error': error_message}


@database_sync_to_async
def release_assessment_grades(user, role, details):
    try:
        assessment = None  # Initialize assessment as None to prevent issues in error handling
        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = users_utilities.get_account_and_linked_school(user, role)

        # Check if the user has permission to create an assessment
        if role != 'PRINCIPAL' and not permissions_utilities.has_permission(requesting_account, 'UPDATE', 'ASSESSMENT'):
            response = f'could not proccess your request, you do not have the necessary permissions to update assessments.'
            audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='ASSESSMENT', outcome='DENIED', response=response, school=requesting_account.school)

            return {'error': response}

        # Fetch the assessment from the requesting user's school
        assessment = requesting_account.school.assessments.select_related('classroom', 'grade', 'subject').get(assessment_id=details.get('assessment'))
        
        with transaction.atomic():
            assessment.release_grades()

            not_submitted_student_ids = assessment.submissions.filter(status='NOT_SUBMITTED').only('student')

            not_submitted = []
            for submission in not_submitted_student_ids:
                not_submitted.append(Transcript(assessment=assessment, student=submission.student, score=0))

            Transcript.objects.bulk_create(not_submitted)

            assessment.update_pass_rate_and_average_score()
            assessment.subject.update_pass_rate_and_average_score()

            assessment.save()

            response = f"grades for assessment with assessment ID {assessment.unique_identifier} have been released, all the students who have not submitted the assessment have been graded a zero for the assessment."
            audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='ASSESSMENT', target_object_id=str(assessment.assessment_id), outcome='UPDATED', response=response, school=assessment.school)

        return {"message": response}

    except Assessment.DoesNotExist:
        # Handle the case where the provided account ID does not exist
        return {'error': 'an assessment in your school with the provided credentials does not exist, please check the assessment details and try again'}

    except ValidationError as e:
        error_message = e.messages[0].lower() if isinstance(e.messages, list) and e.messages else str(e).lower()
        audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='ASSESSMENT', target_object_id=str(assessment.assessment_id) if assessment else 'N/A', outcome='ERROR', response=error_message, school=requesting_account.school)

        return {"error": error_message}

    except Exception as e:
        error_message = str(e)
        audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='ASSESSMENT', target_object_id=str(assessment.assessment_id) if assessment else 'N/A', outcome='ERROR', response=error_message, school=requesting_account.school)

        return {'error': error_message}


@database_sync_to_async
def update_group_schedule_students(user, role, details):
    try:
        students_list = details.get('students', '').split(', ')
        if not students_list or students_list == ['']:
            return {'error': 'your request could not be proccessed.. no students were provided'}
        
        group_schedule = None  # Initialize assessment as None to prevent issues in error handling

        # Retrieve the requesting users account and related school in a single query using select_related
        requesting_account = users_utilities.get_account_and_linked_school(user, role)

        # Check if the user has permission to update classrooms
        if role != 'PRINCIPAL' and not permissions_utilities.has_permission(requesting_account, 'UPDATE', 'CLASSROOM'):
            response = f'could not proccess your request, you do not have the necessary permissions to update classroom details.'
            audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='CLASSROOM', outcome='DENIED', response=response, school=requesting_account.school)

            return {'error': response}

        group_schedule = Classroom.objects.select_related('grade', 'subject').get(classroom_id=details.get('class'), school=requesting_account.school)

        with transaction.atomic():
            # Check for validation errors and perform student updates
            error_message = group_schedule.update_students(students_list=students_list, remove=details.get('remove'))
            
        if error_message:
            return {'error': error_message}

        return {'message': f''}
    
    except Classroom.DoesNotExist:
        # Handle case where the classroom does not exist
        return {'error': 'a classroom in your school with the provided credentials does not exist. please check the classroom details and try again.'}

    except ValidationError as e:
        error_message = e.messages[0].lower() if isinstance(e.messages, list) and e.messages else str(e).lower()
        audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='CLASSROOM', target_object_id=str(group_schedule.group_schedule_id) if group_schedule else 'N/A', outcome='ERROR', response=error_message, school=requesting_account.school)

        return {"error": error_message}

    except Exception as e:
        error_message = str(e)
        audits_utilities.log_audit(actor=requesting_account, action='UPDATE', target_model='CLASSROOM', target_object_id=str(group_schedule.group_schedule_id) if group_schedule else 'N/A', outcome='ERROR', response=error_message, school=requesting_account.school)

        return {'error': error_message}


