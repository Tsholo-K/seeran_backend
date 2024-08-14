# python
from datetime import timedelta

# django
from django.test import TestCase
from django.core.exceptions import ValidationError
from django.utils import timezone

from .models import CustomUser
from schools.models import School
from grades.models import Grade


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
            id_number='0208285344080',
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
            id_number='0208285344080',
            name="Jane",
            surname="Doe",
            role="STUDENT",
            grade=self.grade,
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
            role="STUDENT",
            grade=self.grade,
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
                id_number='0208285344080',
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
            phone_number='711740824',
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
                email="missinggrade@example.com",
                name="Frank",
                surname="Black",
                id_number='0208285344080',
                role="STUDENT",
                grade=None,
                school=self.school
            )

        with self.assertRaises(ValueError):
            CustomUser.objects.create_user(
                email="missingidentifier@example.com",
                name="Frank",
                surname="Black",
                role="STUDENT",
                grade=self.grade,
                school=self.school
            )
            
        with self.assertRaises(ValueError):
            CustomUser.objects.create_user(
                name="Grace",
                surname="Gray",
                role="TEACHER",
                school=self.school,
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

    def test_invalid_email_format(self):
        """
        Test creating a user with an invalid email format.
        """
        with self.assertRaises(ValueError):
            CustomUser.objects.create_user(
                email="invalid-email",
                name="Invalid",
                surname="Email",
                id_number='0208285344080',
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
                phone_number='711740824',
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
            phone_number='711740824',
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
            id_number='0208285344080',
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
                id_number='0208285344080',
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

    def test_role_change(self):
        """
        Test changing a user's role and verifying related constraints.
        """
        user = CustomUser.objects.create_user(
            email="change_role@example.com",
            name="Role",
            surname="Change",
            id_number='0208285344080',
            role="STUDENT",
            school=self.school,
            grade=self.grade,
        )
        user.role = "TEACHER"
        user.grade = None  # Remove grade since it's not required for TEACHER
        user.save()
        self.assertEqual(user.role, "TEACHER")
        self.assertIsNone(user.grade)

    def test_profile_picture_upload(self):
        """
        Test uploading a profile picture with various file sizes and formats.
        """
        from django.core.files.uploadedfile import SimpleUploadedFile

        # Test valid file upload
        valid_file = SimpleUploadedFile("profile.jpg", b"file_content", content_type="image/jpeg")
        user = CustomUser.objects.create_user(
            email="profilepic@example.com",
            name="Profile",
            surname="Pic",
            id_number='0208285344080',
            role="STUDENT",
            school=self.school,
            grade=self.grade,
            profile_picture=valid_file
        )
        self.assertTrue(user.profile_picture)

        # Test invalid file upload
        invalid_file = SimpleUploadedFile("profile.txt", b"file_content", content_type="text/plain")
        with self.assertRaises(ValueError):
            CustomUser.objects.create_user(
                email="invalidpic@example.com",
                name="Invalid",
                surname="Pic",
                id_number='0208285344080',
                role="STUDENT",
                school=self.school,
                grade=self.grade,
                profile_picture=invalid_file
            )

    def test_account_reactivation(self):
        """
        Test reactivating a previously deactivated user.
        """
        user = CustomUser.objects.create_user(
            email="reactivate@example.com",
            name="Reactivate",
            surname="User",
                id_number='0208285344080',
            role="STUDENT",
            school=self.school,
            grade=self.grade,
        )
        user.activated = False
        user.save()
        reactivated_user = CustomUser.objects.activate_user(
            email="reactivate@example.com",
            password="ValidPassword123"
        )
        self.assertTrue(reactivated_user.activated)
