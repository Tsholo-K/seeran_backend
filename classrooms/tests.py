# python
from datetime import date
from decimal import Decimal

# django
from django.test import TestCase
from django.core.exceptions import ValidationError

# models
from .models import Classroom
from schools.models import School
from accounts.models import Teacher, Student
from grades.models import Grade
from subjects.models import Subject
from terms.models import Term


class ClassroomModelTest(TestCase):
    
    def setUp(self):
        # Create basic objects needed for Classroom creation

        # Create secondary school instance for testing
        self.school = School.objects.create(
            name='Test School',
            email_address='secondaryschool@example.com',
            contact_number='0123456789',
            student_count=130,
            teacher_count=24,
            admin_count=19,
            in_arrears=False,
            none_compliant=False,
            type='SECONDARY',
            province='GAUTENG',
            district='GAUTENG WEST',
            grading_system='A-F Grading',
            library_details='Well-stocked library',
            laboratory_details='State-of-the-art labs',
            sports_facilities='Football field, Basketball court',
            operating_hours='07:45 - 14:00',
            location='456 INNER St',
            website='https://secondaryschool.com',
        )

        # Create a Grade instance linked to the School
        self.grade = Grade.objects.create(
            major_subjects= 1, 
            none_major_subjects= 2,
            grade= '10', 
            school= self.school
        )
        
        # Create a Subject instance linked to the Grade
        self.subject = Subject.objects.create(
            subject= 'MATHEMATICS',
            major_subject= True,
            pass_mark= 50.00,
            student_count= 30,
            teacher_count= 2,
            classroom_count= 1,
            grade= self.grade
        )

        # Create a Term instance linked to the Grade
        self.term_1 = Term.objects.create(
            term= 'Term 1',
            weight= Decimal('20.00'),
            start_date= date(2024, 1, 15),
            end_date= date(2024, 4, 10),
            grade= self.grade,
            school= self.school
        )

        # Create a Term instance linked to the Grade
        self.term_2 = Term.objects.create(
            term= 'Term 2',
            weight= Decimal('20.00'),
            start_date= date(2024, 4, 25),
            end_date= date(2024, 7, 1),
            grade= self.grade,
            school= self.school
        )

        # Create a Teacher instance linked to the School
        self.teacher = Teacher.objects.create(
            name="John Doe",
            surname= 'Doe',
            email_address= 'testteacher@example.com',
            role= 'TEACHER',
            school= self.school
        )

        # Create a Student instance linked to the School
        self.student_a = Student.objects.create(
            name="Alice", 
            surname= 'Wang',
            id_number= '0208285344080',
            role= 'STUDENT',
            grade= self.grade,
            school= self.school
        )

        # Create a Student instance linked to the School
        self.student_b = Student.objects.create(
            name="Bob", 
            surname= 'Marly',
            passport_number= '652357849',
            role= 'STUDENT',
            grade= self.grade,
            school= self.school
        )

        # Create a Student instance linked to the School
        self.student_c = Student.objects.create(
            name="Frank", 
            surname= 'Caitlyn',
            passport_number= '652357864',
            role= 'STUDENT',
            grade= self.grade,
            school= self.school
        )

        self.classroom_data = {
            'classroom_number': 'E pod 403',
            'group': '10A',
            'teacher': self.teacher,
            'grade': self.grade,
            'subject': self.subject,
            'school': self.school
        }

    def test_create_classroom(self):
        """Test that a classroom can be successfully created."""
        classroom = Classroom.objects.create(**self.classroom_data)

        self.assertEqual(classroom.classroom_number, "E pod 403")
        self.assertEqual(classroom.group, "10A")
        self.assertEqual(classroom.teacher, self.teacher)
        self.assertEqual(classroom.subject, self.subject)
        self.assertEqual(classroom.grade, self.grade)
        self.assertEqual(classroom.school, self.school)
    
    def test_no_subject_and_not_register(self):
        """Test that a classroom raises an error when no subject or register class is set."""
        classroom_data = self.classroom_data.copy()

        classroom_data['subject'] = None
        classroom = Classroom(**classroom_data)

        with self.assertRaises(ValidationError) as e:
            classroom.clean()  # Call clean to manually trigger validation

    def test_subject_classroom_unique_constraint(self):
        """Test that unique constraint on group works."""
        classroom_data = self.classroom_data.copy()

        classroom_data['subject'] = None
        classroom_data['register_class'] = True
        Classroom.objects.create(**classroom_data)

        classroom_data['subject'] = self.subject
        classroom_data['register_class'] = False
        Classroom.objects.create(**classroom_data)

        classroom_data['classroom_number'] = 'D pod 607'
        
        with self.assertRaises(ValidationError) as e:
            Classroom.objects.create(**classroom_data)

    def test_register_classroom_unique_constraint(self):
        """Test that unique constraint on group works."""
        classroom_data = self.classroom_data.copy()
        
        Classroom.objects.create(**classroom_data)

        classroom_data['subject'] = None
        classroom_data['register_class'] = True
        Classroom.objects.create(**classroom_data)

        classroom_data['classroom_number'] = 'A pod 100'
        
        with self.assertRaises(ValidationError) as e:
            Classroom.objects.create(**classroom_data)

    def test_students_assignment(self):
        """Test that student updates works well."""
        classroom = Classroom.objects.create(**self.classroom_data)

        classroom.update_students([self.student_a.account_id, self.student_b.account_id, self.student_c.account_id])
        classroom.update_students([self.student_b.account_id, self.student_c.account_id], remove=True)

        with self.assertRaises(ValidationError) as e:
            classroom.update_students()

        with self.assertRaises(ValidationError) as e:
            classroom.update_students([classroom.classroom_id])

    def test_teacher_assignment(self):
        """Test that teacher assignment works well."""
        classroom = Classroom.objects.create(**self.classroom_data)

        classroom.update_teacher()
        classroom.update_teacher(self.teacher.account_id)

        with self.assertRaises(ValidationError) as e:
            classroom.update_teacher(classroom.classroom_id)

    # def test_update_performance_metrics(self):
    #     """Test the update of classroom performance metrics."""
    #     classroom = Classroom.objects.create(**self.classroom_data)

    #     classroom.update_students([self.student_a.account_id, self.student_b.account_id, self.student_c.account_id])
        
    #     # Mock performance data for the students (assuming performance is in subject)
    #     performance1 = StudentPerformance.objects.create(student=self.student1, subject=self.subject, term=self.term_1, normalized_score=80)
    #     performance2 = StudentPerformance.objects.create(student=self.student2, subject=self.subject, term=self.term_1, normalized_score=45)
        
    #     # Update classroom performance metrics
    #     classroom.update_performance_metrics()
        
    #     self.assertEqual(classroom.pass_rate, 50)
    #     self.assertEqual(classroom.failure_rate, 50)
    #     self.assertEqual(classroom.average_score, 62.5)
    #     self.assertEqual(classroom.highest_score, 80)
    #     self.assertEqual(classroom.lowest_score, 45)
