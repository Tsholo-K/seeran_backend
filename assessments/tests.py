# python
from datetime import timedelta

# django
from django.test import TestCase
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.db import IntegrityError

# models
from .models import Assessment, Transcript
from users.models import CustomUser
from schools.models import School, Term
from grades.models import Grade, Subject
from classes.models import Classroom


class AssessmentTest(TestCase):
    """
    Test cases for the Assessment model.
    """

    def setUp(self):
        """
        Set up the test environment by creating necessary instances.
        """
        self.school = School.objects.create(
            name="Test School",
            email="testschool@example.com",
            contact_number="1234567890",
            school_type="PRIMARY",
            province="GAUTENG",
            school_district="JHB NORTH"
        )
        self.grade = Grade.objects.create(
            grade='8',
            major_subjects=2,
            none_major_subjects=1,
            school=self.school
        )
        self.term = Term.objects.create(
            term=1,
            start_date=timezone.now().date(),
            end_date=timezone.now().date() + timedelta(days=30),
            weight=20.00,
            school=self.school
        )
        self.subject = Subject.objects.create(
            grade=self.grade,
            subject='ENGLISH',
            major_subject=True,
            pass_mark=50.00
        )
        self.teacher = CustomUser.objects.create_user(
            email='student@example.com',
            name="John",
            surname="Doe",
            role="TEACHER",
            school=self.school,
        )
        self.classroom = Classroom.objects.create(
            teacher=self.teacher,
            classroom_identifier='124',
            group='A',
            grade=self.grade,
            subject=self.subject,
            school=self.school,
        )

    def test_create_assessment(self):
        """
        Test the creation of an Assessment with valid data.
        """
        assessment = Assessment.objects.create(
            title='Midterm Exam',
            set_by=self.teacher,
            total=100,
            formal=True,
            percentage_towards_term_mark=30.00,
            term=self.term,
            classroom=self.classroom,
            subject=self.subject,
            grade=self.grade,
            school=self.school,
            due_date=timezone.now() + timezone.timedelta(days=10),
            unique_identifier='MIDTERM001'
        )
        self.assertEqual(assessment.title, 'Midterm Exam')
        self.assertEqual(assessment.total, 100)
        self.assertEqual(assessment.percentage_towards_term_mark, 30.00)

    def test_due_date_validation(self):
        """
        Test validation of the due_date field to ensure it is in the future.
        """
        future_date = timezone.now().date() + timedelta(days=30)
        past_date = timezone.now().date() - timedelta(days=30)
        
        # Test valid due date
        valid_assessment = Assessment(
            title='Valid Assessment',
            set_by=self.teacher,
            total=100,
            percentage_towards_term_mark=30.00,
            term=self.term,
            due_date=future_date,
            unique_identifier='VALID001',
            subject=self.subject,
            grade=self.grade,
            school=self.school,
        )
        valid_assessment.clean()  # Should not raise any validation error

        # Test invalid due date
        invalid_assessment = Assessment(
            title='Invalid Assessment',
            set_by=self.teacher,
            total=100,
            percentage_towards_term_mark=30.00,
            term=self.term,
            due_date=past_date,
            unique_identifier='INVALID001',
            subject=self.subject,
            grade=self.grade,
            school=self.school,

        )
        with self.assertRaises(ValidationError):
            invalid_assessment.clean()

    def test_percentage_constraint(self):
        """
        Test that the total percentage towards the term does not exceed 100%.
        """
        Assessment.objects.create(
            title='First Assessment',
            set_by=self.teacher,
            total=100,
            percentage_towards_term_mark=40.00,
            term=self.term,
            due_date=timezone.now() + timezone.timedelta(days=10),
            unique_identifier='FIRST001',
            subject=self.subject,
            grade=self.grade,
            school=self.school,

        )
        
        # Test exceeding percentage constraint
        assessment = Assessment(
            title='Second Assessment',
            set_by=self.teacher,
            total=100,
            percentage_towards_term_mark=70.00,
            term=self.term,
            due_date=timezone.now() + timezone.timedelta(days=10),
            unique_identifier='SECOND001',
            subject=self.subject,
            grade=self.grade,
            school=self.school,
        )
        with self.assertRaises(ValidationError):
            assessment.clean()

    def test_mark_as_collected(self):
        """
        Test the functionality of marking an assessment as collected.
        """
        assessment = Assessment.objects.create(
            title='Collection Test',
            set_by=self.teacher,
            total=100,
            percentage_towards_term_mark=10.00,
            term=self.term,
            due_date=timezone.now() + timezone.timedelta(days=10),
            unique_identifier='COLLECT001',
            subject=self.subject,
            grade=self.grade,
            school=self.school,
        )
        assessment.students_assessed.add(self.teacher)
        assessment.mark_as_collected(submitted_students_list=[self.teacher.id])
        
        self.assertIn(self.teacher, assessment.ontime_submission.all())
        self.assertNotIn(self.teacher, assessment.late_submission.all())

    def test_mark_as_released_without_submition(self):
        """
        Test the functionality of marking an assessment as released.
        """
        assessment = Assessment.objects.create(
            title='Release Test',
            set_by=self.teacher,
            total=100,
            percentage_towards_term_mark=10.00,
            term=self.term,
            due_date=timezone.now() + timezone.timedelta(days=10),
            unique_identifier='RELEASE001',
            subject=self.subject,
            grade=self.grade,
            school=self.school,
        )
        assessment.students_assessed.add(self.teacher)
        assessment.mark_as_collected(submitted_students_list=[])
        assessment.mark_as_released()
        
        # Check that students who didn't submit received a score of 0
        transcript = Transcript.objects.get(student=self.teacher, assessment=assessment)
        self.assertEqual(transcript.score, 0)

    def test_mark_as_released_with_submition(self):
        """
        Test the functionality of marking an assessment as released.
        """
        assessment = Assessment.objects.create(
            title='Release Test',
            set_by=self.teacher,
            total=100,
            percentage_towards_term_mark=10.00,
            term=self.term,
            due_date=timezone.now() + timezone.timedelta(days=10),
            unique_identifier='RELEASE001',
            subject=self.subject,
            grade=self.grade,
            school=self.school,
        )
        assessment.students_assessed.add(self.teacher)
        assessment.mark_as_collected(submitted_students_list=[self.teacher.id])
        self.transcript = Transcript.objects.create(
            student=self.teacher,
            assessment=assessment,
            score=70.00, 
            moderated_score=None
        )
        assessment.mark_as_released()
        
        # Check that students who didn't submit received a score of 0
        transcript = Transcript.objects.get(student=self.teacher, assessment=assessment)
        self.assertEqual(transcript.score, 70.00)


