from django.test import TestCase
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta

from .models import School, Grade, CustomUser

class CustomUserManagerTest(TestCase):
    """
    Test cases for the CustomUserManager.
    """

    def setUp(self):
        """
        Set up the test environment by creating necessary instances.
        """
        self.school = School.objects.create(
            name="Test School",
            email="testschool@example.com",
            contact_number="1234567890",
            school_type="PRIMARY",
            province="GAUTENG",
            school_district="GAUTENG NORTH"
        )
        self.grade = Grade.objects.create(
            grade='8',
            major_subjects=1,
            none_major_subjects=2,
            school=self.school
        )

    def test_create_user_with_email(self):
        """
        Test creating a user with email.
        """
        user = CustomUser.objects.create_user(
            email="testuser@example.com",
            name="John",
            surname="Doe",
            role="STUDENT",
            school=self.school,
            grade=self.grade,
        )
        self.assertEqual(user.email, "testuser@example.com")
        self.assertTrue(user.check_password(''))

    def test_create_user_with_id_number(self):
        """
        Test creating a user with ID number.
        """
        user = CustomUser.objects.create_user(
            id_number="1234567890123",
            name="Jane",
            surname="Doe",
            role="TEACHER",
            school=self.school,
        )
        self.assertEqual(user.id_number, "1234567890123")

    def test_create_user_with_passport_number(self):
        """
        Test creating a user with passport number.
        """
        user = CustomUser.objects.create_user(
            passport_number="A12345678",
            name="Alice",
            surname="Smith",
            role="ADMIN",
            school=self.school,
        )
        self.assertEqual(user.passport_number, "A12345678")

    def test_create_user_without_email_id_passport(self):
        """
        Test creating a user without any identifier.
        """
        with self.assertRaises(ValueError):
            CustomUser.objects.create_user(
                name="Bob",
                surname="Brown",
                role="STUDENT",
                school=self.school,
                grade=self.grade,
            )

    def test_create_user_with_existing_email(self):
        """
        Test creating a user with an existing email.
        """
        CustomUser.objects.create_user(
            email="existinguser@example.com",
            name="Charlie",
            surname="Brown",
            role="PARENT",
            school=self.school,
        )
        with self.assertRaises(ValueError):
            CustomUser.objects.create_user(
                email="existinguser@example.com",
                name="David",
                surname="Green",
                role="STUDENT",
                school=self.school,
                grade=self.grade,
            )

    def test_activate_user(self):
        """
        Test activating a user account.
        """
        user = CustomUser.objects.create_user(
            email="activateuser@example.com",
            name="Eve",
            surname="White",
            role="PRINCIPAL",
            school=self.school,
        )
        user = CustomUser.objects.activate_user(
            email="activateuser@example.com",
            password="securepassword"
        )
        self.assertTrue(user.activated)
        self.assertTrue(user.check_password("securepassword"))

    def test_user_role_requirements(self):
        """
        Test role-specific requirements for users.
        """
        with self.assertRaises(ValueError):
            CustomUser.objects.create_user(
                email="missingrole@example.com",
                name="Frank",
                surname="Black",
                role="STUDENT",
                school=self.school
            )
        
        with self.assertRaises(ValueError):
            CustomUser.objects.create_user(
                email="missingphone@example.com",
                name="Grace",
                surname="Gray",
                role="PRINCIPAL",
                school=self.school,
                phone_number=None
            )

    """
    Test edge cases for the CustomUser model and CustomUserManager.
    """

    def setUp(self):
        """
        Set up the test environment by creating necessary instances.
        """
        self.school = School.objects.create(
            name="Test School",
            email="testschool@example.com",
            contact_number="1234567890",
            school_type="PRIMARY",
            province="GAUTENG",
            school_district="GAUTENG NORTH"
        )
        self.grade = Grade.objects.create(
            grade='8',
            major_subjects=1,
            none_major_subjects=2,
            school=self.school
        )

    def test_invalid_email_format(self):
        """
        Test creating a user with an invalid email format.
        """
        with self.assertRaises(ValueError):
            CustomUser.objects.create_user(
                email="invalid-email",
                name="Invalid",
                surname="Email",
                role="STUDENT",
                school=self.school,
                grade=self.grade,
            )

    def test_missing_phone_number_for_principal(self):
        """
        Test creating a principal without a phone number.
        """
        with self.assertRaises(ValueError):
            CustomUser.objects.create_user(
                email="principal@example.com",
                name="Missing",
                surname="Phone",
                role="PRINCIPAL",
                school=self.school,
                phone_number=None
            )

    def test_activation_with_invalid_password(self):
        """
        Test activating a user with an invalid password.
        """
        CustomUser.objects.create_user(
            email="activateuser@example.com",
            name="Activate",
            surname="User",
            role="PRINCIPAL",
            school=self.school,
        )
        with self.assertRaises(ValueError):
            CustomUser.objects.activate_user(
                email="activateuser@example.com",
                password="short"
            )

    def test_create_user_with_long_fields(self):
        """
        Test creating a user with extremely long field values.
        """
        long_email = "x" * 255 + "@example.com"
        long_name = "x" * 32
        long_surname = "x" * 32

        user = CustomUser.objects.create_user(
            email=long_email,
            name=long_name,
            surname=long_surname,
            role="STUDENT",
            school=self.school,
            grade=self.grade,
        )
        self.assertEqual(user.email, long_email)
        self.assertEqual(user.name, long_name)
        self.assertEqual(user.surname, long_surname)

    def test_user_without_required_fields(self):
        """
        Test creating a user without required fields.
        """
        with self.assertRaises(ValueError):
            CustomUser.objects.create_user(
                email="incomplete@example.com",
                name="Incomplete",
                surname="User",
                role="STUDENT",
            )

    def test_concurrent_user_creation(self):
        """
        Test creating multiple users simultaneously.
        """
        from threading import Thread

        def create_user():
            CustomUser.objects.create_user(
                email="threadeduser@example.com",
                name="Threaded",
                surname="User",
                role="STUDENT",
                school=self.school,
                grade=self.grade,
            )

        threads = [Thread(target=create_user) for _ in range(10)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        self.assertTrue(CustomUser.objects.filter(email="threadeduser@example.com").exists())
