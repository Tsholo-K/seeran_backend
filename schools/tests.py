# python
import uuid

# django
from django.test import TestCase
from django.core.exceptions import ValidationError

# models
from .models import School


class SchoolModelTest(TestCase):

    def setUp(self):
        """
        Setup data for testing.
        """
        self.school_data = {
            'name': 'Test School',
            'email_address': 'testschool@example.com',
            'contact_number': '0123456789',
            'student_count': 100,
            'teacher_count': 20,
            'admin_count': 10,
            'in_arrears': False,
            'none_compliant': False,
            'type': 'PRIMARY',
            'province': 'GAUTENG',
            'district': 'GAUTENG NORTH',
            'grading_system': 'A-F Grading',
            'library_details': 'Well-stocked library',
            'laboratory_details': 'State-of-the-art labs',
            'sports_facilities': 'Football field, Basketball court',
            'operating_hours': '08:00 - 15:00',
            'location': '123 Main St',
            'website': 'https://testschool.com',
        }

    def test_clean_method(self):
        """
        Test that the clean method validates contact number, email, and logo.
        """
        school = School(**self.school_data)
        try:
            school.clean()  # Should pass without error
        except ValidationError:
            self

    def test_create_valid_school(self):
        """
        Test that a valid school can be created.
        """
        school = School.objects.create(**self.school_data)
        self.assertEqual(School.objects.count(), 1)
        self.assertEqual(school.name, 'Test School')
        self.assertEqual(school.email_address, 'testschool@example.com')
        self.assertEqual(school.contact_number, '0123456789')

    def test_unique_email(self):
        """
        Test that email must be unique.
        """
        School.objects.create(**self.school_data)
        with self.assertRaises(ValidationError) as e:
            School.objects.create(
                name= 'Test School 2',
                email_address= 'testschool@example.com', # email address is the only field not modified
                contact_number= '0123456782',
                student_count= 130,
                teacher_count= 24,
                admin_count= 19,
                in_arrears= False,
                none_compliant= False,
                type= 'SECONDARY',
                province= 'GAUTENG',
                district= 'GAUTENG EAST',
                grading_system= 'A-F Grading',
                library_details= 'Well-stocked library',
                laboratory_details= 'State-of-the-art labs',
                sports_facilities= 'Football field, Basketball court',
                operating_hours= '07:45 - 14:00',
                location= '456 OUTER St',
                website= 'https://testschool2.com',
            ) # Will raise validation error due to uniqueness error in the email_address field

        # Access the actual message from the exception and clean it
        error_message = str(e.exception).strip("[]'\"")

        # Ensure the correct message is in the exception
        self.assertIn(
            'The email address provided is already in use by another school. Please use a different email address or contact support if you believe this is an error.',
            error_message
        )

    def test_unique_contact_number(self):
        """
        Test that contact number must be unique.
        """
        School.objects.create(**self.school_data)
        with self.assertRaises(ValidationError) as e:
            School.objects.create(
                name= 'Test School 2',
                email_address= 'testschool2@example.com',
                contact_number= '0123456789', # contact number is the only field not modified
                student_count= 130,
                teacher_count= 24,
                admin_count= 19,
                in_arrears= False,
                none_compliant= False,
                type= 'SECONDARY',
                province= 'GAUTENG',
                district= 'GAUTENG WEST',
                grading_system= 'A-F Grading',
                library_details= 'Well-stocked library',
                laboratory_details= 'State-of-the-art labs',
                sports_facilities= 'Football field, Basketball court',
                operating_hours= '07:45 - 14:00',
                location= '456 OUTER St',
                website= 'https://testschool2.com',
            ) # Will raise validation error due to uniqueness error in the contact_number field

        # Access the actual message from the exception and clean it
        error_message = str(e.exception).strip("[]'\"")

        # Ensure the correct message is in the exception
        self.assertIn(
            'The contact number provided is already in use by another school. Please use a unique contact number or verify if the correct number has been entered.',
            error_message
        )

    def test_contact_number_digits_only(self):
        """
        Test that contact number contains only digits.
        """
        invalid_school_data = self.school_data.copy()
        invalid_school_data['contact_number'] = '01234abcd'
        school = School(**invalid_school_data)

        with self.assertRaises(ValidationError) as e:
            school.clean()  # Should raise a validation error due to invalid contact number

        # Access the actual message from the exception and clean it
        error_message = str(e.exception).strip("[]'\"")

        # Ensure the correct message is in the exception
        self.assertIn(
            'The contact number provided contains non-numeric characters. Please enter a numeric only contact number (e.g., 0123456789).',
            error_message
        )

    def test_contact_number_length(self):
        """
        Test that contact number length is between 10 and 15 digits.
        """
        invalid_school_data = self.school_data.copy()
        
        # Too short contact number
        invalid_school_data['contact_number'] = '123456'
        school = School(**invalid_school_data)
        with self.assertRaises(ValidationError) as e:
            school.clean()  # Should raise a validation error

        # Access the actual message from the exception and clean it
        error_message = str(e.exception).strip("[]'\"")

        # Ensure the correct message is in the exception
        self.assertIn(
            'The contact number must be between 10 and 15 digits long. Please provide a valid contact number within this range.',
            error_message
        )

        # Too long contact number
        invalid_school_data['contact_number'] = '12345678901234567890'
        school = School(**invalid_school_data)
        with self.assertRaises(ValidationError) as e:
            school.clean()  # Should raise a validation error

        # Access the actual message from the exception and clean it
        error_message = str(e.exception).strip("[]'\"")

        # Ensure the correct message is in the exception
        self.assertIn(
            'The contact number must be between 10 and 15 digits long. Please provide a valid contact number within this range.',
            error_message
        )

    def test_valid_email(self):
        """
        Test that a valid email passes validation and invalid ones raise errors.
        """
        invalid_school_data = self.school_data.copy()
        invalid_school_data['email_address'] = 'invalid_email'
        school = School(**invalid_school_data)
        with self.assertRaises(ValidationError) as e:
            school.clean()  # Will raise a validation error due to invalid email format

        # Access the actual message from the exception and clean it
        error_message = str(e.exception).strip("[]'\"")

        # Ensure the correct message is in the exception
        self.assertIn(
            'The email address provided is not valid. Please provide a valid email address in the format name@domain.com. If you are unsure, check with your email provider.',
            error_message
        )

    def test_long_email_address(self):
        """Test that an email address longer than 254 characters raises a ValidationError."""
        long_email_school_data = self.school_data.copy()
        long_email_school_data['email_address'] = 'a' * 255 + '@example.com'  # Creating a long email (255 characters)
        school = School(**long_email_school_data)
        with self.assertRaises(ValidationError) as e:
            school.clean()  # Will raise a validation error due to invalid email length

        # Access the actual message from the exception and clean it
        error_message = str(e.exception).strip("[]'\"")

        # Ensure the correct message is in the exception
        self.assertIn(
            'The email address exceeds the maximum allowed length of 254 characters. Please provide a shorter email address or use an alias.',
            error_message
        )

    def test_invalid_school_type(self):
        """Test that an invalid school type raises a ValidationError."""
        invalid_school_data = self.school_data.copy()
        invalid_school_data['type'] = 'INVALID_TYPE'
        school = School(**invalid_school_data)

        with self.assertRaises(ValidationError) as e:
            school.clean()

        # Access the actual message from the exception and clean it
        error_message = str(e.exception).strip("[]'\"")

        # Ensure the correct message is in the exception
        self.assertIn(
            'The selected school type is invalid. Please choose a valid option from Primary, Secondary, Hybrid, or Tertiary.',
            error_message
        )

    def test_invalid_province(self):
        """Test that an invalid province raises a ValidationError."""
        invalid_school_data = self.school_data.copy()
        invalid_school_data['province'] = 'INVALID_PROVINCE'
        school = School(**invalid_school_data)

        with self.assertRaises(ValidationError) as e:
            school.clean()

        # Access the actual message from the exception and clean it
        error_message = str(e.exception).strip("[]'\"")

        # Ensure the correct message is in the exception
        self.assertIn(
            'The selected province is invalid. Please choose one from the available options.',
            error_message
        )

    def test_invalid_district(self):
        """Test that an invalid district raises a ValidationError."""
        invalid_school_data = self.school_data.copy()
        invalid_school_data['district'] = 'INVALID_DISTRICT'
        school = School(**invalid_school_data)

        with self.assertRaises(ValidationError) as e:
            school.clean()

        # Access the actual message from the exception and clean it
        error_message = str(e.exception).strip("[]'\"")

        # Ensure the correct message is in the exception
        self.assertIn(
            'The selected district is invalid. Please choose a valid school district from the provided options.',
            error_message
        )

    def test_invalid_logo_extension(self):
        """
        Test that the school logo is either .png or .jpg/.jpeg.
        """
        invalid_school_data = self.school_data.copy()
        invalid_school_data['logo'] = 'logo.gif'  # Invalid extension
        school = School(**invalid_school_data)
        with self.assertRaises(ValidationError) as e:
            school.clean()  # Should raise a validation error due to invalid logo extension

        # Access the actual message from the exception and clean it
        error_message = str(e.exception).strip("[]'\"")

        # Ensure the correct message is in the exception
        self.assertIn(
            'The school logo must be in PNG, JPG, or JPEG format. Please upload an image file with one of these extensions.',
            error_message
        )

    def test_school_id_is_uuid(self):
        """
        Test that school_id is a UUID and is automatically generated.
        """
        school = School.objects.create(**self.school_data)
        self.assertIsInstance(school.school_id, uuid.UUID)

    def test_ordering(self):
        """
        Test that schools are ordered by the 'name' field by default.
        """
        School.objects.create(
            name= 'School B',
            email_address= 'testschoolb@example.com',
            contact_number= '0123456782',
            student_count= 100,
            teacher_count= 20,
            admin_count= 10,
            in_arrears= False,
            none_compliant= False,
            type= 'PRIMARY',
            province= 'GAUTENG',
            district= 'GAUTENG NORTH',
            grading_system= 'A-F Grading',
            library_details= 'Well-stocked library',
            laboratory_details= 'State-of-the-art labs',
            sports_facilities= 'Football field, Basketball court',
            operating_hours= '08:00 - 15:00',
            location= '123 Main St',
            website= 'https://testschool.com',
        )
        School.objects.create(
            name= 'School A',
            email_address= 'testschoola@example.com',
            contact_number= '0123456789',
            student_count= 100,
            teacher_count= 20,
            admin_count= 10,
            in_arrears= False,
            none_compliant= False,
            type= 'PRIMARY',
            province= 'GAUTENG',
            district= 'GAUTENG NORTH',
            grading_system= 'A-F Grading',
            library_details= 'Well-stocked library',
            laboratory_details= 'State-of-the-art labs',
            sports_facilities= 'Football field, Basketball court',
            operating_hours= '08:00 - 15:00',
            location= '123 Main St',
            website= 'https://testschool.com',
        )
        schools = School.objects.all()
        self.assertEqual(schools[0].name, 'School A')

    def test_str_method(self):
        """
        Test the string representation of the model.
        """
        school = School.objects.create(**self.school_data)
        self.assertEqual(str(school), school.name)
