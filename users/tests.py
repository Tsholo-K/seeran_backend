# django
from django.test import TestCase
from django.core.exceptions import ValidationError

# models
from .models import BaseUser, Founder, Principal, Admin, Teacher, Parent, Student
from schools.models import School
from grades.models import Grade


class BaseUserTests(TestCase):
    def setUp(self):
        self.base_user_data = {
            'name': 'John',
            'surname': 'Doe',
            'email_address': 'john.doe@example.com',
            'role': 'TEACHER',
        }

    def test_invalid_role(self):
        test_user_data = self.base_user_data.copy()

        test_user_data['role'] = 'invalid-role'
        test_user = BaseUser(**test_user_data)

        with self.assertRaises(ValidationError) as e:
            test_user.clean() # Will raise a validation error due to invalid role

        # Access the actual message from the exception and clean it
        error_message = str(e.exception).strip("[]'\"")

        # Ensure the correct message is in the exception
        self.assertIn(
            'Could not process your request, the specified account role is invalid. Please choose a valid role from the options: %s.' % [dict(BaseUser.ROLE_CHOICES).keys()],
            error_message
        )

    def test_unique_email_address(self):
        BaseUser.objects.create(**self.base_user_data)

        test_user_b = BaseUser(
            name='Jane',
            surname='Doe',
            email_address='john.doe@example.com',  # Same email
            role='STUDENT'
        )
        with self.assertRaises(ValidationError) as e:
            test_user_b.save() # Will raise a validation error due to unique constraint on the email field

        # Access the actual message from the exception and clean it
        error_message = str(e.exception).strip("[]'\"")

        # Ensure the correct message is in the exception
        self.assertIn(
            'Could not process your request, an account with the provided email address already exists. Please use a different email address or contact support if you believe this is an error.',
            error_message
        )

    def test_invalid_email_address(self):
        test_user_data = self.base_user_data.copy()

        test_user_data['email_address'] = 'invalid-email'
        test_user = BaseUser(**test_user_data)

        with self.assertRaises(ValidationError) as e:
            test_user.clean() # Will raise a validation error due to invalid email

        # Access the actual message from the exception and clean it
        error_message = str(e.exception).strip("[]'\"")

        # Ensure the correct message is in the exception
        self.assertIn(
            'Could not process your request, the provided email address is not in a valid format. Please correct the email address and try again.',
            error_message
        )

    def test_long_email_address(self):
        """Test that an email address longer than 254 characters raises a ValidationError."""
        test_user_data = self.base_user_data.copy()

        test_user_data['email_address'] = 'a' * 255 + '@example.com'  # Creating a long email (255 characters)
        test_user = BaseUser(**test_user_data)

        with self.assertRaises(ValidationError) as e:
            test_user.clean() # Will raise a validation error due to invalid email length

        # Access the actual message from the exception and clean it
        error_message = str(e.exception).strip("[]'\"")

        # Ensure the correct message is in the exception
        self.assertIn(
            'Could not process your request, email address cannot exceed 254 characters. Please correct the email address and try again.',
            error_message
        )

    def test_invalid_name(self):
        test_user_data = self.base_user_data.copy() # initial user data
        
        test_user_data['name'] = 'J' * 65
        test_user_a = BaseUser(**test_user_data) # user a

        with self.assertRaises(ValidationError) as e:
            test_user_a.clean() # Will raise a validation error due to invalid name length

        # Access the actual message from the exception and clean it
        error_message = str(e.exception).strip("[]'\"")

        # Ensure the correct message is in the exception
        self.assertIn(
            'Could not process your request, name cannot exceed 64 characters. Please correct the name and try again.',
            error_message
        )

        test_user_data['name'] = ''
        test_user_b = BaseUser(**test_user_data) # user b

        with self.assertRaises(ValidationError) as e:
            test_user_b.clean() # Will raise a validation error due to unprovided name

        # Access the actual message from the exception and clean it
        error_message = str(e.exception).strip("[]'\"")

        # Ensure the correct message is in the exception
        self.assertIn(
            'Could not process your request, a name is required for all accounts on the system. Please provide a valid name.',
            error_message
        )

