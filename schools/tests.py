# python 

# djnago
from django.test import TestCase
from django.core.exceptions import ValidationError

# models
from .models import School


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

