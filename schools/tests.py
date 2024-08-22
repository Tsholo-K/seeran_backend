# python 
from datetime import timedelta

# djnago
from django.test import TestCase
from django.core.exceptions import ValidationError
from django.utils import timezone

# models
from .models import Term, School


class SchoolModelTest(TestCase):
    def setUp(self):
        """Set up a sample school instance for use in the tests."""
        self.school = School.objects.create(
            name="Test School",
            email="testschool@example.com",
            contact_number="1234567890",
            type="PRIMARY",
            province="GAUTENG",
            district="JHB NORTH"
        )

    def test_school_creation(self):
        """Test that a school instance is created successfully."""
        self.assertEqual(School.objects.count(), 1)
        self.assertEqual(self.school.name, "Test School")
        self.assertEqual(self.school.email, "testschool@example.com")

    def test_contact_number_validation(self):
        """Test that an invalid contact number raises a ValidationError."""
        with self.assertRaises(ValidationError):
            self.school.contact_number = "123ABC"  # Invalid contact number
            self.school.clean()  # Trigger validation

    def test_logo_validation(self):
        """Test that an invalid logo file extension raises a ValidationError."""
        with self.assertRaises(ValidationError):
            self.school.logo = 'path/to/logo.txt'  # Invalid file extension for a logo
            self.school.clean()  # Trigger validation

    def test_default_values(self):
        """Test that default values for 'in_arrears' and 'none_compliant' fields are set correctly."""
        self.assertFalse(self.school.in_arrears)
        self.assertFalse(self.school.none_compliant)

    def test_school_update(self):
        """Test that a school instance can be updated successfully."""
        self.school.name = "Updated School"
        self.school.save()
        self.assertEqual(School.objects.get(pk=self.school.pk).name, "Updated School")

    def test_invalid_email(self):
        """Test that an invalid email address raises a ValidationError."""
        self.school.email = "invalidemail"  # Invalid email format
        with self.assertRaises(ValidationError):
            self.school.full_clean()  # Trigger validation

    def test_school_motto_empty(self):
        """Test that the 'school_motto' field is empty by default."""
        self.assertEqual(self.school.school_motto, None)

    def test_unique_school_id(self):
        """Test that each school instance has a unique 'school_id'."""
        school_2 = School.objects.create(
            name="Another Test School",
            email="another@example.com",
            contact_number="0987654321",
            type="PRIMARY",
            province="GAUTENG",
            district="JHB NORTH"
        )
        self.assertNotEqual(self.school.school_id, school_2.school_id)

    def test_school_field_defaults(self):
        """Test that the default values for 'school_type' and 'province' fields are set correctly."""
        self.assertEqual(self.school.type, "PRIMARY")
        self.assertEqual(self.school.province, "GAUTENG")

    def test_valid_school_district(self):
        """
        Test that a valid school district is accepted.
        """
        valid_district = 'GAUTENG NORTH'
        school = School(
            name="Valid District School",
            email="another@example.com",
            contact_number="0987654321",
            type="PRIMARY",
            province="GAUTENG",
            district=valid_district
        )
        try:
            school.full_clean()  # Calls clean and validates the model
        except ValidationError:
            self.fail(f"Validation error raised for valid school district '{valid_district}'")

    def test_invalid_school_district(self):
        """
        Test that an invalid school district raises a validation error.
        """
        invalid_district = 'INVALID DISTRICT'
        school = School(
            name="Invalid District School",
            email="another@example.com",
            contact_number="0987654321",
            type="PRIMARY",
            province="GAUTENG",
            district=invalid_district
        )
        with self.assertRaises(ValidationError):
            school.full_clean()  # Calls clean and validates the model


class TermModelTest(TestCase):
    def setUp(self):
        """Set up a sample school and term instance for use in the tests."""
        self.school = School.objects.create(
            name="Test School",
            email="testschool@example.com",
            contact_number="1234567890",
            type="PRIMARY",
            province="GAUTENG",
            district="JHB NORTH"
        )
        self.term = Term.objects.create(
            term=1,
            weight=30.00,
            start_date=timezone.now().date(),
            end_date=timezone.now().date() + timedelta(days=60),
            school=self.school
        )

    def test_term_creation(self):
        """Test that a term instance is created successfully."""
        self.assertEqual(Term.objects.count(), 1)
        self.assertEqual(self.term.term, 1)
        self.assertEqual(self.term.weight, 30.00)

    def test_term_start_date_before_end_date(self):
        """Test that a term's start date cannot be after its end date, raising a ValidationError."""
        with self.assertRaises(ValidationError):
            self.term.start_date = timezone.now().date() + timedelta(days=61)
            self.term.end_date = timezone.now().date() + timedelta(days=60)
            self.term.clean()  # Trigger validation

    def test_term_overlapping_dates(self):
        """Test that overlapping term dates raise a ValidationError."""
        overlapping_term = Term(
            term=2,
            weight=20.00,
            start_date=self.term.start_date + timedelta(days=15),
            end_date=self.term.end_date + timedelta(days=15),
            school=self.school
        )
        with self.assertRaises(ValidationError):
            overlapping_term.clean()  # Trigger validation

    def test_term_weight_exceeding_100(self):
        """Test that a term's total weight exceeding 100% raises a ValidationError."""
        term_2 = Term.objects.create(
            term=2,
            weight=60.00,
            start_date=timezone.now().date() + timedelta(days=61),
            end_date=timezone.now().date() + timedelta(days=120),
            school=self.school
        )
        with self.assertRaises(ValidationError):
            term_2.weight = 80.00  # Total weight would exceed 100%
            term_2.clean()  # Trigger validation

    def test_term_school_days_calculation(self):
        """Test that the school days for a term are calculated correctly."""
        start_date = self.term.start_date
        end_date = self.term.end_date

        total_days = 0
        current_date = start_date

        while current_date <= end_date:
            if current_date.weekday() < 5:  # Monday to Friday are considered school days
                total_days += 1
            current_date += timedelta(days=1)

        self.assertEqual(self.term.school_days, total_days)  # Assuming there are 44 weekdays in a 60-day period

    def test_term_update(self):
        """Test that a term instance can be updated successfully."""
        self.term.term = 2
        self.term.save()
        self.assertEqual(Term.objects.get(pk=self.term.pk).term, 2)

    def test_term_unique_constraint(self):
        """Test that a duplicate term for the same school raises a ValidationError."""
        with self.assertRaises(ValidationError):
            duplicate_term = Term(
                term=1,
                weight=25.00,
                start_date=self.term.start_date + timedelta(days=120),
                end_date=self.term.end_date + timedelta(days=180),
                school=self.school
            )
            duplicate_term.clean()  # Trigger validation

    def test_term_id_is_unique(self):
        """Test that each term instance has a unique 'term_id'."""
        term_2 = Term.objects.create(
            term=2,
            weight=50.00,
            start_date=timezone.now().date() + timedelta(days=61),
            end_date=timezone.now().date() + timedelta(days=120),
            school=self.school
        )
        self.assertNotEqual(self.term.term_id, term_2.term_id)