class FounderTests(TestCase):
    def setUp(self):
        self.founder_data = {
            'name': 'Alice',
            'surname': 'Smith',
            'email_address': 'alice.smith@example.com',
            'role': 'FOUNDER'
        }

    def test_invalid_role(self):
        founder_data = self.founder_data.copy()

        founder_data['role'] = 'ADMIN' # Invalid role for founder
        founder = Founder(**founder_data)

        with self.assertRaises(ValidationError) as e:
            founder.clean()

        # Access the actual message from the exception and clean it
        error_message = str(e.exception).strip("[]'\"")

        # Ensure the correct message is in the exception
        self.assertIn(
            'Could not process your request, founder accounts can only have a role of "Founder". Please correct the provided information and try again.',
            error_message
        )

    def test_invalid_email(self):
        founder_data = self.founder_data.copy()

        founder_data['email_address'] = None # Invalid email for founder, email address missing
        founder = Founder(**founder_data)

        with self.assertRaises(ValidationError) as e:
            founder.clean()

        # Access the actual message from the exception and clean it
        error_message = str(e.exception).strip("[]'\"")

        # Ensure the correct message is in the exception
        self.assertIn(
            'Could not process your request, all founder accounts in the system are required to have an email address linked to their account. Please provide a valid email address.',
            error_message
        )

class PrincipalTests(TestCase):
    def setUp(self):
        self.school = School.objects.create(
            name= 'Test School',
            email_address= 'testschool@example.com',
            contact_number= '0123456789',
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
        )
        self.principal_data = {
            'name': 'Bob',
            'surname': 'Brown',
            'email_address': 'bob.brown@example.com',
            'contact_number': '0123456789',
            'role': 'PRINCIPAL',
            'school': self.school
        }

    def test_invalid_role(self):
        principal_data = self.principal_data.copy()

        principal_data['role'] = 'FOUNDER' # Invalid role for principal
        principal = Principal(**principal_data)

        with self.assertRaises(ValidationError) as e:
            principal.clean()

        # Access the actual message from the exception and clean it
        error_message = str(e.exception).strip("[]'\"")

        # Ensure the correct message is in the exception
        self.assertIn(
            'Could not process your request, principal accounts can only have a role of "Principal". Please correct the provided information and try again.',
            error_message
        )

    def test_invalid_email(self):
        principal_data = self.principal_data.copy()

        principal_data['email_address'] = None # Invalid email for principal account, email address missing
        principal = Principal(**principal_data)

        with self.assertRaises(ValidationError) as e:
            principal.clean()

        # Access the actual message from the exception and clean it
        error_message = str(e.exception).strip("[]'\"")

        # Ensure the correct message is in the exception
        self.assertIn(
            'Could not process your request, all principal accounts in the system are required to have an email address linked to their account. Please provide a valid email address.',
            error_message
        )

    def test_invalid_contact_number(self):
        principal_data = self.principal_data.copy()

        principal_data['contact_number'] = 'invalid-number' # Invalid contact number
        principal_a = Principal(**principal_data)

        with self.assertRaises(ValidationError) as e:
            principal_a.clean()

        # Access the actual message from the exception and clean it
        error_message = str(e.exception).strip("[]'\"")

        # Ensure the correct message is in the exception
        self.assertIn(
            'The contact number provided contains non-numeric characters. Please enter a numeric only contact number (e.g., 0123456789).',
            error_message
        )

        principal_data['contact_number'] = None # Invalid contact number, contact number missing
        principal_b = Principal(**principal_data)

        with self.assertRaises(ValidationError) as e:
            principal_b.clean()

        # Access the actual message from the exception and clean it
        error_message = str(e.exception).strip("[]'\"")

        # Ensure the correct message is in the exception
        self.assertIn(
            'Could not process your request, all principal accounts in the system are required to have an contact number linked to their account. Please provide a valid contact number.',
            error_message
        )

        principal_data['contact_number'] = '01236587498562548' # Invalid contact number, contact number too long
        principal_c = Principal(**principal_data)

        with self.assertRaises(ValidationError) as e:
            principal_c.clean()

        # Access the actual message from the exception and clean it
        error_message = str(e.exception).strip("[]'\"")

        # Ensure the correct message is in the exception
        self.assertIn(
            'The contact number must be between 10 and 15 digits long. Please provide a valid contact number within this range.',
            error_message
        )

        principal_data['contact_number'] = '02135647' # Invalid contact number, contact number too short
        principal_d = Principal(**principal_data)

        with self.assertRaises(ValidationError) as e:
            principal_d.clean()

        # Access the actual message from the exception and clean it
        error_message = str(e.exception).strip("[]'\"")

        # Ensure the correct message is in the exception
        self.assertIn(
            'The contact number must be between 10 and 15 digits long. Please provide a valid contact number within this range.',
            error_message
        )

    def test_invalid_school(self):
        principal_data = self.principal_data.copy()

        principal_data['school'] = None # Invalid school
        principal = Principal(**principal_data)

        with self.assertRaises(ValidationError) as e:
            principal.clean()

        # Access the actual message from the exception and clean it
        error_message = str(e.exception).strip("[]'\"")

        # Ensure the correct message is in the exception
        self.assertIn(
            'Principal accounts must be associated with a school. Please provide a school for this account.',
            error_message
        )

