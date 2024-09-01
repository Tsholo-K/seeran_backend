# python 
import uuid
from django.utils import timezone
import datetime

# django 
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError

# models
from users.models import BaseUser, Student
from classes.models import Classroom
from grades.models import Grade
from terms.models import Term
from subjects.models import Subject
from schools.models import School


class Topic(models.Model):
    name = models.CharField(max_length=124, unique=True)

    def __str__(self):
        return self.name
    
class Assessment(models.Model):
    """
    Model to represent an assessment.
    """
    title = models.CharField(max_length=124)
    topics = models.ManyToManyField(Topic, related_name='assessments')
    
    # The user who set the assessment
    set_by = models.ForeignKey(BaseUser, on_delete=models.SET_NULL, related_name='assessments_set', null=True)

    # Total score possible for the assessment
    total = models.IntegerField()

    # Indicates if the assessment is formal
    formal = models.BooleanField(default=False)
    # Percentage weight towards the term mark
    percentage_towards_term_mark = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)

    # Term during which the assessment is given
    term = models.ForeignKey(Term, on_delete=models.CASCADE)
    
    # The students who are assessed
    students_assessed = models.ManyToManyField(Student, related_name='assessments_taken')
    # the students who submitted the assessment before the due date elapsed
    ontime_submission = models.ManyToManyField(Student, related_name='ontime_submissions', blank=True)
    # the students who submitted the assessment after the due date elapsed
    late_submission = models.ManyToManyField(Student, related_name='late_submissions', blank=True)

    # the students who have been allowed to retake the assessment after the due date elapsed
    retake_submission = models.ManyToManyField(Student, related_name='retake_submissions', blank=True)

    # Indicates if the assessment has been collected
    collected = models.BooleanField(default=False)
    # Date and time when the assessment was collected
    date_collected = models.DateTimeField(null=True, blank=True)

    # Indicates if the assessment results have been released
    released = models.BooleanField(default=False)
    # Date and time when results were released
    date_released = models.DateTimeField(null=True, blank=True)

    # The user who moderated the assessment
    moderator = models.ForeignKey(BaseUser, on_delete=models.SET_NULL, related_name='assessments_moderated', null=True)
    # The classroom where the assessment was conducted
    classroom = models.ForeignKey(Classroom, on_delete=models.SET_NULL, related_name='class_assessments', null=True, blank=True)

    # the subject the assessment is for
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='subject_assessments')
    # the grade the assessment is for
    grade = models.ForeignKey(Grade, on_delete=models.CASCADE, related_name='grade_assessments')
    # The school where the assessment was conducted
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='school_assessments')

    # The date and time when the assessment is due
    due_date = models.DateTimeField()  # Allowed format: yyyy-mm-ddThh:mm

    # Unique identifier for the assessment
    unique_identifier = models.CharField(max_length=15)
    # Type of the assessment (e.g., practical, exam, test)
    assessment_type = models.CharField(max_length=124, default='EXAMINATION')

    # assessment id 
    assessment_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)

    class Meta:
        unique_together = ('unique_identifier', 'grade', 'classroom')
        ordering = ['-due_date']
        indexes = [models.Index(fields=['title', 'due_date', 'subject', 'grade', 'school'])]  # Index for performance

    def __str__(self):
        return self.unique_identifier

    def clean(self):
        
        super().clean()

        if self.set_by and self.set_by.role not in ['PRINCIPAL', 'ADMIN', 'TEACHER']:
            raise ValidationError('Submitted by user must be an Admin or Teacher.')

        # Convert self.due_date to datetime if it's a date object
        if isinstance(self.due_date, datetime.date) and not isinstance(self.due_date, datetime.datetime):
            due_date_datetime = timezone.make_aware(datetime.datetime.combine(self.due_date, datetime.time.min))
        else:
            due_date_datetime = self.due_date

        # Compare with the current datetime
        if due_date_datetime < timezone.now():
            raise ValidationError('an assessments due date must be in the future')
        
        if self.date_released and self.date_released < self.due_date:
            raise ValidationError('an assessments date released cannot be before its due date')

        total_percentage = self.term.assessment_set.aggregate(total_percentage=models.Sum('percentage_towards_term_mark'))['total_percentage'] or 0
        
        if self.percentage_towards_term_mark is None:
            self.percentage_towards_term_mark = 0.00

        if float(total_percentage) + self.percentage_towards_term_mark > 100.00:
            raise ValidationError('the total percentage towards the term of all assessments in a term cannot exceed 100%')
        
        if not (0.00 <= self.percentage_towards_term_mark <= 100.00):
            raise ValidationError('percentage towards term mark for an given assessment must be between 0 and 100')
        
    def save(self, *args, **kwargs):
        """
        Override save method to validate incoming data
        """
        self.clean()

        try:
            super().save(*args, **kwargs)
        except Exception as e:
            raise ValidationError(_(str(e).lower()))

    def mark_as_collected(self, submitted_students_list=None):
        """
        Mark the assessment as collected and manage submissions and late submissions.
        """
        # Move students who submitted the assessment from students_assessed to ontime_submission
        self.ontime_submission.set(submitted_students_list)

        # Find students who haven't submitted and move them to late_submission
        non_submitted_students = self.students_assessed.exclude(id__in=submitted_students_list)
        self.late_submission.set(non_submitted_students)

        self.collected =True
        self.date_collected = timezone.now()

    def mark_as_released(self):
        """
        Mark the assessment as released and assign zero scores to students who did not submit.
        """
        if not self.collected:
            raise ValidationError('assessment must be collected before it can be released.')
        
        # Get the list of students who haven't submitted
        students_to_assign_zero = self.students_assessed.exclude(id__in=self.ontime_submission.values_list('id', flat=True))
        
        # Assign zero score to these students
        for student in students_to_assign_zero:
            Transcript.objects.update_or_create(student=student, assessment=self, defaults={'score': 0})
            
    def set_topics(self, topic_names):
        """
        Set topics for the assessment. Creates new topics if they don't exist.
        """
        topics = []
        for name in topic_names:
            topic, _ = Topic.objects.get_or_create(name=name)
            topics.append(topic)

        self.topics.set(topics)  # Replace the current topics with the new list

