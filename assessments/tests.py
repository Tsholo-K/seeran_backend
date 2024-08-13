# python 
from datetime import timedelta

# django
from django.test import TestCase
from django.core.exceptions import ValidationError
from django.utils import timezone


# models
from .models import Assessment, Transcript
from users.models import CustomUser
from schools.models import Term, School
from grades.models import Subject, Grade


class AssessmentModelTests(TestCase):

    def setUp(self):
        self.school = School.objects.create(
            name="test school",
            email="info@testschool.com",
            contact_number="123456789",
            school_type="PRIMARY",
            province="GAUTENG",
            school_district="EKURHULENI NORTH"
        )
        self.grade = Grade.objects.create(
            school=self.school,
            grade="8",
            major_subjects=1,
            none_major_subjects=2
        )
        self.term = Term.objects.create(
            school=self.school,
            term=1,
            weight=25,
            start_date=timezone.now().date(),
            end_date=timezone.now().date() + timedelta(days=30)
        )
        self.subject = Subject.objects.create(
            grade=self.grade,
            subject="ENGLISH",
            major_subject=True,
            pass_mark=60.0
        )
        self.assessment = Assessment.objects.create(
            term=self.term,
            title="Midterm Exam",
            subject=self.subject,
            total=100.0,
            due_date=timezone.now().date() + timedelta(days=7),
            collected=False,
            released=False
        )

    def test_assessment_creation(self):
        self.assertEqual(self.assessment.title, "Midterm Exam")
        self.assertEqual(self.assessment.total, 100.0)

    def test_invalid_assessment_date(self):
        assessment = Assessment(
            term=self.term,
            titile="Test Assessment",
            subject=self.subject,
            total=100.0,
            assessment_date=timezone.now().date() - timedelta(days=1),
            collected=False,
            released=False
        )
        with self.assertRaises(ValidationError):
            assessment.clean()

class TranscriptModelTests(TestCase):

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
            weight=25.0,
            start_date=timezone.now().date(),
            end_date=timezone.now().date() + timedelta(days=30),
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
        self.assessment = Assessment.objects.create(
            term=self.term,
            title="Midterm Exam",
            subject=self.subject,
            total=100.0,
            due_date=timezone.now().date(),
            collected=False,
            released=False
        )
        self.transcript = Transcript.objects.create(
            student=self.student,
            assessment=self.assessment,
            score=80.0,
            moderated_score=85.0
        )

    def test_transcript_creation(self):
        self.assertEqual(self.transcript.score, 80.0)
        self.assertEqual(self.transcript.moderated_score, 85.0)

    def test_invalid_scores(self):
        transcript = Transcript(
            student=self.student,
            assessment=self.assessment,
            score=110.0,
            moderated_score=120.0
        )
        with self.assertRaises(ValidationError):
            transcript.clean()
