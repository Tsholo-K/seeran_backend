# django
from django.test import TestCase
from django.core.exceptions import ValidationError

# models
from .models import Subject, Grade
from schools.models import School


class GradeModelTests(TestCase):

    def setUp(self):
        self.school = School.objects.create(
            name="Test School",
            email="info@testschool.com",
            contact_number="123456789",
            school_type="PRIMARY",
            province="GAUTENG",
            school_district="EKURHULENI NORTH"
        )

    def test_grade_creation(self):
        grade = Grade.objects.create(
            school=self.school,
            grade="8",
            major_subjects=1,
            none_major_subjects=2
        )
        self.assertEqual(grade.grade, "8")
        self.assertEqual(grade.major_subjects, 1)
        self.assertEqual(grade.none_major_subjects, 2)
        self.assertEqual(grade.none_major_subjects, 2)
        self.assertEqual(grade.grade_order, 8)

    def test_invalid_grade_level(self):
        grade = Grade(
            school=self.school,
            grade="13",
            major_subjects=1,
            none_major_subjects=1
        )
        with self.assertRaises(ValidationError):
            grade.save()
        
        grade = Grade(
            school=self.school,
            grade="alpha",
            major_subjects=1,
            none_major_subjects=1
        )
        with self.assertRaises(ValidationError):
            grade.save()

    def test_negative_subject_counts(self):
        grade = Grade(
            school=self.school,
            grade="8",
            major_subjects=-1,
            none_major_subjects=3
        )
        with self.assertRaises(ValidationError):
            grade.save()
        
        grade = Grade(
            school=self.school,
            grade="8",
            major_subjects=3,
            none_major_subjects=-1
        )
        with self.assertRaises(ValidationError):
            grade.save()

    def test_no_subject_counts(self):
        grade = Grade(
            school=self.school,
            grade="8",
            major_subjects=0,
            none_major_subjects=0
        )
        with self.assertRaises(ValidationError):
            grade.save()


class SubjectModelTests(TestCase):

    def setUp(self):
        school = School.objects.create(
            name="test school",
            email="info@testschool.com",
            contact_number="123456789",
            school_type="PRIMARY",
            province="GAUTENG",
            school_district="EKURHULENI NORTH"
        )
        self.grade = Grade.objects.create(
            school=school,
            grade="8",
            major_subjects=1,
            none_major_subjects=2
        )

    def test_subject_creation(self):
        subject = Subject.objects.create(
            grade=self.grade,
            subject="ENGLISH",
            major_subject=True,
            pass_mark=40.0
        )
        self.assertEqual(subject.subject, "ENGLISH")
        self.assertEqual(subject.pass_mark, 40.0)

    def test_invalid_pass_mark(self):
        subject = Subject(
            grade=self.grade,
            subject="MATH",
            major_subject=False,
            pass_mark=105.0
        )
        with self.assertRaises(ValidationError):
            subject.clean()

        subject = Subject(
            grade=self.grade,
            subject="MATH",
            major_subject=False,
            pass_mark=-15.0
        )
        with self.assertRaises(ValidationError):
            subject.clean()
