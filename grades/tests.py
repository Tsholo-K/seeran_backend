# django
from django.test import TestCase
from django.core.exceptions import ValidationError

# models
from .models import Grade
from schools.models import School


class GradeModelTestCase(TestCase):
    def setUp(self):
        """Set up test data for Grade model tests."""
        """
        Set up test data for Grade model tests.

        - Creates a test `School` instance as grades are linked to a school.
        - Prepares a valid grade data dictionary that can be reused across tests.
        """
        # Create primary school instance for testing
        self.primary_school = School.objects.create(
            name='Test School 1',
            email_address='primaryschool@example.com',
            contact_number='0123456789',
            student_count=130,
            teacher_count=24,
            admin_count=19,
            in_arrears=False,
            none_compliant=False,
            type='PRIMARY',
            province='GAUTENG',
            district='GAUTENG WEST',
            grading_system='A-F Grading',
            library_details='Well-stocked library',
            laboratory_details='State-of-the-art labs',
            sports_facilities='Football field, Basketball court',
            operating_hours='07:45 - 14:00',
            location='456 INNER St',
            website='https://primaryschool.com',
        )

        # Create secondary school instance for testing
        self.secondary_school = School.objects.create(
            name='Test School 2',
            email_address='secondaryschool@example.com',
            contact_number='1011121314',
            student_count=130,
            teacher_count=24,
            admin_count=19,
            in_arrears=False,
            none_compliant=False,
            type='SECONDARY',
            province='GAUTENG',
            district='GAUTENG EAST',
            grading_system='A-F Grading',
            library_details='Well-stocked library',
            laboratory_details='State-of-the-art labs',
            sports_facilities='Football field, Basketball court',
            operating_hours='07:45 - 14:00',
            location='123 OUTER St',
            website='https://secondaryschool.com',
        )

        # Default data for creating a Grade
        self.grade_data = {
            'major_subjects': 1, 
            'none_major_subjects': 2,
            'grade': '10', 
            'school': self.secondary_school
        }
    
    def test_create_valid_grade(self):
        """Test creating a valid grade."""
        grade = Grade.objects.create(**self.grade_data)  # Create a new Grade instance
        self.assertEqual(grade.grade, '10')  # Check if the grade is set correctly
        self.assertEqual(grade.school, self.secondary_school)  # Check if the school is set correctly
        self.assertEqual(grade.grade_order, 12)  # Ensure the correct order based on the grading system

    def test_invalid_subjects(self):
        """Test validation for negative major and non-major subjects."""
        grade_data = self.grade_data.copy()  # Create a copy of the default grade data

        # Test case for negative major subjects
        grade_data['major_subjects'] = -1  # Set major subjects to an invalid negative number
        grade_a = Grade(**grade_data)  # Create a Grade instance

        with self.assertRaises(ValidationError) as e:  # Expect a validation error
            grade_a.clean()  # Attempt to validate the Grade instance

        # Access the actual message from the exception
        error_message = str(e.exception).strip("[]'\"")
        self.assertIn(
            'Could not process your request, major subjects and non-major subjects must be non-negative integers. Please correct the values and try again.',
            error_message  # Verify the correct error message is raised
        )

        # Test case for negative non-major subjects
        grade_data['major_subjects'] = 0  # Set major subjects to 0 (valid)
        grade_data['none_major_subjects'] = -1  # Set non-major subjects to an invalid negative number
        grade_b = Grade(**grade_data)  # Create another Grade instance

        with self.assertRaises(ValidationError) as e:  # Expect a validation error
            grade_b.clean()  # Attempt to validate the Grade instance

        # Access the actual message from the exception
        error_message = str(e.exception).strip("[]'\"")
        self.assertIn(
            'Could not process your request, major subjects and non-major subjects must be non-negative integers. Please correct the values and try again.',
            error_message  # Verify the correct error message is raised
        )

    def test_at_least_one_subject_required(self):
        """Test validation that at least one subject must be specified."""
        grade_data = self.grade_data.copy()  # Create a copy of the default grade data

        grade_data['major_subjects'] = 0  # Set major subjects to 0
        grade_data['none_major_subjects'] = 0  # Set non-major subjects to 0
        grade = Grade(**grade_data)  # Create a Grade instance

        with self.assertRaises(ValidationError) as e:  # Expect a validation error
            grade.clean()  # Attempt to validate the Grade instance

        # Access the actual message from the exception
        error_message = str(e.exception).strip("[]'\"")
        self.assertIn(
            'Could not process your request, you must specify at least one major or non-major subject for the grading criteria. Please correct the values and try again.',
            error_message  # Verify the correct error message is raised
        )

    def test_primary_school_grade_limit(self):
        """Test validation for grade limit in primary schools."""
        grade_data = self.grade_data.copy()  # Create a copy of the default grade data

        grade_data['grade'] = 10  # Set grade to 10 (invalid for primary school)
        grade_data['school'] = self.primary_school  # Set school to primary school
        grade_a = Grade(**grade_data)  # Create a Grade instance

        with self.assertRaises(ValidationError) as e:  # Expect a validation error
            grade_a.clean()  # Attempt to validate the Grade instance

        # Access the actual message from the exception
        error_message = str(e.exception).strip("[]'\"")
        self.assertIn(
            'Could not process your request, primary schools cannot assign grades higher than Grade 7. Please choose a valid grade for primary school and try again.',
            error_message  # Verify the correct error message is raised
        )

        # Test case for secondary school
        grade_data['grade'] = 6  # Set grade to 6 (invalid for secondary school)
        grade_data['school'] = self.secondary_school  # Set school to secondary school
        grade_b = Grade(**grade_data)  # Create another Grade instance

        with self.assertRaises(ValidationError) as e:  # Expect a validation error
            grade_b.clean()  # Attempt to validate the Grade instance

        # Access the actual message from the exception
        error_message = str(e.exception).strip("[]'\"")
        self.assertIn(
            'Could not process your request, secondary schools must assign grades higher than Grade 7. Please update the grade accordingly.',
            error_message  # Verify the correct error message is raised
        )

        # Test case for non-numeric grade
        grade_data['grade'] = 'R'  # Set grade to a non-numeric value
        grade_c = Grade(**grade_data)  # Create another Grade instance

        with self.assertRaises(ValidationError) as e:  # Expect a validation error
            grade_c.clean()  # Attempt to validate the Grade instance

        # Access the actual message from the exception
        error_message = str(e.exception).strip("[]'\"")
        self.assertIn(
            'Could not process your request, secondary and tertiary schools cannot assign non-numeric grades such as "R", "00", or "000". Please select a valid numeric grade.',
            error_message  # Verify the correct error message is raised
        )

    def test_duplicate_grades(self):
        """Test that duplicate grades for the same school raise a ValidationError."""
        Grade.objects.create(**self.grade_data)  # Create the first Grade instance
        with self.assertRaises(ValidationError) as e:  # Expect a validation error on duplicate
            Grade.objects.create(**self.grade_data)  # Attempt to create a duplicate Grade instance

        # Access the actual message from the exception
        error_message = str(e.exception).strip("[]'\"")
        self.assertIn(
            'Could not process your request, the provided grade already exists for your school, duplicate grades are not permitted. Please choose a different grade.',
            error_message  # Verify the correct error message is raised
        )

    def test_save_without_school(self):
        """Test saving a grade without an associated school raises a ValidationError."""
        grade_data = self.grade_data.copy()  # Create a copy of the default grade data

        grade_data['school'] = None  # Set school to None (invalid)
        grade = Grade(**grade_data)  # Create a Grade instance

        with self.assertRaises(ValidationError) as e:  # Expect a validation error
            grade.clean()  # Attempt to validate the Grade instance

        # Access the actual message from the exception
        error_message = str(e.exception).strip("[]'\"")
        self.assertIn(
            'Could not process your request, a grade needs to be associated with a school. Please provide a school and try again.',
            error_message  # Verify the correct error message is raised
        )

    def test_grade_order_is_set_on_creation(self):
        """Test that grade_order is set correctly based on SCHOOL_GRADES_CHOICES."""
        grade_data = self.grade_data.copy()  # Create a copy of the default grade data

        grade = Grade.objects.create(**grade_data)  # Create a new Grade instance
        self.assertEqual(grade.grade_order, 12)  # Check that the grade_order is correctly set

    def test_string_representation(self):
        """Test the string representation of the grade."""
        grade_data = self.grade_data.copy()  # Create a copy of the default grade data

        grade = Grade.objects.create(**grade_data)  # Create a Grade instance
        self.assertEqual(str(grade), "Grade 10 (Order: 12)")  # Verify the string representation
