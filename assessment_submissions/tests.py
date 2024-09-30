# python
from datetime import date
from decimal import Decimal

# django
from django.test import TestCase
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.test import TestCase
from django.core.exceptions import ValidationError

# models
from .models import AssessmentSubmission
from schools.models import School
from accounts.models import Teacher, Student
from grades.models import Grade
from terms.models import Term
from subjects.models import Subject
from classrooms.models import Classroom
from assessments.models import Assessment


class SubmissionModelTest(TestCase):
    def setUp(self):
        """
        Set up initial data that will be used for the tests, including creating 
        a student and an assessment for them to submit work for.
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
            grade= self.grade
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

        # Create an assessment
        self.assessment = Assessment.objects.create(
            title= 'Midterm Exam',
            assessor= self.teacher,
            start_time= timezone.now() + timezone.timedelta(days=10),
            dead_line= timezone.now() + timezone.timedelta(hours=2) + timezone.timedelta(days=10),
            total= Decimal(100),
            percentage_towards_term_mark= Decimal(30.00),
            term= self.term_1,
            classroom= self.classroom,
            subject= self.subject,
            grade= self.grade,
            school= self.school,
        )

        self.submission_data = {
            'student': self.student_a,
            'assessment': self.assessment,
            'status': 'ONTIME'
        }

    def test_submission_created_on_time(self):
        """
        Test that a submission marked as 'ONTIME' is saved correctly.
        """
        submission = AssessmentSubmission.objects.create(**self.submission_data)
        self.assertEqual(submission.status, 'ONTIME')
        self.assertEqual(submission.student, self.student_a)
        self.assertEqual(submission.assessment, self.assessment)

    def test_late_submission(self):
        """
        Test that a submission after the deadline is marked as 'LATE'.
        """
        # Modify the assessment to simulate the deadline passing
        self.assessment.start_time = timezone.now() - timezone.timedelta(days=1) - timezone.timedelta(hours=2)  # start time was yesterday
        self.assessment.dead_line = timezone.now() - timezone.timedelta(days=1)  # Deadline was yesterday
        self.assessment.save()

        submission = AssessmentSubmission.objects.create(student=self.student_a, assessment=self.assessment)

        # Since the deadline has passed, it should be marked as 'LATE'
        self.assertEqual(submission.status, 'LATE')

    def test_unique_constraint(self):
        """
        Test that only one submission per student per assessment is allowed.
        """
        # Create the first submission
        AssessmentSubmission.objects.create(student=self.student_a, assessment=self.assessment, status='ONTIME')

        # Try to create a second submission, which should raise a ValidationError due to the unique constraint
        with self.assertRaises(ValidationError):
            AssessmentSubmission.objects.create(student=self.student_a, assessment=self.assessment, status='LATE')

    def test_submission_date_validation(self):
        """
        Test that a submission date earlier than the assessment's set date raises a validation error.
        """
        # Set the submission date to before the assessment was set
        with self.assertRaises(ValidationError):
            AssessmentSubmission.objects.create(
                student=self.student_a,
                assessment=self.assessment,
                submission_date=timezone.now() - timezone.timedelta(days=3)  # 3 days ago, before the assessment was set
            )

    def test_excused_submission(self):
        """
        Test that a submission marked as 'EXCUSED' behaves as expected.
        """
        submission = AssessmentSubmission.objects.create(student=self.student_a, assessment=self.assessment, status='EXCUSED')
        self.assertEqual(submission.status, 'EXCUSED')
