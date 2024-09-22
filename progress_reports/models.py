# python 
import uuid

# django 
from django.db import models, IntegrityError
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from django.apps import apps

# models
from users.models import Student
from schools.models import School
from grades.models import Grade
from terms.models import Term
from student_subject_performances.models import StudentSubjectPerformance


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
    school = models.ForeignKey(School, on_delete=models.CASCADE, editable=False, related_name='progress_reports')
    
    last_updated = models.DateTimeField(auto_now=True)

    # report card id
    report_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['student', 'term', 'grade', 'school'], name='unique_student_term_grade_progress_report')
        ]
        ordering = ['-term__start_date']
        indexes = [models.Index(fields=['student', 'term', 'school'])]

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
            if 'unique_student_term_grade_progress_report' in str(e):
                raise IntegrityError(_('a student cannot have duplicate report cards for the same term. Consider regenerating a new report card for the term, which will discard the current one.'))
            else:
                raise

    def generate_progress_report(self):
        failed_subjects = 0
        failed_major_subjects = 0

        if self.year_end_report:
            # Get the Subject model dynamically
            Subject = apps.get_model('subjects', 'Subject')
            # Get all subjects the student is enrolled in
            students_subjects = Subject.objects.filter(id__in=self.student.subject_performances.values('subject_id', flat=True))

            for subject in students_subjects:
                performance = self.student.subject_performances.filter(subject=subject, term__start_date__year=self.term.start_date.year).aggregate(total_score=models.Sum('weighted_score'))['total_score']

                # Determine if the subject has been failed based on the aggregated weighted score
                if performance and performance > 0 and performance < subject.pass_mark:
                    failed_subjects += 1
                    if subject.major_subject:
                        failed_major_subjects += 1

        else:
            for performance in self.student.subject_performances.filter(term=self.term):
                if not performance.passed:
                    failed_subjects += 1
                    if performance.subject.major_subject:
                        failed_major_subjects += 1

        self.passed = False if failed_major_subjects >= self.grade.major_subjects or failed_subjects >= self.grade.none_major_subjects else True

        attendance_data = self.student.aggregate(
            absences=models.Count('absences'),
            late_arrivals=models.Count('late_arrival'),
        )

        total_school_days = self.term.school_days
        if not total_school_days:
            self.term.calculate_total_school_days()
            self.term.save()
            total_school_days = self.term.school_days

        self.attendance_percentage = (1 - (attendance_data['absences'] / total_school_days)) * 100

        self.save()

