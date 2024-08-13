# python 
from datetime import timedelta

# python
from django.test import TestCase
from django.core.exceptions import ValidationError
from django.utils import timezone

# models
from users.models import CustomUser
from grades.models import Subject, Grade
from schools.models import School, Term
from .models import ReportCard, StudentSubjectScore

class StudentSubjectScoreModelTests(TestCase):

    def setUp(self):
        self.school = School.objects.create(
            name="test school",
            email="info@testschool.com",
            contact_number="123456789",
            school_type="PRIMARY",
            province="GAUTENG",
            school_district="EKURHULENI NORTH"
        )
        self.student = CustomUser.objects.create(
            name="peter", 
            surname='parker', 
            email='example@example.com', 
            role='STUDENT', 
            passport_number='548672159', 
            school=self.school
        )
        self.term = Term.objects.create(
            school=self.school,
            term=1,
            weight=25,
            start_date=timezone.now().date(),
            end_date=timezone.now().date() + timedelta(days=30)
        )
        self.grade = Grade.objects.create(
            school=self.school,
            grade="8",
            major_subjects=1,
            none_major_subjects=2
        )
        self.subject = Subject.objects.create(
            grade=self.grade,
            subject="ENGLISH",
            major_subject=True,
            pass_mark=40.0
        )


    def test_student_subject_score_creation(self):
        score = StudentSubjectScore.objects.create(
            student=self.student,
            term=self.term,
            subject=self.subject,
            score=75.0,
            weighted_score=18.75
        )
        self.assertEqual(score.score, 75.0)
        self.assertEqual(score.weighted_score, 18.75)

    def test_invalid_scores(self):
        score = StudentSubjectScore(
            student=self.student,
            term=self.term,
            subject=self.subject,
            score=105.0,
            weighted_score=110.0
        )
        with self.assertRaises(ValidationError):
            score.save()

class ReportCardModelTests(TestCase):

    def setUp(self):
        self.school = School.objects.create(
            name="test school",
            email="info@testschool.com",
            contact_number="123456789",
            school_type="PRIMARY",
            province="GAUTENG",
            school_district="EKURHULENI NORTH"
        )
        self.student = CustomUser.objects.create(
            name="peter", 
            surname='parker', 
            email='example@example.com', 
            role='STUDENT', 
            passport_number='548672159', 
            school=self.school
        )
        self.term = Term.objects.create(
            school=self.school,
            term=1,
            weight=25,
            start_date=timezone.now().date(),
            end_date=timezone.now().date() + timedelta(days=30)
        )
        self.report_card = ReportCard.objects.create(
            student=self.student,
            term=self.term,
            school=self.school,
            attendance_percentage=95.0,
            passed=True
        )

    def test_report_card_creation(self):
        self.assertEqual(self.report_card.student, self.student)
        self.assertEqual(self.report_card.term, self.term)
        self.assertEqual(self.report_card.attendance_percentage, 95.0)

    def test_invalid_attendance_percentage(self):
        report_card = ReportCard(
            student=self.student,
            term=self.term,
            school=self.school,
            attendance_percentage=105.0
        )
        with self.assertRaises(ValidationError):
            report_card.save()

        report_card = ReportCard(
            student=self.student,
            term=self.term,
            school=self.school,
            attendance_percentage=-15.0
        )
        with self.assertRaises(ValidationError):
            report_card.save()
