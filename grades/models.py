# python 
import uuid

# django 
from django.db import models
from django.utils.translation import gettext_lazy as _

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
            self.grade_id = self.generate_unique_id('GR')

        super(Grade, self).save(*args, **kwargs)

    @staticmethod
    def generate_unique_id(prefix=''):
        max_attempts = 10
        for _ in range(max_attempts):
            unique_part = uuid.uuid4().hex[:13]  # Take only the first 13 characters
            id = f"{prefix}{unique_part}"
            if not Grade.objects.filter(grade_id=id).exists():
                return id
        raise ValueError('failed to generate a unique grade ID after 10 attempts, please try again later.')
            

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
        return self.subject

    # class account id creation handler
    def save(self, *args, **kwargs):
        if not self.subject_id:
            self.subject_id = self.generate_unique_id('SB')

        super(Subject, self).save(*args, **kwargs)

    @staticmethod
    def generate_unique_id(prefix=''):
        max_attempts = 10
        for _ in range(max_attempts):
            unique_part = uuid.uuid4().hex[:13]  # Take only the first 13 characters
            id = f"{prefix}{unique_part}"
            if not Subject.objects.filter(subject_id=id).exists():
                return id
        raise ValueError('failed to generate a unique subject ID after 10 attempts, please try again later.')