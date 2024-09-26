# python
from datetime import date
from decimal import Decimal

# django
from django.test import TestCase
from django.core.exceptions import ValidationError
from django.utils import timezone

# models
from .models import Transcript
from schools.models import School
from users.models import Teacher, Student
from grades.models import Grade
from terms.models import Term
from subjects.models import Subject
from classrooms.models import Classroom
from assessments.models import Assessment
from submissions.models import Submission


class TranscriptModelTest(TestCase):
    
    def setUp(self):
        """
        Set up initial data, including a student, an assessment, and a submission 
        for the student.
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
        self.student = Student.objects.create(
            name="Alice", 
            surname= 'Wang',
            id_number= '0208285344080',
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
            collected= True,
            term= self.term_1,
            classroom= self.classroom,
            subject= self.subject,
            grade= self.grade,
            school= self.school,
        )

        # Create a submission for the student and the assessment
        self.submission = Submission.objects.create(
            student=self.student,
            assessment=self.assessment,
            status='ONTIME',
        )
    
    def test_create_transcript(self):
        """
        Test that a transcript can be created with a valid score, and weighted score is calculated correctly.
        """
        transcript = Transcript.objects.create(student=self.student, assessment=self.assessment, score=Decimal('80.00'))
        # Check if weighted score is correctly calculated
        self.assertEqual(transcript.weighted_score, (transcript.score / self.assessment.total) * 100)
    
    def test_score_above_total(self):
        """
        Test that a score above the assessment's total raises a validation error.
        """
        with self.assertRaises(ValidationError) as e:
            Transcript.objects.create(student=self.student, assessment=self.assessment, score=Decimal('110.00'))

    def test_moderated_score_above_total(self):
        """
        Test that a moderated score above the assessment's total raises a validation error.
        """
        with self.assertRaises(ValidationError) as e:
            Transcript.objects.create(student=self.student, assessment=self.assessment, moderated_score=Decimal('110.00'))

    def test_no_submission(self):
        """
        Test that trying to create a transcript without a submission raises an error.
        """
        # Delete the submission to simulate no submission
        self.submission.delete()

        with self.assertRaises(ValidationError) as e:
            Transcript.objects.create(student=self.student, assessment=self.assessment, score=Decimal('85.00'))

    def test_assessment_not_collected(self):
        """
        Test that trying to create a transcript for an assessment that hasn't been collected raises an error.
        """
        # Modify the assessment to not collected
        self.assessment.collected = False
        self.assessment.save()

        with self.assertRaises(ValidationError) as e:
            Transcript.objects.create(student=self.student, assessment=self.assessment, score=Decimal('75.00'))

    def test_unique_constraint(self):
        """
        Test that the unique constraint on the student-assessment pair is enforced.
        """
        # Create a first transcript
        Transcript.objects.create(student=self.student, assessment=self.assessment, score=Decimal('80.00'))

        # Try to create a second transcript for the same student and assessment, which should fail
        with self.assertRaises(ValidationError) as e:
            Transcript.objects.create(student=self.student, assessment=self.assessment, score=Decimal('90.00'))

    def test_weighted_score_with_moderation(self):
        """
        Test that the weighted score is correctly calculated when a moderated score is provided.
        """
        transcript = Transcript.objects.create(student=self.student, assessment=self.assessment, score=Decimal('75.00'), moderated_score=Decimal('90.00'))
        # Check if weighted score is calculated based on moderated score
        self.assertEqual(transcript.weighted_score, (transcript.moderated_score / self.assessment.total) * 100)
