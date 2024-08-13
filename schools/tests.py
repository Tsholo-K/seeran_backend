# python 
from datetime import date, timedelta

# djnago
from django.test import TestCase
from django.core.exceptions import ValidationError
from django.utils import timezone

# models
from .models import Term, School


class SchoolModelTests(TestCase):
    
    def test_school_creation(self):
        """
        Test that a School object can be created with valid data.
        """
        school = School.objects.create(
            name="test school",
            email="info@testschool.com",
            contact_number="123456789",
            school_type="PRIMARY",
            province="GAUTENG",
            school_district="EKURHULENI NORTH"
        )
        self.assertEqual(school.name, "test school")
        self.assertEqual(school.email, "info@testschool.com")
        self.assertEqual(school.contact_number, "123456789")

    def test_invalid_contact_number(self):
        """
        Test that an invalid contact number raises a ValidationError.
        """
        school = School(
            name="Invalid School",
            email="invalid@testschool.com",
            contact_number="abc123",
            school_type="PRIMARY",
            province="GAUTENG",
            school_district="EKURHULENI NORTH"
        )
        with self.assertRaises(ValidationError):
            school.save()

    def test_invalid_logo_extension(self):
        """
        Test that an invalid logo file extension raises a ValidationError.
        """
        school = School(
            name="Invalid Logo School",
            email="logo@testschool.com",
            contact_number="123456789",
            school_type="PRIMARY",
            province="GAUTENG",
            school_district="EKURHULENI NORTH",
            logo="invalid_logo.bmp"
        )
        with self.assertRaises(ValidationError):
            school.save()

class TermModelTests(TestCase):

    def setUp(self):
        """
        Set up a School instance for use in the Term tests.
        """
        self.school = School.objects.create(
            name="test school",
            email="info@testschool.com",
            contact_number="123456789",
            school_type="PRIMARY",
            province="GAUTENG",
            school_district="EKURHULENI NORTH"
        )

    def test_term_creation(self):
        """
        Test that a Term object can be created with valid data.
        """
        term = Term.objects.create(
            school=self.school,
            term=1,
            weight=25,
            start_date=timezone.now().date(),
            end_date=timezone.now().date() + timedelta(days=30),
        )
        self.assertEqual(term.term, 1)
        self.assertEqual(term.weight, 25)

    def test_term_enddate_before_startdate(self):
        """
        Test that a term with an end date before the start date raises a ValidationError.
        """
        overlapping_term = Term(
            school=self.school,
            term=1,
            weight=25,
            start_date=timezone.now().date() + timedelta(days=30),
            end_date=timezone.now().date(),
        )
        with self.assertRaises(ValidationError):
            overlapping_term.save()

    def test_overlap_terms(self):
        """
        Test that overlapping terms raise a ValidationError.
        """
        Term.objects.create(
            school=self.school,
            term=1,
            weight=25,
            start_date=timezone.now().date(),
            end_date=timezone.now().date() + timedelta(days=30),
        )
        overlapping_term = Term(
            school=self.school,
            term=2,
            weight=25,
            start_date=timezone.now().date() + timedelta(days=29),
            end_date=timezone.now().date() + timedelta(days=59),
        )
        with self.assertRaises(ValidationError):
            overlapping_term.save()

    def test_weight_exceeds_limit(self):
        """
        Test that a term's weight exceeding the total limit raises a ValidationError.
        """
        Term.objects.create(
            school=self.school,
            term=1,
            weight=80,
            start_date=timezone.now().date(),
            end_date=timezone.now().date() + timedelta(days=30),
        )
        term = Term(
            school=self.school,
            term=2,
            weight=21,
            start_date=timezone.now().date() + timedelta(days=31),
            end_date=timezone.now().date() + timedelta(days=60),
        )
        with self.assertRaises(ValidationError):
            term.save()

    def test_calculate_total_school_days(self):
        """
        Test the calculation of total school days excluding weekends.
        """
        term = Term(
            school=self.school,
            term=1,
            weight=25,
            start_date=date(2024, 8, 1),  # Start date: August 1, 2024
            end_date=date(2024, 8, 14)    # End date: August 14, 2024
        )
        
        # Manually calculate the expected number of school days
        start_date = term.start_date
        end_date = term.end_date

        total_days = 0
        current_date = start_date

        while current_date <= end_date:
            if current_date.weekday() < 5:  # Monday to Friday are considered school days
                total_days += 1
            current_date += timedelta(days=1)

        expected_school_days = total_days
        
        # Calculate the actual number of school days using the method
        actual_school_days = term.calculate_total_school_days()
        
        # Assert that the calculated number of school days is as expected
        self.assertEqual(actual_school_days, expected_school_days)