class AdminTests(TestCase):
    def setUp(self):
        self.school = School.objects.create(
            name= 'Test School',
            email_address= 'testschool@example.com',
            contact_number= '0123456789',
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
        )
        self.admin_data = {
            'name': 'Bob',
            'surname': 'Brown',
            'email_address': 'bob.brown@example.com',
            'role': 'ADMIN',
            'school': self.school
        }

    def test_invalid_role(self):
        admin_data = self.admin_data.copy()

        admin_data['role'] = 'FOUNDER' # Invalid role for admin
        admin = Admin(**admin_data)

        with self.assertRaises(ValidationError) as e:
            admin.clean()

        # Access the actual message from the exception and clean it
        error_message = str(e.exception).strip("[]'\"")

        # Ensure the correct message is in the exception
        self.assertIn(
            'Could not process your request, admin accounts can only have a role of "ADMIN". Please correct the provided information and try again.',
            error_message
        )

    def test_invalid_email(self):
        admin_data = self.admin_data.copy()

        admin_data['email_address'] = None # Invalid email for admin account, email address missing
        admin = Admin(**admin_data)

        with self.assertRaises(ValidationError) as e:
            admin.clean()

        # Access the actual message from the exception and clean it
        error_message = str(e.exception).strip("[]'\"")

        # Ensure the correct message is in the exception
        self.assertIn(
            'Could not process your request, all admin accounts in the system are required to have an email address linked to their account. Please provide a valid email address.',
            error_message
        )

    def test_invalid_school(self):
        admin_data = self.admin_data.copy()

        admin_data['school'] = None # Invalid school
        admin = Admin(**admin_data)

        with self.assertRaises(ValidationError) as e:
            admin.clean()

        # Access the actual message from the exception and clean it
        error_message = str(e.exception).strip("[]'\"")

        # Ensure the correct message is in the exception
        self.assertIn(
            'Could not process your request, admin accounts must be associated with a school. Please provide a school for this account.',
            error_message
        )
class TeacherTests(TestCase):
    def setUp(self):
        self.school = School.objects.create(
            name= 'Test School',
            email_address= 'testschool@example.com',
            contact_number= '0123456789',
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
        )
        self.teacher_data = {
            'name': 'Bob',
            'surname': 'Brown',
            'email_address': 'bob.brown@example.com',
            'role': 'TEACHER',
            'school': self.school
        }

    def test_invalid_role(self):
        teacher_data = self.teacher_data.copy()

        teacher_data['role'] = 'FOUNDER' # Invalid role for teacher
        teacher = Teacher(**teacher_data)

        with self.assertRaises(ValidationError)as e:
            teacher.clean()

        # Access the actual message from the exception and clean it
        error_message = str(e.exception).strip("[]'\"")

        # Ensure the correct message is in the exception
        self.assertIn(
            'Could not process your request, teacher accounts can only have a role of "TEACHER". Please correct the provided information and try again.',
            error_message
        )

    def test_invalid_email(self):
        teacher_data = self.teacher_data.copy()

        teacher_data['email_address'] = None # Invalid email for teacher account, email address missing
        teacher = Teacher(**teacher_data)

        with self.assertRaises(ValidationError) as e:
            teacher.clean()

        # Access the actual message from the exception and clean it
        error_message = str(e.exception).strip("[]'\"")

        # Ensure the correct message is in the exception
        self.assertIn(
            'Could not process your request, all teacher accounts in the system are required to have an email address linked to their account. Please provide a valid email address.',
            error_message
        )

    def test_invalid_school(self):
        teacher_data = self.teacher_data.copy()

        teacher_data['school'] = None # Invalid school
        teacher = Teacher(**teacher_data)

        with self.assertRaises(ValidationError) as e:
            teacher.clean()

        # Access the actual message from the exception and clean it
        error_message = str(e.exception).strip("[]'\"")

        # Ensure the correct message is in the exception
        self.assertIn(
            'Could not process your request, teacher accounts must be associated with a school. Please provide a school for this account.',
            error_message
        )

