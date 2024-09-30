# python
from datetime import date
from decimal import Decimal

# django
from django.test import TestCase
from django.core.exceptions import ValidationError
from django.utils import timezone

# models
from .models import TermSubjectPerformance
from schools.models import School
from accounts.models import Teacher, Student
from grades.models import Grade
from terms.models import Term
from subjects.models import Subject
from classrooms.models import Classroom
from assessments.models import Assessment
from assessment_submissions.models import Submission
from assessment_transcripts.models import Transcript


class TermSubjectPerformanceTest(TestCase):

    def setUp(self):
        """
        Set up initial data, including a student, an assessment, and a submission 
        for the student.
        """

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
            student_count= 3,
            teacher_count= 1,
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

        self.classroom = Classroom.objects.create(
            classroom_number= 'E pod 403',
            group= '10A',
            teacher= self.teacher,
            grade= self.grade,
            subject= self.subject,
            school= self.school,
        )

        # Create an assessment
        self.assessment = Assessment.objects.create(
            title= 'Midterm Exam',
            assessor= self.teacher,
            start_time= timezone.now() + timezone.timedelta(days=10),
            dead_line= timezone.now() + timezone.timedelta(hours=2) + timezone.timedelta(days=10),
            total= Decimal(100),
            percentage_towards_term_mark= Decimal(30.00),
            collected= True,
            term= self.term_1,
            classroom= self.classroom,
            subject= self.subject,
            grade= self.grade,
            school= self.school,
        )
        
        self.term_performance_data = {
            'pass_rate': 75.0,
            'failure_rate': 25.0,
            'highest_score': 95.0,
            'lowest_score': 35.0,
            'average_score': 65.0,
            'median_score': 60.0,
            'standard_deviation': 12.0,
            'term': self.term_1,
            'subject': self.subject,
            'school': self.school,
        }
    
    def test_model_creation(self):
        """Test that a TermSubjectPerformance object is created with valid data."""
        performance = TermSubjectPerformance.objects.create(**self.term_performance_data)

        self.assertEqual(performance.pass_rate, 75.0)
        self.assertEqual(performance.school.name, "Test School")

    def test_invalid_rates(self):
        """Test that a pass rate greater than 100 raises a ValidationError."""
        term_performance_data = self.term_performance_data.copy()

        term_performance_data['pass_rate'] = 110.0
        performance_a = TermSubjectPerformance(**term_performance_data)

        with self.assertRaises(ValidationError):
            performance_a.clean()

        term_performance_data['pass_rate'] = 70.0
        term_performance_data['failure_rate'] = 110.0
        performance_b = TermSubjectPerformance(**term_performance_data)

        with self.assertRaises(ValidationError):
            performance_b.clean()

    def test_unique_subject_term_performance(self):
        """Test that the unique constraint for subject, term, and school works."""
        TermSubjectPerformance.objects.create(**self.term_performance_data)

        with self.assertRaises(ValidationError):
            TermSubjectPerformance.objects.create(**self.term_performance_data)

    def test_update_performance_metrics(self):
        """Test the update_performance_metrics function calculates stats correctly."""
        # Add student performances
        self.classroom.update_students([self.student_a.account_id, self.student_b.account_id, self.student_c.account_id]) # add students to the classroom

        self.assessment.collected = True # modify assessment collected field so we can release grades
        self.assessment.start_time = timezone.now() - timezone.timedelta(minutes=5)
        self.assessment.date_collected = timezone.now()
        self.assessment.save()

        if self.assessment.classroom and self.assessment.classroom.students.exists(): # mark all students in the classroom as submitted
            submissions = []
            transcripts = []
            for student in self.assessment.classroom.students.all():
                submissions.append(Submission(assessment=self.assessment, student=student, status='ON_TIME'))
                transcripts.append(Transcript(assessment=self.assessment, student=student, score=50, weighted_score=15, comment=''))

            batch_size = 50
            for i in range(0, len(submissions), batch_size):
                Submission.objects.bulk_create(submissions[i:i + batch_size])

            for i in range(0, len(transcripts), batch_size):
                Transcript.objects.bulk_create(transcripts[i:i + batch_size])

        self.assessment.release_grades()  # Should allow for releasing grades as all submissions have been graded
        self.assertTrue(self.assessment.grades_released)

        performance_a = TermSubjectPerformance.objects.get(term=self.assessment.term)

        self.assertEqual(performance_a.highest_score, 50.0)
        self.assertEqual(performance_a.lowest_score, 50.0)
        self.assertEqual(performance_a.average_score, 50.0)
        self.assertEqual(performance_a.pass_rate, 100.0)  # Assuming all students pass

    # def test_empty_data(self):
    #     """Test that empty data sets metrics to None."""
    #     term_performance = TermSubjectPerformance(**self.term_performance_data)
        
    #     term_performance.update_performance_metrics()
        
    #     self.assertIsNone(self.term_performance.pass_rate)
    #     self.assertIsNone(self.term_performance.average_score)

    # def test_single_student_score(self):
    #     """Test performance metrics with a single student's score."""
        
    #     self.term_performance.update_performance_metrics()
        
    #     self.assertEqual(self.term_performance.pass_rate, 100.0)
    #     self.assertEqual(self.term_performance.average_score, 70.0)

    # def test_top_performers(self):
    #     """Test that top performers are correctly set."""
    #     # Create performances for multiple students
    #     student_2 = Student.objects.create(name="Jane Doe", school=self.school)
        
    #     self.term_performance.update_performance_metrics()
        
    #     top_performers = self.term_performance.top_performers.all()
    #     self.assertEqual(top_performers.count(), 2)
    #     self.assertIn(self.student, top_performers)
    #     self.assertIn(student_2, top_performers)

