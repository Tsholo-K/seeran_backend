# python
import uuid
from datetime import timedelta

# django
from django.test import TestCase
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.db import IntegrityError

# models
from .models import ReportCard, StudentSubjectScore
from users.models import CustomUser
from schools.models import School, Term
from grades.models import Grade, Subject
from attendances.models import Absent, Late
from assessments.models import Assessment, Transcript


class StudentSubjectScoreTest(TestCase):
    def setUp(self):
        self.school = School.objects.create(name="Test School")
        self.grade = Grade.objects.create(grade="8", grade_order=1, major_subjects=1, none_major_subjects=1, school=self.school)
        self.term = Term.objects.create(name="Term 1", start_date=timezone.now(), end_date=timezone.now() + timedelta(days=30), weight=100, school=self.school)
        self.subject = Subject.objects.create(grade=self.grade, subject="Math", major_subject=True, pass_mark=50, school=self.school)
        self.student = CustomUser.objects.create(username="student1", grade=self.grade, school=self.school)
        self.assessment = Assessment.objects.create(subject=self.subject, term=self.term, formal=True, percentage_towards_term_mark=50)
        self.transcript = Transcript.objects.create(student=self.student, assessment=self.assessment, score=70, moderated_score=None)
    
    def test_score_range_validation(self):
        """ Test that score and weighted_score are within valid ranges. """
        score = StudentSubjectScore(
            student=self.student, term=self.term, score=105, weighted_score=50, subject=self.subject, grade=self.grade, school=self.school
        )
        with self.assertRaises(ValidationError):
            score.clean()

        score.score = 50
        score.weighted_score = 105
        with self.assertRaises(ValidationError):
            score.clean()

    def test_unique_constraint(self):
        """ Test that duplicate StudentSubjectScore raises an IntegrityError. """
        StudentSubjectScore.objects.create(
            student=self.student, term=self.term, score=85, weighted_score=90, subject=self.subject, grade=self.grade, school=self.school
        )
        with self.assertRaises(IntegrityError):
            StudentSubjectScore.objects.create(
                student=self.student, term=self.term, score=75, weighted_score=80, subject=self.subject, grade=self.grade, school=self.school
            )

    def test_calculate_term_score(self):
        """ Test that the term score is calculated correctly. """
        score = StudentSubjectScore.objects.create(
            student=self.student, term=self.term, score=None, weighted_score=None, subject=self.subject, grade=self.grade, school=self.school
        )
        score.calculate_term_score()
        self.assertEqual(score.score, 35)  # Assuming transcript score and weight calculation leads to this result

    def test_calculate_weighted_score(self):
        """ Test that the weighted score is calculated correctly. """
        score = StudentSubjectScore.objects.create(
            student=self.student, term=self.term, score=70, weighted_score=None, subject=self.subject, grade=self.grade, school=self.school
        )
        score.calculate_weighted_score()
        self.assertEqual(score.weighted_score, 70)  # Assuming term weight is 100

class ReportCardTest(TestCase):
    def setUp(self):
        self.school = School.objects.create(name="Test School")
        self.grade = Grade.objects.create(grade="8", grade_order=1, major_subjects=1, none_major_subjects=1, school=self.school)
        self.term = Term.objects.create(name="Term 1", start_date=timezone.now(), end_date=timezone.now() + timedelta(days=30), weight=100, school=self.school)
        self.subject = Subject.objects.create(grade=self.grade, subject="Math", major_subject=True, pass_mark=50, school=self.school)
        self.student = CustomUser.objects.create(username="student1", grade=self.grade, school=self.school)
        self.score = StudentSubjectScore.objects.create(
            student=self.student, term=self.term, score=75, weighted_score=75, subject=self.subject, grade=self.grade, school=self.school
        )
        self.report = ReportCard.objects.create(
            student=self.student, term=self.term, days_absent=0, days_late=0, attendance_percentage=100, passed=True, year_end_report=False, school=self.school
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
        ReportCard.objects.create(
            student=self.student, term=self.term, days_absent=1, days_late=0, attendance_percentage=95, passed=True, year_end_report=False, school=self.school
        )
        with self.assertRaises(IntegrityError):
            ReportCard.objects.create(
                student=self.student, term=self.term, days_absent=0, days_late=1, attendance_percentage=90, passed=False, year_end_report=False, school=self.school
            )