class StudentTests(TestCase):
    def setUp(self):
        self.school = School.objects.create(
            name= 'Test School',
            email_address= 'testschool@example.com',
            contact_number= '0123456789',
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
        )
        self.grade = Grade.objects.create(
            grade='10',
            school=self.school
        )
        self.student_data = {
            'name': 'Bob',
            'surname': 'Brown',
            'id_number': '0208285344080',
            'role': 'STUDENT',
            'grade': self.grade,
            'school': self.school
        }

    def test_invalid_role(self):
        student_data = self.student_data.copy()

        student_data['role'] = 'FOUNDER' # Invalid role for student
        student = Student(**student_data)

        with self.assertRaises(ValidationError)as e:
            student.clean()

        # Access the actual message from the exception and clean it
        error_message = str(e.exception).strip("[]'\"")

        # Ensure the correct message is in the exception
        self.assertIn(
            'Could not process your request, student accounts can only have a role of "STUDENT". Please correct the provided information and try again.',
            error_message
        )

    def test_unique_id_number(self):
        student_data = self.student_data.copy()

        Student.objects.create(**student_data)

        with self.assertRaises(ValidationError)as e:
            Student.objects.create(**student_data) # Will raise a validation error due to unique constraint in the ID number field

        # Access the actual message from the exception and clean it
        error_message = str(e.exception).strip("[]'\"")

        # Ensure the correct message is in the exception
        self.assertIn(
            'Could not process your request, an account with the provided ID number already exists, please use a different ID number.',
            error_message
        )

    def test_invalid_id_number(self):
        student_data = self.student_data.copy()

        student_data['id_number'] = '0936748364527' # Invalid ID number
        student_a = Student(**student_data)

        with self.assertRaises(ValidationError)as e:
            student_a.clean() # Will raise a validation error due to the invlid ID number

        # Access the actual message from the exception and clean it
        error_message = str(e.exception).strip("[]'\"")

        # Ensure the correct message is in the exception
        self.assertIn(
            'The provided ID number is invalid. Please ensure it contains 13 digits, follows the correct date format (YYMMDD), and is a valid South African ID number. If unsure, verify the number and try again.',
            error_message
        )

        student_data['id_number'] = None # Invalid ID number
        student_b = Student(**student_data)

        with self.assertRaises(ValidationError)as e:
            student_b.clean() # Will raise a validation error due to unprovided ID number

        # Access the actual message from the exception and clean it
        error_message = str(e.exception).strip("[]'\"")

        # Ensure the correct message is in the exception
        self.assertIn(
            'Could not process your request, either ID or Passport number is required for every student account on the system.',
            error_message
        )

    def test_unique_passport_number(self):
        student_data = self.student_data.copy()

        student_data['id_number'] = None
        student_data['passport_number'] = '012345678'
        Student.objects.create(**student_data)

        with self.assertRaises(ValidationError)as e:
            Student.objects.create(**student_data) # Will raise a validation error due to unique constraint in the passport number field

        # Access the actual message from the exception and clean it
        error_message = str(e.exception).strip("[]'\"")

        # Ensure the correct message is in the exception
        self.assertIn(
            'Could not process your request, an account with the provided passport number already exists, please use a different passport number.',
            error_message
        )

    def test_invalid_passport_number(self):
        student_data = self.student_data.copy()

        student_data['id_number'] = None 
        student_data['passport_number'] = '56325' # Invalid passport number length, too short
        student_a = Student(**student_data)

        with self.assertRaises(ValidationError)as e:
            student_a.clean() # Will raise a validation error due to invalid passport number length

        # Access the actual message from the exception and clean it
        error_message = str(e.exception).strip("[]'\"")

        # Ensure the correct message is in the exception
        self.assertIn(
            'The provided passport number is invalid. Please ensure it contains between 6 and 9 alphanumeric characters without spaces or special characters.',
            error_message
        )

        student_data['passport_number'] = '6532658974' # Invalid ID number length, too long
        student_b = Student(**student_data)

        with self.assertRaises(ValidationError):
            student_b.clean() # Will raise a validation error due to invalid passport number length

        # Access the actual message from the exception and clean it
        error_message = str(e.exception).strip("[]'\"")

        # Ensure the correct message is in the exception
        self.assertIn(
            'The provided passport number is invalid. Please ensure it contains between 6 and 9 alphanumeric characters without spaces or special characters.',
            error_message
        )

    def test_invalid_grade(self):
        student_data = self.student_data.copy()

        student_data['grade'] = None 
        student_a = Student(**student_data)

        with self.assertRaises(ValidationError)as e:
            student_a.clean() # Will raise a validation error due to unprovided grade

        # Access the actual message from the exception and clean it
        error_message = str(e.exception).strip("[]'\"")

        # Ensure the correct message is in the exception
        self.assertIn(
            'Could not process your request, student accounts must be assigned to a grade. please correct the provided information and try again.',
            error_message
        )

    def test_invalid_school(self):
        student_data = self.student_data.copy()

        student_data['school'] = None # Invalid school
        student = Student(**student_data)

        with self.assertRaises(ValidationError)as e:
            student.clean() # Will raise a validation error due to unprovided school

        # Access the actual message from the exception and clean it
        error_message = str(e.exception).strip("[]'\"")

        # Ensure the correct message is in the exception
        self.assertIn(
            'Could not process your request, student accounts must be associated with a school. Please provide a school for this account.',
            error_message
        )

