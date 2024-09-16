# python 
import uuid
# import logging

# django 
from django.db import models, IntegrityError
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError

# logging
# logger = logging.getLogger(__name__)

# models
from users.models import Student
from schools.models import School
from grades.models import Grade
from terms.models import Term
from subjects.models import Subject


class StudentSubjectScore(models.Model):
    # The student whose score is being recorded
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='subject_scores')

    # The score the student achieved in the subject
    score = models.DecimalField(max_digits=5, decimal_places=2)
    # the weighted score the student acheived for this subject in the given term
    weighted_score = models.DecimalField(max_digits=5, decimal_places=2)

    # field to indicate if the student passed the subject for the specified term
    passed = models.BooleanField(default=False)
    # The academic term for which this score applies
    term = models.ForeignKey(Term, editable=False, on_delete=models.CASCADE, related_name='scores')

    # The subject for which the score is recorded
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, editable=False, related_name='student_scores')

    #The grade to which this score belongs
    grade = models.ForeignKey(Grade, on_delete=models.CASCADE, editable=False, related_name='grade_subject_scores')
    # The school where the assessment was conducted
    school = models.ForeignKey(School, on_delete=models.CASCADE, editable=False, related_name='school_subject_scores')
    
    last_updated = models.DateTimeField(auto_now=True)

    # subject score id
    student_score_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)

    class Meta:
        unique_together = ('student', 'subject', 'term', 'school')

    def __str__(self):
        return f"{self.subject} - {self.student} - Term {self.term}"
    
    def clean(self):
        """
        Ensure that score and weighted_score are within valid ranges.
        """
        if not (0 <= self.score <= 100):
            raise ValidationError(_('students subject score for any given term must be between 0 and 100'))
        if not (0 <= self.weighted_score <= 100):
            raise ValidationError(_('a students subject weighted score for any given term must be between 0 and 100'))
        
    def save(self, *args, **kwargs):
        if not self.pk:
            self.calculate_scores()

        self.clean()
        try:
            super().save(*args, **kwargs)
        except IntegrityError as e:
            if 'unique constraint' in str(e):
                raise IntegrityError(_('a student can not have dupliate subject scores for the same subject in the same term, concider regenerating new subject scores for the term which will discard the current ones'))
            else:
                raise

    def calculate_scores(self):
        """
        Calculate the score and weighted score the student acheived for this subject in the given term, using the moderated_score if provided.
        """
        score = 0
        assessments = self.student.assessements.filter(subject=self.subject, term=self.term, formal=True, grades_released=True)
        
        if not assessments.exists():
            score = 0
    
        else:
            for assessment in assessments:
                transcript = self.student.transcripts.filter(assessment=assessment)
                if not transcript:
                    continue

                weight = assessment.percentage_towards_term_mark / 100
                score += transcript.moderated_score * weight if transcript.moderated_score else transcript.score * weight

        self.score = score

        if self.score and self.score > 0:
            term_weight = float(self.term.weight) / 100
            self.weighted_score = float(self.score) * term_weight

    def determine_pass_status(self):
        if self.score:
            if self.score > self.subject.pass_mark:
                self.passed = True
            else:
                self.passed = False


class TermSubjectScore(models.Model):
    # The academic term for which this score applies
    term = models.ForeignKey(Term, editable=False, on_delete=models.CASCADE, related_name='performances')

    pass_rate = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    average_score = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)

    students_failing_the_class = models.ManyToManyField(Student, related_name='failing_terms', help_text='Students who are failing the term.')

    # The subject for which the score is recorded
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, editable=False, related_name='subject_termly_performances')

    # The school where the assessment was conducted
    school = models.ForeignKey(School, on_delete=models.CASCADE, editable=False, related_name='school_termly_subject_performances')
    
    last_updated = models.DateTimeField(auto_now=True)

    # subject score id
    term_score_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)

    class Meta:
        unique_together = ('subject', 'term', 'school')

    def __str__(self):
        return f"{self.subject} - Term {self.term}"
    
    def clean(self):
        """
        Ensure that score and weighted_score are within valid ranges.
        """
        if not (0 <= self.score <= 100):
            raise ValidationError(_('students subject score for any given term must be between 0 and 100'))
        if not (0 <= self.weighted_score <= 100):
            raise ValidationError(_('a students subject weighted score for any given term must be between 0 and 100'))
        
    def save(self, *args, **kwargs):
        if not self.pk:
            self.calculate_scores()

        self.clean()
        try:
            super().save(*args, **kwargs)
        except IntegrityError as e:
            if 'unique constraint' in str(e):
                raise IntegrityError(_('a student can not have dupliate subject scores for the same subject in the same term, concider regenerating new subject scores for the term which will discard the current ones'))
            else:
                raise

    def calculate_scores(self):
        """
        Calculate the score and weighted score the student acheived for this subject in the given term, using the moderated_score if provided.
        """
        score = 0
        assessments = self.student.assessements.filter(subject=self.subject, term=self.term, formal=True, grades_released=True)
        
        if not assessments.exists():
            score = 0
    
        else:
            for assessment in assessments:
                transcript = self.student.transcripts.filter(assessment=assessment)
                if not transcript:
                    continue

                weight = assessment.percentage_towards_term_mark / 100
                score += transcript.moderated_score * weight if transcript.moderated_score else transcript.score * weight

        self.score = score

        if self.score and self.score > 0:
            term_weight = float(self.term.weight) / 100
            self.weighted_score = float(self.score) * term_weight
