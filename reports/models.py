# python 
import uuid

# django 
from django.db import models, IntegrityError
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError

# models
from users.models import CustomUser
from schools.models import School, Term
from grades.models import Grade, Subject
from assessments.models import Assessment, Transcript
from attendances.models import Absent, Late


class StudentSubjectScore(models.Model):
    """
    Model to represent the score a student has achieved in a specific subject during a term.
    """
    # The student whose score is being recorded
    student = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='subject_scores')

    # field to indicate if the student passed the subject for the specified term
    passed = models.BooleanField(default=False)
    # The academic term for which this score applies
    term = models.ForeignKey(Term, on_delete=models.CASCADE, related_name='scores')

    # The score the student achieved in the subject
    score = models.DecimalField(max_digits=5, decimal_places=2)
    # the weighted score the student acheived for this subject in the given term
    weighted_score = models.DecimalField(max_digits=5, decimal_places=2)

    # The subject for which the score is recorded
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='student_scores')

    #The grade to which this score belongs
    grade = models.ForeignKey(Grade, on_delete=models.CASCADE, related_name='grade_subject_scores')
    # The school where the assessment was conducted
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='school_subject_scores')

    # subject score id
    score_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)

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
            if StudentSubjectScore.objects.filter(student=self.student, term=self.term, school=self.school, subject=self.subject).exists():
                raise IntegrityError(_('a student can not have dupliate subject scores for the same subject in the same term, concider regenerating new subject scores for the term which will discard the current ones'))

        if self.score is None or self.weighted_score is None:
            self.calculate_term_score()
            self.calculate_weighted_score()

            self.passed = self.score >= self.subject.pass_mark

        self.clean()
        super().save(*args, **kwargs)

    def calculate_term_score(self):
        """
        Calculate the score the student acheived for this subject in the given term, using the moderated_score if provided.
        """
        total_score = 0
        assessments = Assessment.objects.filter(subject=self.subject, term=self.term, formal=True)
        
        if not assessments.exists():
            self.score = 0
            return
    
        for assessment in assessments:
            try:
                transcript = Transcript.objects.get(student=self.student, assessment=assessment)
                weight = assessment.percentage_towards_term_mark / 100
                total_score += transcript.moderated_score * weight if transcript.moderated_score else transcript.score * weight
            except Transcript.DoesNotExist:
                continue

        self.score = total_score

    def calculate_weighted_score(self):
        """
        Calculate the weighted score the student acheived for this subject in the specified term.
        """
        term_weight = float(self.term.weight) / 100
        self.weighted_score = float(self.score) * term_weight


