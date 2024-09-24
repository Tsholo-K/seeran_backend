# python
from datetime import date
from decimal import Decimal

# django
from django.test import TestCase
from django.core.exceptions import ValidationError
from django.test import TestCase

# models
from .models import Term
from grades.models import Grade
from schools.models import School


class TermModelTestCase(TestCase):

    def setUp(self):
        """
        Set up the test data including a School and Grade instance, which are needed for creating Terms.
        """
        # Create a School instance for testing
        self.school = School.objects.create(
            name='Test School',
            email_address='school@example.com',
            contact_number='12345678910',
            student_count=200,
            teacher_count=20,
            admin_count=10,
            in_arrears=False,
            none_compliant=False,
            type='SECONDARY',
            province='GAUTENG',
            district='GAUTENG EAST',
            grading_system='A-F Grading',
            location='123 Test St',
            website='https://testschool.com'
        )

        # Create a Grade instance for testing
        self.grade = Grade.objects.create(
            major_subjects=3,
            none_major_subjects=2,
            grade='10',
            school=self.school
        )

        # Default data for creating a valid term
        self.term_data = {
            'term': 'Term 1',
            'weight': Decimal('30.00'),
            'start_date': date(2024, 1, 15),
            'end_date': date(2024, 4, 10),
            'grade': self.grade,
            'school': self.school
        }

    def test_create_valid_term(self):
        """
        Test creating a valid term with all required fields.
        """
        term = Term.objects.create(**self.term_data)
        self.assertEqual(term.term, 'Term 1')
        self.assertEqual(term.weight, Decimal('30.00'))
        self.assertEqual(term.grade, self.grade)

    def test_term_dates_validation(self):
        """
        Test that a term with a start date after the end date raises a ValidationError.
        """
        term_data = self.term_data.copy()

        term_data['start_date'] = date(2024, 4, 15)  # Start date after end date
        term = Term(**term_data)

        with self.assertRaises(ValidationError) as e:
            term.clean()  # Manually trigger the validation

    def test_overlapping_term_dates(self):
        """
        Test that overlapping terms within the same grade and school raise a ValidationError.
        """
        # Create the first valid term
        Term.objects.create(**self.term_data)

        # Attempt to create another term that overlaps with the first one
        overlapping_term_data = self.term_data.copy()
        overlapping_term_data['term'] = 'Term 2'  # Different term, same dates
        overlapping_term_data['start_date'] = date(2024, 4, 1)  # Overlaps with existing term
        overlapping_term = Term(**overlapping_term_data)

        with self.assertRaises(ValidationError) as e:
            overlapping_term.clean()  # Trigger validation

    def test_term_weight_validation(self):
        """
        Test that creating a term that causes the total weight to exceed 100% raises a ValidationError.
        """
        # Create the first valid term
        Term.objects.create(**self.term_data)

        # Attempt to create a second term with weight that exceeds the total of 100%
        exceeding_weight_data = self.term_data.copy()
        exceeding_weight_data['term'] = 'Term 2'
        exceeding_weight_data['weight'] = Decimal('80.00')  # Total weight will exceed 100%

        with self.assertRaises(ValidationError) as e:
            term = Term(**exceeding_weight_data)
            term.clean()  # Trigger validation

    def test_school_days_calculation(self):
        """
        Test that the total school days are automatically calculated if not provided.
        """
        term_data = self.term_data.copy()
        term_data['school_days'] = None # Remove school_days to test auto-calculation

        term = Term.objects.create(**term_data)

        # Assuming school days are Monday to Friday
        # This period (2024-01-15 to 2024-04-10) has 61 weekdays (actual school days)
        self.assertEqual(term.school_days, 63)  # School days should be auto-calculated

    def test_unique_term_constraint(self):
        """
        Test that creating a term with the same identifier for the same grade and school raises a ValidationError.
        """
        # Create the first term
        Term.objects.create(**self.term_data)

        # Attempt to create a duplicate term
        with self.assertRaises(ValidationError) as e:
            Term.objects.create(**self.term_data)

    def test_invalid_term_identifier(self):
        """
        Test that a term with an invalid identifier (too long) raises a ValidationError.
        """
        invalid_term_data = self.term_data.copy()

        invalid_term_data['term'] = 'ThisTermIdentifierIsWayTooLongg'  # More than 16 characters
        term = Term(**invalid_term_data)

        with self.assertRaises(ValidationError) as e:
            term.clean()

    def test_string_representation(self):
        """
        Test the string representation of the term model.
        """
        term = Term.objects.create(**self.term_data)
        self.assertEqual(str(term), 'Term Term 1')
