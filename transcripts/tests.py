from django.test import TestCase

# Create your tests here.
# class TranscriptTest(TestCase):
#     """
#     Test cases for the Transcript model.
#     """

#     def setUp(self):
#         """
#         Set up the test environment by creating necessary instances.
#         """
#         self.school = School.objects.create(
#             name="Test School",
#             email="testschool@example.com",
#             contact_number="1234567890",
#             type="PRIMARY",
#             province="GAUTENG",
#             district="JHB NORTH"
#         )
#         self.grade = Grade.objects.create(
#             grade='7',
#             major_subjects=1,
#             none_major_subjects=2,
#             school=self.school
#         )
#         self.term = Term.objects.create(
#             term=1,
#             start_date=timezone.now().date(),
#             end_date=timezone.now().date() + timedelta(days=30),
#             weight=20.00,
#             grade=self.grade,
#             school=self.school
#         )
#         self.subject = Subject.objects.create(
#             grade=self.grade,
#             subject='ENGLISH',
#             major_subject=True,
#             pass_mark=50.00
#         )
#         self.student = Student.objects.create_user(
#             name="John",
#             surname="Doe",
#             role="STUDENT",
#             school=self.school,
#             grade=self.grade,
#             passport_number='845751548'
#         )
#         self.assessment = Assessment.objects.create(
#             set_by=None,
#             title='Test Assessment',
#             total=100,
#             percentage_towards_term_mark=50.00,
#             term=self.term,
#             subject=self.subject,
#             grade=self.grade,
#             school=self.school,
#             due_date=timezone.now() + timezone.timedelta(days=10),
#             unique_identifier='TEST001'
#         )

#     def test_create_transcript(self):
#         """
#         Test the creation of a Transcript with valid data.
#         """
#         transcript = Transcript.objects.create(
#             student=self.student,
#             score=85.00,
#             assessment=self.assessment
#         )
#         self.assertEqual(transcript.score, 85.00)
#         self.assertEqual(transcript.student, self.student)

#     def test_score_validation(self):
#         """
#         Test validation of the score field to ensure it is within the valid range.
#         """
#         valid_transcript = Transcript(
#             student=self.student,
#             score=90.00,
#             assessment=self.assessment
#         )
#         valid_transcript.clean()  # Should not raise any validation error

#         # Test invalid score
#         invalid_transcript = Transcript(
#             student=self.student,
#             score=110.00,  # Exceeds the total score
#             assessment=self.assessment
#         )
#         with self.assertRaises(ValidationError):
#             invalid_transcript.clean()

#     def test_moderated_score_validation(self):
#         """
#         Test validation of the moderated_score field to ensure it is within the valid range.
#         """
#         transcript = Transcript.objects.create(
#             student=self.student,
#             score=85.00,
#             moderated_score=90.00,
#             assessment=self.assessment
#         )
#         self.assertEqual(transcript.moderated_score, 90.00)

#         # Test invalid moderated score
#         invalid_transcript = Transcript(
#             student=self.student,
#             score=85.00,
#             moderated_score=110.00,  # Exceeds the total score
#             assessment=self.assessment
#         )
#         with self.assertRaises(ValidationError):
#             invalid_transcript.clean()