class ParentTests(TestCase):
    def setUp(self):
        self.parent_data = {
            'name': 'Bob',
            'surname': 'Brown',
            'email_address': 'bob.brown@example.com',
            'role': 'PARENT',
        }
        self.school = School.objects.create(
            name= 'Test School',
            email_address= 'testschool@example.com',
            contact_number= '0123456789',
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
        )
        self.grade = Grade.objects.create(
            grade='10',
            school=self.school
        )
        self.child = Student.objects.create(
            name= 'Bob',
            surname= 'Brown',
            id_number= '0208285344080',
            role= 'STUDENT',
            grade= self.grade,
            school= self.school
        )

    def test_invalid_role(self):
        parent_data = self.parent_data.copy()

        parent_data['role'] = 'FOUNDER' # Invalid role for teacher
        parent = Parent(**parent_data)

        with self.assertRaises(ValidationError)as e:
            parent.clean() # Will raise a validation error due to invalid role for account

        # Access the actual message from the exception and clean it
        error_message = str(e.exception).strip("[]'\"")

        # Ensure the correct message is in the exception
        self.assertIn(
            'Could not process your request, parent accounts can only have a role of "PARENT". Please correct the provided information and try again.',
            error_message
        )

    def test_invalid_email(self):
        parent_data = self.parent_data.copy()

        parent_data['email_address'] = None # Invalid email for parent account, email address missing
        parent = Parent(**parent_data)

        with self.assertRaises(ValidationError) as e:
            parent.clean() # Will raise a validation error due to unprovided email address

        # Access the actual message from the exception and clean it
        error_message = str(e.exception).strip("[]'\"")

        # Ensure the correct message is in the exception
        self.assertIn(
            'Could not process your request, all parent accounts in the system are required to have an email address linked to their account. Please provide a valid email address.',
            error_message
        )

    def test_children_assignment(self):
        parent = Parent.objects.create(**self.parent_data)
        parent.add_child(self.child)

        with self.assertRaises(ValidationError)as e:
            parent.add_child(parent)

        # Access the actual message from the exception and clean it
        error_message = str(e.exception).strip("[]'\"")

        # Ensure the correct message is in the exception
        self.assertIn(
            'Could not process your request, only student accounts can be assigned as children to a parent account.',
            error_message
        )
