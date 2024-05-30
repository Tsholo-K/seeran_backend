# python 
import uuid

# django 
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.db import IntegrityError

# models
from users.models import CustomUser
from classes.models import Classroom
from grades.models import Grade
from schools.models import School


class Assessment(models.Model):

    set_by = models.ForeignKey(CustomUser, on_delete=models.DO_NOTHING, related_name='assessments_set')

    due_date = models.DateTimeField() # allowed format yyyy-m-ddThh:mm
    total = models.IntegerField()
    formal = models.BooleanField(default=False)

    percentage_towards_term_mark = models.IntegerField(max_length=3)
    term = models.IntegerField(max_length=1)

    students_assessed = models.ManyToManyField(CustomUser)

    collected = models.BooleanField(default=False)

    released = models.BooleanField(default=False)
    date_released = models.DateTimeField()

    unique_identifier = models.CharField(max_length=15)

    moderator = models.ForeignKey(CustomUser, on_delete=models.DO_NOTHING, related_name='assessments_moderated')

    classroom = models.ForeignKey(Classroom, on_delete=models.CASCADE, related_name='class_assessments', null=True, blank=True)
    grade = models.ForeignKey(Grade, on_delete=models.CASCADE, related_name='grade_assessments')

    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='school_assessments')

    # assessment id 
    assessment_id = models.CharField(max_length=15, unique=True)  

    class Meta:
        verbose_name = _('assessment')
        verbose_name_plural = _('assessments')

    def __str__(self):
        return self.name

    # assessment id creation handler
    def save(self, *args, **kwargs):
        if not self.assessment_id:
            self.assessment_id = self.generate_unique_account_id('AS')

        attempts = 0
        while attempts < 5:
            try:
                super().save(*args, **kwargs)
                break
            except IntegrityError:
                self.assessment_id = self.generate_unique_account_id('AS') # Assessment
                attempts += 1
        if attempts >= 5:
            raise ValueError('Could not create school with unique account ID after 5 attempts. Please try again later.')

    @staticmethod
    def generate_unique_account_id(prefix=''):
        while True:
            unique_part = uuid.uuid4().hex
            account_id = prefix + unique_part
            account_id = account_id[:15].ljust(15, '0')

            if not Assessment.objects.filter(assessment_id=account_id).exists():
                return account_id


class Transcript(models.Model):

    student = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='my_transcripts')
    score = models.IntegerField()
    assessment = models.ForeignKey(Assessment, on_delete=models.CASCADE, related_name='student_scores')

    # transcript id 
    transcript_id = models.CharField(max_length=15, unique=True)  

    class Meta:
        verbose_name = _('transcript')
        verbose_name_plural = _('transcripts')

    def __str__(self):
        return self.name

    # transcript id creation handler
    def save(self, *args, **kwargs):
        if not self.transcript_id:
            self.transcript_id = self.generate_unique_account_id('TR')

        attempts = 0
        while attempts < 5:
            try:
                super().save(*args, **kwargs)
                break
            except IntegrityError:
                self.transcript_id = self.generate_unique_account_id('TR') # Assessment
                attempts += 1
        if attempts >= 5:
            raise ValueError('Could not create transcript with unique account ID after 5 attempts. Please try again later.')

    @staticmethod
    def generate_unique_account_id(prefix=''):
        while True:
            unique_part = uuid.uuid4().hex
            account_id = prefix + unique_part
            account_id = account_id[:15].ljust(15, '0')

            if not Assessment.objects.filter(transcript_id=account_id).exists():
                return account_id

