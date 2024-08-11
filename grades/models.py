# python 
import uuid

# django 
from django.db import models
from django.utils.translation import gettext_lazy as _

# models
from schools.models import School

class Grade(models.Model):

    # grade choices
    SCHOOL_GRADES_CHOICES = [('000', 'Grade 000'), ('00', 'Grade 00'), ('R', 'Grade R'), ('1', 'Grade 1'), ('2', 'Grade 2'), ('3', 'Grade 3'), ('4', 'Grade 4'), ('5', 'Grade 5'), ('6', 'Grade 6'), ('7', 'Grade 7'), ('8', 'Grade 8'), ('9', 'Grade 9'), ('10', 'Grade 10'), ('11', 'Grade 11'), ('12', 'Grade 12')]
    grade = models.CharField(_('school grade'), choices=SCHOOL_GRADES_CHOICES, max_length=4, default="8")
    grade_order = models.PositiveIntegerField()

    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='school_grades')

    # grade  id 
    grade_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)

    class Meta:
        verbose_name = _('grade')
        verbose_name_plural = _('grades')
        unique_together = ('school', 'grade') # this will prevent the creation of duplicate grades within the same school
        ordering = ['grade_order']
        
    def __str__(self):
        return self.grade_id
            

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
        ('BUSINESS STUDIES', 'Business Studies'),
        ('AGRICULTURE', 'Agriculture'),
        ('TOURISM', 'Tourism'),
        ('LIFE ORIENTATION', 'Life Orientation'),
        ('SOCIAL SCIENCE', 'Social Science'),
        ('ARTS AND CULTURE', 'Arts And Culture'),
    ]
    subject = models.CharField(_('grade subject'), max_length=100, choices=SCHOOL_SUBJECTS_CHOICES, default="ENGLISH")

    # class account id 
    subject_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)

    class Meta:
        verbose_name = _('subject')
        verbose_name_plural = _('subjects')
        unique_together = ('grade', 'subject') # this will prevent the creation of duplicate subjects within the same grade

    def __str__(self):
        return self.subject
