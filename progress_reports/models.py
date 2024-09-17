# python 
import uuid

# django 
from django.db import models, IntegrityError
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError

# models
from users.models import Student
from schools.models import School
from grades.models import Grade
from terms.models import Term
from subject_performances.models import StudentSubjectPerformance


class ProgressReport(models.Model):
    # The student whose report is being generated
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='reports')

    # The subject scores associated with this report
    subject_scores = models.ManyToManyField(StudentSubjectPerformance, related_name='report')
    # The academic term for which the report is for
    term = models.ForeignKey(Term, editable=False, on_delete=models.SET_NULL, related_name='reports', null=True)
    
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

    #The grade to which this score belongs
    grade = models.ForeignKey(Grade, on_delete=models.CASCADE, editable=False, related_name='progress_reports')

    # The school where the report is generated
    school = models.ForeignKey(School, on_delete=models.CASCADE, editable=False, related_name='term_reports')
    
    last_updated = models.DateTimeField(auto_now=True)

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

        self.clean()
        try:
            super().save(*args, **kwargs)
        except IntegrityError as e:
            if 'unique constraint' in str(e):
                raise IntegrityError(_('a student cannot have duplicate report cards for the same term. Consider regenerating a new report card for the term, which will discard the current one.'))
            else:
                raise

    def generate_subject_scores(self):
        """
        Get or create subject scores for each subject the student is enrolled in for the current term,
        and add these scores to the report's subject_scores field.
        """
        # Get the list of subjects the student is enrolled in
        subjects = self.student.enrolled_classes.values_list('subject', flat=True).distinct()
        
        # Create and collect SubjectScore instances for each subject
        subject_scores = []
        for subject in subjects:            
            # Get or create a SubjectScore instance
            subject_score, created = StudentSubjectScore.objects.get_or_create(student=self.student, term=self.term, subject=subject, defaults={'grade': self.grade, 'school': self.school})
            subject_score.determine_pass_status()

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
                total_subjects_weighted_score = 0
                total_terms_weight = 0

                # Calculate total weighted score for each subject across all terms
                terms = Term.objects.filter(start_date__year=self.term.start_date.year, school=self.school)
                for term in terms:
                    try:
                        # Get or create the student's subject score for the current term and subject
                        subject_score, created = StudentSubjectScore.objects.get_or_create(student=self.student, subject=subject, term=term, defaults={'grade': self.grade, 'school': self.school})
                        total_subjects_weighted_score += subject_score.weighted_score
                        total_terms_weight += term.weight
                    except StudentSubjectScore.DoesNotExist:
                        continue

                # Determine if the subject has been failed based on the aggregated weighted score
                if total_terms_weight > 0 and total_subjects_weighted_score / total_terms_weight < subject.pass_mark:
                    failed_subjects += 1
                    if subject.major_subject:
                        failed_major_subjects += 1
        else:
            for subject_score in self.subject_scores.all():
                if not subject_score.passed:
                    failed_subjects += 1
                    if subject_score.subject.major_subject:
                        failed_major_subjects += 1

        if failed_major_subjects > self.grade.major_subjects or failed_subjects >= self.grade.none_major_subjects:
            self.passed = False
        else:
            self.passed = True

    def calculate_days_absent(self):
        """
        Calculate the total number of days a student was absent during the term.
        """
        absences = self.student.attendance.filter(date__date__range=(self.term.start_date.date(), self.term.end_date.date())).values('date').distinct()
        self.days_absent = absences.count()

    def calculate_days_late(self):
        """
        Calculate the total number of days a student was late during the term.
        """
        # Assuming term has start_date and end_date fields
        late_arrivals = self.student.attendance.filter(late_students=self.student, date__date__range=(self.term.start_date.date(), self.term.end_date.date())).values('date').distinct()
        self.days_late = late_arrivals.count()

    def calculate_attendance_percentage(self):
        """
        Calculate the attendance percentage for this report based on days absent and total school days.
        """
        total_school_days = self.term.school_days
        if not total_school_days:
            self.term.calculate_total_school_days()
            self.term.save()
            total_school_days = self.term.school_days
        self.attendance_percentage = (1 - (self.days_absent / total_school_days)) * 100