class TranscriptTest(TestCase):
    """
    Test cases for the Transcript model.
    """

    def setUp(self):
        """
        Set up the test environment by creating necessary instances.
        """
        self.school = School.objects.create(
            name="Test School",
            email="testschool@example.com",
            contact_number="1234567890",
            school_type="PRIMARY",
            province="GAUTENG",
            school_district="JHB NORTH"
        )
        self.grade = Grade.objects.create(
            grade='7',
            major_subjects=1,
            none_major_subjects=2,
            school=self.school
        )
        self.term = Term.objects.create(
            term=1,
            start_date=timezone.now().date(),
            end_date=timezone.now().date() + timedelta(days=30),
            weight=20.00,
            school=self.school
        )
        self.subject = Subject.objects.create(
            grade=self.grade,
            subject='ENGLISH',
            major_subject=True,
            pass_mark=50.00
        )
        self.student = CustomUser.objects.create_user(
            name="John",
            surname="Doe",
            role="STUDENT",
            school=self.school,
            grade=self.grade,
            passport_number='845751548'
        )
        self.assessment = Assessment.objects.create(
            set_by=None,
            title='Test Assessment',
            total=100,
            percentage_towards_term_mark=50.00,
            term=self.term,
            subject=self.subject,
            grade=self.grade,
            school=self.school,
            due_date=timezone.now() + timezone.timedelta(days=10),
            unique_identifier='TEST001'
        )

    def test_create_transcript(self):
        """
        Test the creation of a Transcript with valid data.
        """
        transcript = Transcript.objects.create(
            student=self.student,
            score=85.00,
            assessment=self.assessment
        )
        self.assertEqual(transcript.score, 85.00)
        self.assertEqual(transcript.student, self.student)

    def test_score_validation(self):
        """
        Test validation of the score field to ensure it is within the valid range.
        """
        valid_transcript = Transcript(
            student=self.student,
            score=90.00,
            assessment=self.assessment
        )
        valid_transcript.clean()  # Should not raise any validation error

        # Test invalid score
        invalid_transcript = Transcript(
            student=self.student,
            score=110.00,  # Exceeds the total score
            assessment=self.assessment
        )
        with self.assertRaises(ValidationError):
            invalid_transcript.clean()

    def test_moderated_score_validation(self):
        """
        Test validation of the moderated_score field to ensure it is within the valid range.
        """
        transcript = Transcript.objects.create(
            student=self.student,
            score=85.00,
            moderated_score=90.00,
            assessment=self.assessment
        )
        self.assertEqual(transcript.moderated_score, 90.00)

        # Test invalid moderated score
        invalid_transcript = Transcript(
            student=self.student,
            score=85.00,
            moderated_score=110.00,  # Exceeds the total score
            assessment=self.assessment
        )
        with self.assertRaises(ValidationError):
            invalid_transcript.clean()