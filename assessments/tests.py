# python
from datetime import date
from decimal import Decimal

# django
from django.test import TestCase
from django.core.exceptions import ValidationError
from django.utils import timezone

# models
from .models import Assessment
from schools.models import School
from accounts.models import BaseAccount, Teacher, Student
from grades.models import Grade
from terms.models import Term
from subjects.models import Subject
from classrooms.models import Classroom
from assessment_submissions.models import AssessmentSubmission
from assessment_transcripts.models import AssessmentTranscript


class AssessmentTest(TestCase):
    """
    Test cases for the Assessment model.
    """

    def setUp(self):
        """
        Set up the test environment by creating necessary instances.
        """

        # Create secondary school instance for testing
        self.school = School.objects.create(
            name='Test School',
            email_address='secondaryschool@example.com',
            contact_number='0123456789',
            student_count=130,
            teacher_count=24,
            admin_count=19,
            in_arrears=False,
            none_compliant=False,
            type='SECONDARY',
            province='GAUTENG',
            district='GAUTENG WEST',
            grading_system='A-F Grading',
            library_details='Well-stocked library',
            laboratory_details='State-of-the-art labs',
            sports_facilities='Football field, Basketball court',
            operating_hours='07:45 - 14:00',
            location='456 INNER St',
            website='https://secondaryschool.com',
        )

        # Create a Grade instance linked to the School
        self.grade = Grade.objects.create(
            major_subjects= 1, 
            none_major_subjects= 2,
            grade= '10', 
            school= self.school
        )
        
        # Create a Subject instance linked to the Grade
        self.subject = Subject.objects.create(
            subject= 'MATHEMATICS',
            major_subject= True,
            pass_mark= 50.00,
            student_count= 3,
            teacher_count= 1,
            classroom_count= 1,
            grade= self.grade,
            school= self.school
        )

        # Create a Term instance linked to the Grade
        self.term_1 = Term.objects.create(
            term= 'Term 1',
            weight= Decimal('20.00'),
            start_date= date(2024, 1, 15),
            end_date= date(2024, 4, 10),
            grade= self.grade,
            school= self.school
        )

        # Create a Term instance linked to the Grade
        self.term_2 = Term.objects.create(
            term= 'Term 2',
            weight= Decimal('20.00'),
            start_date= date(2024, 4, 25),
            end_date= date(2024, 7, 1),
            grade= self.grade,
            school= self.school
        )

        # Create a Teacher instance linked to the School
        self.teacher = Teacher.objects.create(
            name="John Doe",
            surname= 'Doe',
            email_address= 'testteacher@example.com',
            role= 'TEACHER',
            school= self.school
        )

        # Create a Student instance linked to the School
        self.student_a = Student.objects.create(
            name="Alice", 
            surname= 'Wang',
            id_number= '0208285344080',
            role= 'STUDENT',
            grade= self.grade,
            school= self.school
        )

        # Create a Student instance linked to the School
        self.student_b = Student.objects.create(
            name="Bob", 
            surname= 'Marly',
            passport_number= '652357849',
            role= 'STUDENT',
            grade= self.grade,
            school= self.school
        )

        # Create a Student instance linked to the School
        self.student_c = Student.objects.create(
            name="Frank", 
            surname= 'Caitlyn',
            passport_number= '652357864',
            role= 'STUDENT',
            grade= self.grade,
            school= self.school
        )

        self.classroom = Classroom.objects.create(
            classroom_number= 'E pod 403',
            group= '10A',
            teacher= self.teacher,
            grade= self.grade,
            subject= self.subject,
            school= self.school,
        )

        self.assessment_data = {
            'title': 'Midterm Exam',
            'assessor': self.teacher,
            'start_time': timezone.now() + timezone.timedelta(days=10),
            'dead_line': timezone.now() + timezone.timedelta(hours=2) + timezone.timedelta(days=10),
            'total': Decimal(100),
            'percentage_towards_term_mark': Decimal(30.00),
            'term': self.term_1,
            'classroom': self.classroom,
            'subject': self.subject,
            'grade': self.grade,
            'school': self.school,
        }

    def test_create_assessment(self):
        """
        Test that we can create an assessment successfully with valid data.
        """
        assessment = Assessment.objects.create(**self.assessment_data)

        self.assertIsNotNone(assessment.pk)
        self.assertEqual(assessment.total, Decimal(100.00))
        self.assertEqual(assessment.title, 'Midterm Exam')
        self.assertEqual(assessment.assessor, self.teacher)
        self.assertEqual(assessment.percentage_towards_term_mark, Decimal(30.00))
        self.assertEqual(assessment.term, self.term_1)

    def test_role_validation_for_assessor_and_moderator(self):
        """
        Test that only principals, admins, and teachers can set assessments.
        """
        assessment_data = self.assessment_data.copy()

        invalid_user = BaseAccount.objects.create(name="invalid_assessor", surname="invalid_assessor", role="STUDENT")

        assessment_data['assessor'] = invalid_user
        assessment_a = Assessment(**assessment_data)

        with self.assertRaises(ValidationError):
            assessment_a.clean()  # Validate
        
        assessment_data['assessor'] = None
        assessment_data['moderator'] = invalid_user
        assessment_b = Assessment(**assessment_data)

        with self.assertRaises(ValidationError):
            assessment_b.clean()  # Validate

    def test_assessment_invalid_percentage_towards_term_mark(self):
        """
        Test that an assessment's percentage towards term mark cannot be less than 0 or more than 100.
        """
        assessment_data = self.assessment_data.copy()

        assessment_data['percentage_towards_term_mark'] = -1
        assessment_a = Assessment(**assessment_data)

        with self.assertRaises(ValidationError):
            assessment_a.clean()  # Validate

        assessment_data['percentage_towards_term_mark'] = 101
        assessment_b = Assessment(**assessment_data)

        with self.assertRaises(ValidationError):
            assessment_b.clean()  # Validate

    def test_start_time_before_deadline(self):
        """
        Test that the start time must be before the deadline.
        """
        assessment_data = self.assessment_data.copy()

        assessment_data['start_time'] = timezone.now()
        assessment_data['dead_line'] = timezone.now() - timezone.timedelta(minutes=1)
        assessment = Assessment(**assessment_data)

        with self.assertRaises(ValidationError):
            assessment.clean()  # Validate

    def test_mark_as_collected(self):
        """
        Test that an assessment can be marked as collected after the deadline or if all submissions are in.
        """
        self.classroom.update_students([self.student_a.account_id, self.student_b.account_id, self.student_c.account_id]) # add students to the classroom

        assessment_data = self.assessment_data.copy()
        assessment_data['percentage_towards_term_mark'] = Decimal(15) # modify assessment percentage towards term mark so the assessment dont cause and error

        assessment_a = Assessment.objects.create(**assessment_data) # normal assessment with start time and deadline in the future

        with self.assertRaises(ValidationError):
            assessment_a.mark_as_collected()  # Should not allow marking as collected as the start time has not elapsed

        assessment_data['start_time'] = timezone.now() - timezone.timedelta(minutes=5) # adjust start time to 5 min ago

        assessment_b = Assessment.objects.create(**assessment_data) # normal assessment with start time 5 min ago and deadline in the future

        with self.assertRaises(ValidationError):
            assessment_b.mark_as_collected()  # Should not allow marking as collected as the deadline has not elapsed and not all students have submitted the assessment

        if assessment_b.classroom and assessment_b.classroom.students.exists(): # mark all students in the classroom as submitted
            submissions = []
            for student in assessment_b.classroom.students.all():
                submissions.append(AssessmentSubmission(assessment=assessment_b, student=student, status='ON_TIME'))
            
            batch_size = 50
            for i in range(0, len(submissions), batch_size):
                AssessmentSubmission.objects.bulk_create(submissions[i:i + batch_size])

        assessment_b.mark_as_collected()  # Should allow marking as collected as all students have submitted the assessment, even tho the deadline is not elapsed
        self.assertTrue(assessment_b.collected)

        assessment_data['dead_line'] = timezone.now() - timezone.timedelta(minutes=5) # adjust deadline to 5 min ago

        assessment_c = Assessment.objects.create(**assessment_data) # normal assessment with both start time and deadline elapsed
        assessment_c.mark_as_collected()  # Should allow marking as collected as the deadline has elapsed
        self.assertTrue(assessment_c.collected)

        assessment_data['classroom'] = None # make the assessment a grade wide assessment
        assessment_data['dead_line'] = timezone.now() + timezone.timedelta(minutes=5) # adjust deadline to 5 min in the future
        assessment_d = Assessment.objects.create(**assessment_data) # normal assessment with deadline in the future

        with self.assertRaises(ValidationError):
            assessment_d.mark_as_collected()  # Should not allow marking as collected as the deadline has not elapsed and not all students have submitted the assessment

        if not assessment_d.classroom and assessment_d.grade.students.exists(): # mark all students in the grade as submitted
            non_submissions = []
            for student in assessment_d.grade.students.all():
                non_submissions.append(AssessmentSubmission(assessment=assessment_d, student=student, status='ON_TIME'))
            
            batch_size = 50
            for i in range(0, len(non_submissions), batch_size):
                AssessmentSubmission.objects.bulk_create(non_submissions[i:i + batch_size])

        assessment_d.mark_as_collected()  # Should allow marking as collected as all students have submitted the assessment, even tho the deadline is not elapsed
        self.assertTrue(assessment_d.collected)

        assessment_data['collected'] = True

        assessment_d = Assessment.objects.create(**assessment_data) # normal assessment with start time and deadline in the future

        with self.assertRaises(ValidationError):
            assessment_d.mark_as_collected()  # Should not allow marking as collected as the assessment has already been collected

    def test_release_grades(self):
        """
        Test that grades can only be released when all submissions are graded.
        """
        self.classroom.update_students([self.student_a.account_id, self.student_b.account_id, self.student_c.account_id]) # add students to the classroom

        assessment_data = self.assessment_data.copy()
        assessment_data['percentage_towards_term_mark'] = Decimal(15) # modify assessment percentage towards term mark so the assessment dont cause and error

        assessment_a = Assessment.objects.create(**assessment_data)

        with self.assertRaises(ValidationError):
            assessment_a.release_grades()  # Should not allow releasing grades as the assessment has not been collected

        assessment_data['collected'] = True # modify assessment collected field so we can release grades
        assessment_data['start_time'] = timezone.now() - timezone.timedelta(minutes=5)
        assessment_data['date_collected'] = timezone.now()

        assessment_b = Assessment.objects.create(**assessment_data)

        assessment_b.release_grades()  # Should allow for releasing grades as the assessment has been collected
        self.assertTrue(assessment_b.grades_released)

        assessment_c = Assessment.objects.create(**assessment_data)

        if assessment_c.classroom and assessment_c.classroom.students.exists(): # mark all students in the classroom as submitted
            submissions = []
            for student in assessment_c.classroom.students.all():
                submissions.append(AssessmentSubmission(assessment=assessment_c, student=student, status='ON_TIME'))

            batch_size = 50
            for i in range(0, len(submissions), batch_size):
                AssessmentSubmission.objects.bulk_create(submissions[i:i + batch_size])

        with self.assertRaises(ValidationError):
            assessment_c.release_grades()  # Should not allow releasing grades because not all submissions are graded

        assessment_d = Assessment.objects.create(**assessment_data)

        if assessment_d.classroom and assessment_d.classroom.students.exists(): # mark all students in the classroom as submitted
            submissions = []
            transcripts = []
            for student in assessment_d.classroom.students.all():
                submissions.append(AssessmentSubmission(assessment=assessment_d, student=student, status='ON_TIME'))
                transcripts.append(AssessmentTranscript(assessment=assessment_d, student=student, score=50, weighted_score=7.5, comment=''))

            batch_size = 50
            for i in range(0, len(submissions), batch_size):
                AssessmentSubmission.objects.bulk_create(submissions[i:i + batch_size])

            for i in range(0, len(transcripts), batch_size):
                AssessmentTranscript.objects.bulk_create(transcripts[i:i + batch_size])

        assessment_d.release_grades()  # Should allow for releasing grades as all submissions have been graded
        self.assertTrue(assessment_d.grades_released)

    def test_update_performance_metrics(self):
        """
        Test that performance metrics (pass rate, failure rate, etc.) are updated correctly.
        """
        self.classroom.update_students([self.student_a.account_id, self.student_b.account_id, self.student_c.account_id]) # add students to the classroom

        # Create assessment and simulate the release of grades, and calculation of metrics
        assessment_data = self.assessment_data.copy()

        assessment_data['percentage_towards_term_mark'] = Decimal(15) # modify assessment percentage towards term mark so the assessment dont cause and error
        assessment_data['collected'] = True # modify assessment collected field so we can release grades
        assessment_data['start_time'] = timezone.now() - timezone.timedelta(minutes=5)
        assessment_data['date_collected'] = timezone.now()

        assessment_a = Assessment.objects.create(**assessment_data)

        if assessment_a.classroom and assessment_a.classroom.students.exists(): # mark all students in the classroom as submitted
            submissions = []
            transcripts = []
            for student in assessment_a.classroom.students.all():
                submissions.append(AssessmentSubmission(assessment=assessment_a, student=student, status='ON_TIME'))
                transcripts.append(AssessmentTranscript(assessment=assessment_a, student=student, score=50, weighted_score=7.5, comment=''))

            batch_size = 50
            for i in range(0, len(submissions), batch_size):
                AssessmentSubmission.objects.bulk_create(submissions[i:i + batch_size])

            for i in range(0, len(transcripts), batch_size):
                AssessmentTranscript.objects.bulk_create(transcripts[i:i + batch_size])

        # Simulate grades being calculated
        assessment_a.release_grades()
        assessment_a.update_performance_metrics()
        self.assertIsNotNone(assessment_a.pass_rate)
        self.assertIsNotNone(assessment_a.average_score)

