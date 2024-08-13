# python 
from datetime import date, timedelta

# djnago
from django.test import TestCase
from django.core.exceptions import ValidationError
from django.utils import timezone

# models
from .models import Term, School


class SchoolModelTest(TestCase):
    def setUp(self):
        self.school = School.objects.create(
            name="Test School",
            email="testschool@example.com",
            contact_number="1234567890",
            school_type="PRIMARY",
            province="GAUTENG",
            school_district="District 1"
        )

    def test_school_creation(self):
        self.assertEqual(School.objects.count(), 1)
        self.assertEqual(self.school.name, "Test School")
        self.assertEqual(self.school.email, "testschool@example.com")

    def test_contact_number_validation(self):
        with self.assertRaises(ValidationError):
            self.school.contact_number = "123ABC"
            self.school.clean()  # This should raise ValidationError

    def test_logo_validation(self):
        with self.assertRaises(ValidationError):
            self.school.logo = 'path/to/logo.txt'  # Invalid extension
            self.school.clean()  # This should raise ValidationError

    def test_default_values(self):
        self.assertFalse(self.school.in_arrears)
        self.assertFalse(self.school.none_compliant)

    def test_school_update(self):
        self.school.name = "Updated School"
        self.school.save()
        self.assertEqual(School.objects.get(pk=self.school.pk).name, "Updated School")

    def test_invalid_email(self):
        with self.assertRaises(ValidationError):
            self.school.email = "invalidemail"
            self.school.clean()  # This should raise ValidationError

    def test_school_motto_empty(self):
        self.assertEqual(self.school.school_motto, None)

    def test_unique_school_id(self):
        school_2 = School.objects.create(
            name="Another Test School",
            email="another@example.com",
            contact_number="0987654321",
            school_type="PRIMARY",
            province="GAUTENG",
            school_district="District 2"
        )
        self.assertNotEqual(self.school.school_id, school_2.school_id)

    def test_school_accreditation_field(self):
        self.school.accreditation = "Department of Education"
        self.school.save()
        self.assertEqual(self.school.accreditation, "Department of Education")

    def test_school_field_defaults(self):
        self.assertEqual(self.school.school_type, "PRIMARY")
        self.assertEqual(self.school.province, "GAUTENG")


class TermModelTest(TestCase):
    def setUp(self):
        self.school = School.objects.create(
            name="Test School",
            email="testschool@example.com",
            contact_number="1234567890",
            school_type="PRIMARY",
            province="GAUTENG",
            school_district="District 1"
        )
        self.term = Term.objects.create(
            term=1,
            weight=30.00,
            start_date=timezone.now().date(),
            end_date=timezone.now().date() + timedelta(days=60),
            school=self.school
        )

    def test_term_creation(self):
        self.assertEqual(Term.objects.count(), 1)
        self.assertEqual(self.term.term, 1)
        self.assertEqual(self.term.weight, 30.00)

    def test_term_start_date_before_end_date(self):
        with self.assertRaises(ValidationError):
            self.term.start_date = timezone.now().date() + timedelta(days=61)
            self.term.end_date = timezone.now().date() + timedelta(days=60)
            self.term.clean()  # This should raise ValidationError

    def test_term_overlapping_dates(self):
        overlapping_term = Term(
            term=2,
            weight=20.00,
            start_date=self.term.start_date + timedelta(days=15),
            end_date=self.term.end_date + timedelta(days=15),
            school=self.school
        )
        with self.assertRaises(ValidationError):
            overlapping_term.clean()  # This should raise ValidationError

    def test_term_weight_exceeding_100(self):
        term_2 = Term.objects.create(
            term=2,
            weight=60.00,
            start_date=timezone.now().date() + timedelta(days=61),
            end_date=timezone.now().date() + timedelta(days=120),
            school=self.school
        )
        with self.assertRaises(ValidationError):
            term_2.weight = 80.00
            term_2.clean()  # This should raise ValidationError

    def test_term_school_days_calculation(self):
        self.assertEqual(self.term.school_days, 44)  # Assuming there are 44 weekdays in a 60-day period

    def test_term_update(self):
        self.term.term = 2
        self.term.save()
        self.assertEqual(Term.objects.get(pk=self.term.pk).term, 2)

    def test_term_unique_constraint(self):
        with self.assertRaises(ValidationError):
            duplicate_term = Term(
                term=1,
                weight=25.00,
                start_date=self.term.start_date + timedelta(days=120),
                end_date=self.term.end_date + timedelta(days=180),
                school=self.school
            )
            duplicate_term.clean()  # This should raise ValidationError

    def test_term_id_is_unique(self):
        term_2 = Term.objects.create(
            term=2,
            weight=50.00,
            start_date=timezone.now().date() + timedelta(days=61),
            end_date=timezone.now().date() + timedelta(days=120),
            school=self.school
        )
        self.assertNotEqual(self.term.term_id, term_2.term_id)

