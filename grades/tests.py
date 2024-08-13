# django
from django.test import TestCase
from django.core.exceptions import ValidationError


# models
from schools.models import School
from grades.models import Grade, Subject


SCHOOL_GRADES_CHOICES = [
    ('000', 'Grade 000'), 
    ('00', 'Grade 00'), 
    ('R', 'Grade R'), 
    ('1', 'Grade 1'), 
    ('2', 'Grade 2'), 
    ('3', 'Grade 3'), 
    ('4', 'Grade 4'), 
    ('5', 'Grade 5'), 
    ('6', 'Grade 6'), 
    ('7', 'Grade 7'), 
    ('8', 'Grade 8'), 
    ('9', 'Grade 9'), 
    ('10', 'Grade 10'), 
    ('11', 'Grade 11'), 
    ('12', 'Grade 12')
]


class GradeModelTest(TestCase):
    def setUp(self):
        """Set up a sample school instance for use in the tests."""
        self.school = School.objects.create(
            name="Test School",
            email="testschool@example.com",
            contact_number="1234567890",
            school_type="PRIMARY",
            province="GAUTENG",
            school_district="District 1"
        )
        self.grade = Grade.objects.create(
            grade='8',
            major_subjects=1,
            none_major_subjects=2,
            school=self.school
        )

    def test_grade_creation(self):
        """Test that a grade instance is created successfully."""
        self.assertEqual(Grade.objects.count(), 1)
        self.assertEqual(self.grade.grade, '8')
        self.assertEqual(self.grade.major_subjects, 1)
        self.assertEqual(self.grade.none_major_subjects, 2)

    def test_grade_order(self):
        """Test that the grade_order is set correctly based on the grade."""
        self.assertEqual(self.grade.grade_order, [choice[0] for choice in SCHOOL_GRADES_CHOICES].index('8'))

    def test_invalid_grade_value(self):
        """Test that an invalid grade value raises a ValidationError."""
        with self.assertRaises(ValidationError):
            invalid_grade = Grade(
                grade='INVALID',
                major_subjects=2,
                none_major_subjects=1,
                school=self.school
            )
            invalid_grade.save()  # This should raise ValidationError

    def test_negative_subjects(self):
        """Test that negative values for major_subjects and none_major_subjects raise a ValidationError."""
        with self.assertRaises(ValidationError):
            invalid_grade = Grade(
                grade='8',
                major_subjects=-1,
                none_major_subjects=1,
                school=self.school
            )
            invalid_grade.clean()  # This should raise ValidationError

    def test_no_subjects(self):
        """Test that having zero major and non-major subjects raises a ValidationError."""
        with self.assertRaises(ValidationError):
            invalid_grade = Grade(
                grade='8',
                major_subjects=0,
                none_major_subjects=0,
                school=self.school
            )
            invalid_grade.clean()  # This should raise ValidationError

    def test_unique_grade_within_school(self):
        """Test that duplicate grades within the same school raise a ValidationError."""
        with self.assertRaises(ValidationError):
            duplicate_grade = Grade(
                grade='8',
                major_subjects=1,
                none_major_subjects=2,
                school=self.school
            )
            duplicate_grade.save()  # This should raise ValidationError


class SubjectModelTest(TestCase):
    def setUp(self):
        """Set up a sample school and grade instance for use in the tests."""
        self.school = School.objects.create(
            name="Test School",
            email="testschool@example.com",
            contact_number="1234567890",
            school_type="PRIMARY",
            province="GAUTENG",
            school_district="District 1"
        )
        self.grade = Grade.objects.create(
            grade='8',
            major_subjects=2,
            none_major_subjects=1,
            school=self.school
        )
        self.subject = Subject.objects.create(
            grade=self.grade,
            subject='ENGLISH',
            major_subject=True,
            pass_mark=50.00
        )

    def test_subject_creation(self):
        """Test that a subject instance is created successfully."""
        self.assertEqual(Subject.objects.count(), 1)
        self.assertEqual(self.subject.subject, 'ENGLISH')
        self.assertTrue(self.subject.major_subject)
        self.assertEqual(self.subject.pass_mark, 50.00)

    def test_pass_mark_validation(self):
        """Test that an invalid pass mark raises a ValidationError."""
        with self.assertRaises(ValidationError):
            invalid_subject = Subject(
                grade=self.grade,
                subject='ENGLISH',
                major_subject=True,
                pass_mark=105.00  # Pass mark exceeds 100
            )
            invalid_subject.clean()  # This should raise ValidationError

    def test_unique_subject_within_grade(self):
        """Test that duplicate subjects within the same grade raise a ValidationError."""
        with self.assertRaises(ValidationError):
            duplicate_subject = Subject(
                grade=self.grade,
                subject='ENGLISH',
                major_subject=False,
                pass_mark=40.00
            )
            duplicate_subject.save()  # This should raise ValidationError

    def test_subject_update(self):
        """Test that a subject instance can be updated successfully."""
        self.subject.subject = 'MATHEMATICS'
        self.subject.save()
        self.assertEqual(Subject.objects.get(pk=self.subject.pk).subject, 'MATHEMATICS')

    def test_subject_id_is_unique(self):
        """Test that each subject instance has a unique 'subject_id'."""
        subject_2 = Subject.objects.create(
            grade=self.grade,
            subject='MATHEMATICS',
            major_subject=True,
            pass_mark=60.00
        )
        self.assertNotEqual(self.subject.subject_id, subject_2.subject_id)
