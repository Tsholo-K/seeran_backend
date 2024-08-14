# python
from datetime import timedelta
import threading 

# django
from django.test import TestCase
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.db import transaction, IntegrityError

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
        self.school.save()
        self.grade = Grade.objects.create(
            grade='8',
            major_subjects=1,
            none_major_subjects=2,
            school=self.school
        )
        self.grade.save()

    def test_create_user_with_email(self):
        """
        Test creating a user with email.
        """

        # Case 1: Valid email creation
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
        self.assertTrue(user.password is None)

        # Case 2: Email with invalid format
        with self.assertRaises(ValueError):
            CustomUser.objects.create_user(
                email="invalid-email",
                name="Invalid",
                surname="Email",
                id_number='0208285344081',
                role="STUDENT",
                school=self.school,
                grade=self.grade,
            )

        # Case 3: Duplicate Emails
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

    def test_create_user_with_id_number(self):
        """
        Test creating a user with ID number.
        """

        # Case 1: Valid ID number creation
        user = CustomUser.objects.create_user(
            id_number='0208285344080',
            name="Jane",
            surname="Doe",
            role="STUDENT",
            grade=self.grade,
            school=self.school,
        )
        self.assertEqual(user.id_number, "0208285344080")

        # Case 2: Duplicate ID number
        with self.assertRaises(ValueError):
            CustomUser.objects.create_user(
                id_number='0208285344080',
                name="Jane",
                surname="Doe",
                role="STUDENT",
                grade=self.grade,
                school=self.school,
            )

    def test_create_user_with_passport_number(self):
        """
        Test creating a user with passport number.
        """

        # Case 1: Valid passport number creation
        user = CustomUser.objects.create_user(
            passport_number="123456789",
            name="Alice",
            surname="Smith",
            role="STUDENT",
            grade=self.grade,
            school=self.school,
        )
        self.assertEqual(user.passport_number, "A12345678")

        # Case 2: Duplicate passport number
        with self.assertRaises(ValueError):
            CustomUser.objects.create_user(
                passport_number="123456789",
                name="Bob",
                surname="Smith",
                role="STUDENT",
                grade=self.grade,
                school=self.school,
            )        

    def test_activate_user(self):
        """
        Test activating a user account with various password scenarios.
        """
        user = CustomUser.objects.create_user(
            email="activateuser@example.com",
            name="Eve",
            surname="White",
            phone_number='711740824',
            role="PRINCIPAL",
            school=self.school,
        )

        # Case 1: Valid password
        user = CustomUser.objects.activate_user(
            email="activateuser@example.com",
            password="SecurePassword123!"
        )
        self.assertTrue(user.activated)
        self.assertTrue(user.check_password("SecurePassword123!"))

        # Case 2: Password without an uppercase letter
        with self.assertRaises(ValueError) as context:
            CustomUser.objects.activate_user(
                email="activateuser@example.com",
                password="securepassword123!"
            )
        self.assertIn("Password must contain at least one uppercase letter", str(context.exception))

        # Case 3: Password without a number
        with self.assertRaises(ValueError) as context:
            CustomUser.objects.activate_user(
                email="activateuser@example.com",
                password="SecurePassword!"
            )
        self.assertIn("Password must contain at least one digit", str(context.exception))

        # Case 4: Password without a special character
        with self.assertRaises(ValueError) as context:
            CustomUser.objects.activate_user(
                email="activateuser@example.com",
                password="SecurePassword123"
            )
        self.assertIn("Password must contain at least one special character", str(context.exception))

        # Case 5: Password too short (e.g., less than 8 characters)
        with self.assertRaises(ValueError) as context:
            CustomUser.objects.activate_user(
                email="activateuser@example.com",
                password="S1!"
            )
        self.assertIn("Password must be at least 8 characters long", str(context.exception))

        # Case 6: Password too long (e.g., more than 128 characters)
        long_password = "S" + "e" * 127 + "!"
        with self.assertRaises(ValueError) as context:
            CustomUser.objects.activate_user(
                email="activateuser@example.com",
                password=long_password
            )
        self.assertIn("Password cannot exceed 128 characters", str(context.exception))

    def test_user_role_requirements(self):
        """
        Test role-specific requirements for users.
        """
        # Case 1: Missing school for roles that require it
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

        # Case 2: Missing identifier for STUDENT role
        with self.assertRaises(ValueError):
            CustomUser.objects.create_user(
                email="missingidentifier@example.com",
                name="Frank",
                surname="Black",
                role="STUDENT",
                grade=self.grade,
                school=self.school
            )

        # Case 3: Missing required fields for TEACHER role
        with self.assertRaises(ValueError):
            CustomUser.objects.create_user(
                name="Grace",
                surname="Gray",
                role="TEACHER",
                school=self.school,
            )

        # Case 4: Missing phone number for PRINCIPAL role
        with self.assertRaises(ValueError):
            CustomUser.objects.create_user(
                email="missingphone@example.com",
                name="Grace",
                surname="Gray",
                role="PRINCIPAL",
                school=self.school,
                phone_number=None
            )

    def test_create_user_with_long_fields(self):
        """
        Test creating a user with field values that exceed the maximum allowed length.
        """
        # Max length
        long_email = "x" * 242 + "@example.com"
        long_name = "x" * 64
        long_surname = "x" * 64

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

        # Exceeding length
        too_long_email = "x" * 255 + "@example.com"
        too_long_name = "x" * 65
        too_long_surname = "x" * 65

        # Case 1: Long email
        with self.assertRaises(ValidationError) as context:
            CustomUser.objects.create_user(
                email=too_long_email,
                name='john',
                surname='doe',
                id_number='0208285344081',
                role="STUDENT",
                school=self.school,
                grade=self.grade,
            )
        self.assertIn("email address cannot exceed 254 characters", str(context.exception))

        # Case 2: Long name
        with self.assertRaises(ValidationError) as context:
            CustomUser.objects.create_user(
                email="normalemail@example.com",
                name=too_long_name,
                surname='doe',
                id_number='0208285344082',
                role="STUDENT",
                school=self.school,
                grade=self.grade,
            )
        self.assertIn("name cannot exceed 64 characters", str(context.exception))

        # Case 3: Long surname
        with self.assertRaises(ValidationError) as context:
            CustomUser.objects.create_user(
                email="normalemail@example.com",
                name='john',
                surname=too_long_surname,
                id_number='0208285344083',
                role="STUDENT",
                school=self.school,
                grade=self.grade,
            )
        self.assertIn("surname cannot exceed 64 characters", str(context.exception))

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

    # def test_concurrent_user_creation_race_condition(self):
    #     """
    #     Test handling race conditions when creating users.
    #     """
    #     def create_user(email_suffix):
    #         with transaction.atomic():
    #             CustomUser.objects.create_user(
    #                 email=f"raceconditionuser{email_suffix}@example.com",
    #                 name="RaceCondition",
    #                 surname="User",
    #                 id_number=f'020828{email_suffix}',  # Ensure unique ID
    #                 role="STUDENT",
    #                 school=self.school,
    #                 grade=self.grade,
    #             )

    #     email_suffixes = [f"{i:03d}" for i in range(10)]
    #     threads = [threading.Thread(target=create_user, args=(suffix,)) for suffix in email_suffixes]
    #     for thread in threads:
    #         thread.start()
    #     for thread in threads:
    #         thread.join()

    #     self.assertEqual(CustomUser.objects.count(), 10)


    # def test_concurrent_user_creation_with_duplicate_emails(self):
    #     """
    #     Test creating multiple users with the same email simultaneously.
    #     """
    #     def create_user(email):
    #         with transaction.atomic():
    #             try:
    #                 # Generate a unique 13-character ID number
    #                 id_number = f'020828{threading.current_thread().name[-7:].zfill(7)}'
    #                 CustomUser.objects.create_user(
    #                     email=email,
    #                     name="DuplicateEmail",
    #                     surname="User",
    #                     id_number=id_number,  # Ensure 13 characters including prefix
    #                     role="STUDENT",
    #                     school=self.school,
    #                     grade=self.grade,
    #                 )
    #             except IntegrityError:
    #                 pass

    #     email = "duplicateemail@example.com"
    #     threads = [threading.Thread(target=create_user, args=(email,)) for _ in range(10)]
    #     for thread in threads:
    #         thread.start()
    #     for thread in threads:
    #         thread.join()

    #     self.assertEqual(CustomUser.objects.filter(email=email).count(), 1)


    # def test_concurrent_user_creation_with_duplicate_id_numbers(self):
    #     """
    #     Test creating multiple users with the same ID number simultaneously.
    #     """
    #     def create_user(id_number):
    #         try:
    #             with transaction.atomic():
    #                 CustomUser.objects.create_user(
    #                     email=f"uniqueuser{threading.current_thread().name}@example.com",
    #                     name="DuplicateID",
    #                     surname="User",
    #                     id_number=id_number,
    #                     role="STUDENT",
    #                     school=self.school,
    #                     grade=self.grade,
    #                 )
    #         except IntegrityError:
    #             pass

    #     id_number = '0208285344080'
    #     threads = [threading.Thread(target=create_user, args=(id_number,)) for _ in range(10)]
    #     for thread in threads:
    #         thread.start()
    #     for thread in threads:
    #         thread.join()

    #     self.assertEqual(CustomUser.objects.filter(id_number=id_number).count(), 1)

    # def test_concurrent_user_creation_with_duplicate_passport_number(self):
    #     """
    #     Test creating multiple users with the same passport number simultaneously.
    #     """
    #     def create_user(passport_number):
    #         try:
    #             with transaction.atomic():
    #                 CustomUser.objects.create_user(
    #                     email=f"uniqueuser{threading.current_thread().name}@example.com",
    #                     name="DuplicatePassport",
    #                     surname="User",
    #                     passport_number=passport_number,
    #                     role="STUDENT",
    #                     school=self.school,
    #                     grade=self.grade,
    #                 )
    #         except IntegrityError:
    #             pass

    #     passport_number = '1234567890'
    #     threads = [threading.Thread(target=create_user, args=(passport_number,)) for _ in range(10)]
    #     for thread in threads:
    #         thread.start()
    #     for thread in threads:
    #         thread.join()

    #     self.assertEqual(CustomUser.objects.filter(passport_number=passport_number).count(), 1)