class ReportCard(models.Model):
    """
    Model to represent a student's report card for a specific term.
    """
    # The student whose report is being generated
    student = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='term_reports')

    # The subject scores associated with this report
    subject_scores = models.ManyToManyField(StudentSubjectScore, related_name='reports')
    # The academic term for which the report is for
    term = models.ForeignKey(Term, on_delete=models.SET_NULL, related_name='reports', null=True)
    
    # The total number of days the student was absent
    days_absent = models.IntegerField(default=0)
    # The total number of days the student was late
    days_late = models.IntegerField(default=0)

    # The percentage of school days the student attended
    attendance_percentage = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)

    # Whether the student passed the term based on their subject scores
    passed = models.BooleanField(default=False)

    # Indicates whether this is the year-end report
    year_end_report = models.BooleanField(default=False)

    # The school where the report is generated
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='term_reports')

    # report card id
    report_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)

    class Meta:
        unique_together = ('student', 'term', 'school')
        ordering = ['-term__start_date']
        indexes = [models.Index(fields=['student', 'term', 'school'])]  # Index for performance

    def __str__(self):
        return f"Report - {self.student} - Term {self.term}"

    def clean(self):
        """
        Ensure attendance and pass status calculations are accurate.
        """
        if self.attendance_percentage is not None and not (0 <= self.attendance_percentage <= 100):
            raise ValidationError(_('a studends attendance percentage must be between 0 and 100 for any given term'))

    def save(self, *args, **kwargs):
        """
        Override save method to calculate total_score, attendance_percentage,
        and year_end_score if applicable, before saving the report.
        """
        if not self.pk:
            if ReportCard.objects.filter(student=self.student, term=self.term, school=self.school).exists():
                raise IntegrityError(_('a student cannot have duplicate report cards for the same term. Consider regenerating a new report card for the term, which will discard the current one.'))

        # self.generate_subject_scores()
        # self.determine_pass_status()
        # self.calculate_days_absent()
        # self.calculate_days_late()
        # self.calculate_attendance_percentage()

        self.clean()
        super().save(*args, **kwargs)

    def generate_subject_scores(self):
        """
        Create subject scores for each subject the student is enrolled in for the current term,
        and add these scores to the report's subject_scores field.
        """
        # Get the list of subjects the student is enrolled in
        subjects = self.student.enrolled_classes.values_list('subject', flat=True).distinct()
        
        # Create and collect SubjectScore instances for each subject
        subject_scores = []
        for subject in subjects:
            # Ensure that `subject` is a Subject instance
            subject_instance = Subject.objects.get(id=subject)
            
            # Get or create a SubjectScore instance
            subject_score, created = StudentSubjectScore.objects.get_or_create(
                student=self.student,
                term=self.term,
                subject=subject_instance,
                defaults={'grade': self.student.grade, 'school': self.student.school}
            )
            
            # Collect the created or existing SubjectScore instance
            subject_scores.append(subject_score)
        
        # Add the generated SubjectScore instances to the report's subject_scores field
        self.subject_scores.set(subject_scores)


    def determine_pass_status(self):
        """
        Determine if the student has passed the term based on their subject scores and pass mark.
        If it's a year-end report, consider all terms in the current academic year.
        """
        failed_subjects = 0
        failed_major_subjects = 0

        if self.year_end_report:
            # Get all subjects the student is enrolled in
            subjects = self.student.enrolled_classes.values_list('subject', flat=True).distinct()

            for subject in subjects:
                total_weighted_score = 0
                total_weight = 0

                # Calculate total weighted score for each subject across all terms
                terms = Term.objects.filter(start_date__year=self.term.start_date.year, school=self.school)
                for term in terms:
                    try:
                        subject_score = StudentSubjectScore.objects.get(student=self.student, term=term, subject=subject)
                        total_weighted_score += subject_score.weighted_score
                        total_weight += term.weight
                    except StudentSubjectScore.DoesNotExist:
                        continue

                # Determine if the subject has been failed based on the aggregated weighted score
                if total_weight > 0 and total_weighted_score / total_weight < subject.pass_mark:
                    failed_subjects += 1
                    if subject.major_subject:
                        failed_major_subjects += 1
        else:
            for subject_score in self.subject_scores.all():
                if not subject_score.passed:
                    failed_subjects += 1
                    if subject_score.subject.major_subject:
                        failed_major_subjects += 1

        if failed_major_subjects > 0 or failed_subjects >= 2:
            self.passed = False
        else:
            self.passed = True

    def calculate_days_absent(self):
        """
        Calculate the total number of days a student was absent during the term.
        """
        absences = Absent.objects.filter(absent_students=self.student, date__date__range=(self.term.start_date.date(), self.term.end_date.date())).values('date').distinct()
        self.days_absent = absences.count()

    def calculate_days_late(self):
        """
        Calculate the total number of days a student was late during the term.
        """
        # Assuming term has start_date and end_date fields
        late_arrivals = Late.objects.filter(late_students=self.student, date__date__range=(self.term.start_date.date(), self.term.end_date.date())).values('date').distinct()
        self.days_late = late_arrivals.count()

    def calculate_attendance_percentage(self):
        """
        Calculate the attendance percentage for this report based on days absent and total school days.
        """
        total_school_days = self.term.school_days
        if total_school_days > 0:
            self.attendance_percentage = (1 - (self.days_absent / total_school_days)) * 100
        else:
            self.attendance_percentage = 0

