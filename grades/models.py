# python 
import uuid

# django 
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.db import IntegrityError

# models
from schools.models import School


class Grade(models.Model):

    grade = models.CharField(_('school grade'), max_length=2)
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='school_grades')

    # grade  id 
    grade_id = models.CharField(max_length=15, unique=True)

    class Meta:
        verbose_name = _('grade')
        verbose_name_plural = _('grades')

    def __str__(self):
        return self.name

    # grade id creation handler
    def save(self, *args, **kwargs):
        if not self.grade_id:
            self.grade_id = self.generate_unique_account_id('GR')

        attempts = 0
        while attempts < 5:
            try:
                super().save(*args, **kwargs)
                break
            except IntegrityError:
                self.grade_id = self.generate_unique_account_id('GR') # Grade
                attempts += 1
        if attempts >= 5:
            raise ValueError('Could not create grade with unique account ID after 5 attempts. Please try again later.')

    @staticmethod
    def generate_unique_account_id(prefix=''):
        while True:
            unique_part = uuid.uuid4().hex
            account_id = prefix + unique_part
            account_id = account_id[:15].ljust(15, '0')

            if not Grade.objects.filter(grade_id=account_id).exists():
                return account_id
            

class Subject(models.Model):

    grade = models.ForeignKey(Grade, on_delete=models.CASCADE, related_name='grade_subjects')

    # subject choices
    SCHOOL_SUBJECTS_CHOICES = [
        ('ENGLISH', 'English'),
        ('SEPEDI', 'Sepedi'),
        ('ZULU', 'Zulu'),
        ('AFRIKAANS', 'Afrikaans'),
        ('MATHEMATICS', 'Mathematics'),
        ('MATHEMATICS LITERACY', 'Mathematics Literacy'),
        ('TECHNICAL MATHEMATICS', 'Technical Mathematics'),
        ('PHYSICAL SCIENCE', 'Physical Science'),
        ('LIFE SCIENCE', 'Life Science'),
        ('BIOLOGY', 'Biology'),
        ('GEOGRAPHY', 'Geography'),
        ('ACCOUNTING', 'Accounting'),
        ('TOURISM', 'Tourism'),
        ('LIFE ORIENTATION', 'Life Orientation'),
        ('SOCIAL SCIENCE', 'Social Science'),
        ('ARTS AND CULTURE', 'Arts And Culture'),
    ]
    subject = models.CharField(_('grade subject'), max_length=100, choices=SCHOOL_SUBJECTS_CHOICES, default="")  # School subjects

    # class account id 
    subject_id = models.CharField(max_length=15, unique=True)

    class Meta:
        verbose_name = _('subject')
        verbose_name_plural = _('subjects')

    def __str__(self):
        return self.name

    # class account id creation handler
    def save(self, *args, **kwargs):
        if not self.subject_id:
            self.subject_id = self.generate_unique_account_id('SB')

        attempts = 0
        while attempts < 5:
            try:
                super().save(*args, **kwargs)
                break
            except IntegrityError:
                self.subject_id = self.generate_unique_account_id('SB') # Class Room
                attempts += 1
        if attempts >= 5:
            raise ValueError('Could not create grade with unique account ID after 5 attempts. Please try again later.')

    @staticmethod
    def generate_unique_account_id(prefix=''):
        while True:
            unique_part = uuid.uuid4().hex
            account_id = prefix + unique_part
            account_id = account_id[:15].ljust(15, '0')

            if not Subject.objects.filter(subject_id=account_id).exists():
                return account_id