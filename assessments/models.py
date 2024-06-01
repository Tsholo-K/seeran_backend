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

    percentage_towards_term_mark = models.IntegerField()
    term = models.IntegerField()

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
        return self.unique_identifier

    # assessment id creation handler
    def save(self, *args, **kwargs):
        if not self.assessment_id:
            self.assessment_id = self.generate_unique_id('AS')

        super(Assessment, self).save(*args, **kwargs)

    @staticmethod
    def generate_unique_id(prefix=''):
        max_attempts = 10
    
        for _ in range(max_attempts):
            unique_part = uuid.uuid4().hex[:13]  # Take only the first 13 characters
            id = f"{prefix}{unique_part}"
            if not Assessment.objects.filter(assessment_id=id).exists():
                return id
   
        raise ValueError('failed to generate a unique account ID after 10 attempts, please try again later.')


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
        return self.assessment

    # transcript id creation handler
    def save(self, *args, **kwargs):
        if not self.transcript_id:
            self.transcript_id = self.generate_unique_id('TR')

        super(Transcript, self).save(*args, **kwargs)

    @staticmethod
    def generate_unique_id(prefix=''):
        max_attempts = 10
      
        for _ in range(max_attempts):
            unique_part = uuid.uuid4().hex[:13]  # Take only the first 13 characters
            id = f"{prefix}{unique_part}"
            if not Transcript.objects.filter(transcript_id=id).exists():
                return id
     
        raise ValueError('failed to generate a unique account ID after 10 attempts, please try again later.')

