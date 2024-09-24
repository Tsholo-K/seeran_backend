# django
from django.test import TestCase
from django.core.exceptions import ValidationError

# models
from .models import Subject
from grades.models import Grade
from schools.models import School


class SubjectModelTestCase(TestCase):
    def setUp(self):
        """
        Set up the environment for each test. 

        - Creates a test `School` instance as subjects are linked to a school via grades.
        - Creates a `Grade` instance linked to the school.
        - Prepares a valid subject data dictionary that can be reused across tests.
        """
        # Create a School instance (required because a Grade must be associated with a School)
        self.school = School.objects.create(
            name='Test School',
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

        # Create a Grade instance linked to the School
        self.grade = Grade.objects.create(
            major_subjects=1, 
            none_major_subjects=2,
            grade='10', 
            school=self.school
        )

        # Set up a valid subject data dictionary for reuse in different tests
        self.subject_data = {
            'subject': 'MATHEMATICS',
            'major_subject': True,
            'pass_mark': 50.00,
            'student_count': 30,
            'teacher_count': 2,
            'classroom_count': 1,
            'grade': self.grade
        }

    def test_create_valid_subject(self):
        """
        Test creating a valid `Subject` instance.

        - Ensures that a subject with valid data is successfully created.
        - Asserts that the subject's data matches the expected values.
        """
        subject = Subject.objects.create(**self.subject_data)
        self.assertEqual(subject.subject, 'MATHEMATICS')
        self.assertEqual(subject.pass_mark, 50.00)
        self.assertEqual(subject.grade, self.grade)

    def test_create_invalid_subject(self):
        """
        Test that attempting to create a subject with an invalid subject choice raises a `ValidationError`.

        - Modifies the valid data to include an invalid subject choice.
        - Asserts that a `ValidationError` is raised with the appropriate error message.
        """
        subject_data = self.subject_data.copy()
        subject_data['subject'] = 'invalid-subject'  # Use an invalid subject choice

        subject = Subject(**subject_data)  # Create subject instance but don't save

        # Expecting ValidationError when saving due to invalid subject choice
        with self.assertRaises(ValidationError) as e:
            subject.save()  # Attempt to save the invalid subject

        # Extract and clean up the exception message
        error_message = str(e.exception).strip("[]'\"")
        self.assertIn(
            'Could not process your request, the specified school subject is invalid. Please choose a valid subject from the provided options.',
            error_message
        )

    def test_create_subject_without_grade(self):
        """
        Test that creating a subject without an associated grade raises a `ValidationError`.

        - Modifies the valid data to remove the grade.
        - Asserts that a `ValidationError` is raised with the correct error message.
        """
        subject_data = self.subject_data.copy()
        subject_data['grade'] = None  # Remove the grade

        subject = Subject(**subject_data)  # Create subject instance

        # Expecting ValidationError when saving due to missing grade
        with self.assertRaises(ValidationError) as e:
            subject.save()  # Attempt to save without a grade

        # Extract and clean up the exception message
        error_message = str(e.exception).strip("[]'\"")
        self.assertIn(
            'Could not process your request, a subject needs to be associated with a school grade. Please provide a grade before saving the subject.',
            error_message
        )

    def test_duplicate_subject(self):
        """
        Test that creating a duplicate subject for the same grade raises a `ValidationError`.

        - First, create a subject using the valid data.
        - Attempt to create a duplicate subject with the same name and grade, and assert that a `ValidationError` is raised.
        """
        # Create the initial subject
        Subject.objects.create(**self.subject_data)

        # Expecting ValidationError when trying to create a duplicate subject
        with self.assertRaises(ValidationError) as e:
            Subject.objects.create(**self.subject_data)  # Duplicate creation

        # Extract and clean up the exception message
        error_message = str(e.exception).strip("[]'\"")
        self.assertIn(
            'Could not process your request, the subject "MATHEMATICS" already exists for the selected grade. Duplicate subjects are not permitted. Please choose a different subject for this grade or check existing subjects.',
            error_message
        )

    def test_invalid_pass_mark(self):
        """
        Test that an invalid pass mark (outside the 0-100 range) raises a `ValidationError`.

        - First, test with a pass mark greater than 100.
        - Then, test with a negative pass mark.
        - Assert that a `ValidationError` is raised with the appropriate message in both cases.
        """
        subject_data = self.subject_data.copy()

        # Test with pass mark greater than 100
        subject_data['pass_mark'] = 150.00
        subject_a = Subject(**subject_data)  # Create subject instance

        # Expecting ValidationError when validating the pass mark
        with self.assertRaises(ValidationError) as e:
            subject_a.clean()  # Call clean method to validate pass mark

        error_message = str(e.exception).strip("[]'\"")
        self.assertIn(
            'Could not process your request, the subject\'s pass mark must be between 0.00 and 100.00.',
            error_message
        )

        # Test with a negative pass mark
        subject_data['pass_mark'] = -50.00
        subject_b = Subject(**subject_data)  # Create subject instance

        # Expecting ValidationError when validating the negative pass mark
        with self.assertRaises(ValidationError) as e:
            subject_b.clean()  # Call clean method to validate pass mark

        error_message = str(e.exception).strip("[]'\"")
        self.assertIn(
            'Could not process your request, the subject\'s pass mark must be between 0.00 and 100.00.',
            error_message
        )

    def test_string_representation(self):
        """
        Test the string representation of the subject model.

        - Creates a valid subject and asserts that the string representation matches the subject's name.
        """
        subject = Subject.objects.create(**self.subject_data)
        self.assertEqual(str(subject), "MATHEMATICS")  # The string representation should be the subject's name

