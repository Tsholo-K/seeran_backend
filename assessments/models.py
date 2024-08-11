# python 
import uuid

# django 
from django.db import models
from django.utils.translation import gettext_lazy as _

# models
from users.models import CustomUser
from classes.models import Classroom
from grades.models import Grade
from schools.models import School


class Assessment(models.Model):
    """
    Model to represent an assessment.

    Attributes:
        set_by (ForeignKey): The user who set the assessment.
        due_date (DateTimeField): The date and time when the assessment is due.
        total (IntegerField): The total score possible for the assessment.
        formal (BooleanField): Indicates if the assessment is formal.
        percentage_towards_term_mark (IntegerField): The percentage weight of the assessment towards the term mark.
        term (IntegerField): The term during which the assessment is given.
        students_assessed (ManyToManyField): The students who are assessed.
        collected (BooleanField): Indicates if the assessment has been collected from students.
        released (BooleanField): Indicates if the assessment results have been released.
        date_released (DateTimeField): The date and time when the assessment results were released.
        unique_identifier (CharField): A unique identifier for the assessment.
        moderator (ForeignKey): The user who moderated the assessment.
        classroom (ForeignKey): The classroom where the assessment was conducted.
        grade (ForeignKey): The grade to which the assessment belongs.
        school (ForeignKey): The school where the assessment was conducted.
        assessment_id (UUIDField): A unique identifier for the assessment.
    """

    # User who set the assessment
    set_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, related_name='assessments_set', null=True)

    # Date and time details
    due_date = models.DateTimeField()  # Allowed format: yyyy-mm-ddThh:mm
    total = models.IntegerField()  # Total score possible for the assessment
    formal = models.BooleanField(default=False)  # Indicates if the assessment is formal

    # Assessment details
    percentage_towards_term_mark = models.IntegerField()  # Percentage weight towards the term mark
    term = models.IntegerField()  # Term during which the assessment is given

    # Relationship fields
    students_assessed = models.ManyToManyField(CustomUser, related_name='assessments_taken')
    collected = models.BooleanField(default=False)  # Indicates if the assessment has been collected
    released = models.BooleanField(default=False)  # Indicates if the assessment results have been released
    date_released = models.DateTimeField()  # Date and time when results were released
    unique_identifier = models.CharField(max_length=15)  # Unique identifier for the assessment

    moderator = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, related_name='assessments_moderated', null=True)
    classroom = models.ForeignKey(Classroom, on_delete=models.SET_NULL, related_name='class_assessments', null=True, blank=True)
    grade = models.ForeignKey(Grade, on_delete=models.CASCADE, related_name='grade_assessments')
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='school_assessments')

    # Unique assessment ID
    assessment_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)

    class Meta:
        verbose_name = _('assessment')
        verbose_name_plural = _('assessments')
        unique_together = ['unique_identifier', 'grade', 'classroom']

    def __str__(self):
        return self.unique_identifier


class Transcript(models.Model):
    """
    Model to represent a student's transcript for a specific assessment.

    Attributes:
        student (ForeignKey): The student who received the score.
        score (IntegerField): The score the student received in the assessment.
        assessment (ForeignKey): The assessment for which the score is recorded.
        transcript_id (UUIDField): A unique identifier for the transcript.
    """

    # Relationship fields
    student = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='my_transcripts')
    score = models.IntegerField()  # The score received by the student
    assessment = models.ForeignKey(Assessment, on_delete=models.CASCADE, related_name='student_scores')

    # Unique transcript ID
    transcript_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)

    class Meta:
        verbose_name = _('transcript')
        verbose_name_plural = _('transcripts')

    def __str__(self):
        return f"{self.assessment.unique_identifier} - {self.student.username}"

