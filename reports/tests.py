# python
from datetime import timedelta

# django
from django.test import TestCase
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.db import IntegrityError

# models
from .models import ReportCard, StudentSubjectScore
from users.models import CustomUser
from schools.models import School
from grades.models import Grade, Term, Subject
from assessments.models import Assessment, Transcript
from classes.models import Classroom


class StudentSubjectScoreTest(TestCase):
    def setUp(self):
        self.school = School.objects.create(
            name="Test School",
            email="testschool@example.com",
            contact_number="1234567890",
            type="PRIMARY",
            province="GAUTENG",
            district="JHB NORTH"
        )
        self.grade = Grade.objects.create(
            grade='7',
            major_subjects=2,
            none_major_subjects=1,
            school=self.school
        )
        self.term = Term.objects.create(
            term=1,
            start_date=timezone.now().date(),
            end_date=timezone.now().date() + timedelta(days=30),
            weight=20.00,
            grade=self.grade,
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
            subject=self.subject, 
            term=self.term,
            school=self.school,
            grade=self.grade,
            assessment_type='EXAMINATION',
            unique_identifier='exam1',
            due_date=timezone.now().date() + timedelta(days=7),
            formal=True,
            total=100.00,
            percentage_towards_term_mark=50.00
        )
        self.transcript = Transcript.objects.create(
            student=self.student,
            assessment=self.assessment,
            score=70.00, 
            moderated_score=None
        )
    
    def test_score_range_validation(self):
        """ Test that score and weighted_score are within valid ranges. """
        score = StudentSubjectScore(
            student=self.student, 
            term=self.term, 
            score=105, 
            weighted_score=50, 
            subject=self.subject, 
            grade=self.grade, 
            school=self.school
        )
        with self.assertRaises(ValidationError):
            score.clean()

        score.score = 50
        score.weighted_score = 105
        with self.assertRaises(ValidationError):
            score.clean()

    def test_calculate_term_score(self):
        """ Test that the term score is calculated correctly. """
        score = StudentSubjectScore.objects.create(
            student=self.student, 
            term=self.term, 
            score=None, 
            weighted_score=None, 
            subject=self.subject, 
            grade=self.grade, 
            school=self.school
        )
        score.calculate_term_score()
        self.assertEqual(score.score, 35)  # Assuming transcript score and weight calculation leads to this result

    def test_calculate_weighted_score(self):
        """ Test that the weighted score is calculated correctly. """
        score = StudentSubjectScore.objects.create(
            student=self.student, 
            term=self.term, 
            score=35.00, 
            weighted_score=None, 
            subject=self.subject, 
            grade=self.grade, 
            school=self.school
        )
        score.calculate_weighted_score()
        self.assertEqual(score.weighted_score, 7.00)  # Assuming term weight is 100

    def test_unique_constraint(self):
        """ Test that duplicate StudentSubjectScore raises an IntegrityError. """
        StudentSubjectScore.objects.create(
            student=self.student, 
            term=self.term, 
            score=85, 
            weighted_score=90, 
            subject=self.subject, 
            grade=self.grade, 
            school=self.school
        )
        with self.assertRaises(IntegrityError):
            StudentSubjectScore.objects.create(
                student=self.student, 
                term=self.term, 
                score=75, 
                weighted_score=80, 
                subject=self.subject, 
                grade=self.grade, 
                school=self.school
            )


class ReportCardTest(TestCase):
    def setUp(self):
        self.school = School.objects.create(
            name="Test School",
            email="testschool@example.com",
            contact_number="1234567890",
            type="PRIMARY",
            province="GAUTENG",
            district="JHB NORTH"
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
            grade=self.grade,
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
        self.classroom = Classroom.objects.create(
            classroom_number='124',
            group='A',
            grade=self.grade,
            subject=self.subject,
            school=self.school,
        )
        self.classroom.students.set([self.student])
        self.assessment = Assessment.objects.create(
            subject=self.subject, 
            term=self.term,
            school=self.school,
            grade=self.grade,
            assessment_type='EXAMINATION',
            unique_identifier='exam1',
            due_date=timezone.now().date() + timedelta(days=7),
            formal=True,
            total=100.00,
            percentage_towards_term_mark=50.00
        )
        self.report = ReportCard.objects.create(
            student=self.student, 
            term=self.term, 
            days_absent=0, 
            days_late=0, 
            attendance_percentage=100, 
            passed=True, 
            year_end_report=False, 
            school=self.school
        )

    def test_attendance_percentage(self):
        """ Test that attendance percentage is calculated correctly. """
        self.report.calculate_attendance_percentage()
        self.assertEqual(self.report.attendance_percentage, 100)

    def test_pass_status(self):
        """ Test that the pass status is determined correctly. """
        self.report.determine_pass_status()
        self.assertTrue(self.report.passed)

    def test_generate_subject_scores(self):
        """ Test that subject scores are generated correctly for the report. """
        self.report.generate_subject_scores()
        self.assertEqual(self.report.subject_scores.count(), 1)

    def test_unique_constraint(self):
        """ Test that duplicate ReportCard raises an IntegrityError. """
        with self.assertRaises(IntegrityError):
            ReportCard.objects.create(
                student=self.student, 
                term=self.term, 
                days_absent=0, 
                days_late=1, 
                attendance_percentage=90.00, 
                passed=False, 
                year_end_report=False, 
                school=self.school
            )
