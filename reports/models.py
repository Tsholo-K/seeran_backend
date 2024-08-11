# python 
import uuid

# django 
from django.db import models
from django.utils.translation import gettext_lazy as _

# models
from users.models import CustomUser
from schools.models import School
from grades.models import Grade, Subject


class SubjectScore(models.Model):
    """
    Model to represent the score a student has achieved in a specific subject during a term.

    Attributes:
        student (CustomUser): The student whose score is being recorded.
        subject (Subject): The subject for which the score is recorded.
        term (Integer): The academic term for which this score applies.
        score (Float): The score the student achieved in the subject.
        total_score (Float): The total possible score for the subject.
        grade (Grade): The grade to which this score belongs.
        school (School): The school where the assessment was conducted.
        score_id (UUIDField): A unique identifier for each subject score record.
    """

    # Foreign key to the CustomUser model, representing the student. If the student is deleted, this record will be deleted as well.
    student = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='subject_scores')
    
    # Foreign key to the Subject model, representing the subject. If the subject is deleted, this record will be deleted as well.
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='student_scores')
    
    # Integer field to store the academic term for which this score applies.
    term = models.IntegerField()

    # Float field to store the actual score achieved by the student in the subject.
    score = models.FloatField()
    
    # Float field to store the total possible score for the subject.
    total_score = models.FloatField()

    # Foreign key to the Grade model, representing the grade to which this score belongs. If the grade is deleted, this record will be deleted as well.
    grade = models.ForeignKey(Grade, on_delete=models.CASCADE, related_name='grade_subject_scores')

    # Foreign key to the School model, representing the school where the assessment was conducted. If the school is deleted, this record will be deleted as well.
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='school_subject_scores')

    # UUID field to store a unique identifier for each subject score record. Automatically generates a UUID upon creation.
    score_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)

    class Meta:
        verbose_name = _('Subject Score')
        verbose_name_plural = _('Subject Scores')
        unique_together = ['student', 'subject', 'term', 'school'] # Ensures that each combination of student, subject, term, and school is unique.

    def __str__(self):
        """
        String representation of the SubjectScore model.
        """
        return f"{self.subject} - {self.student} - Term {self.term}"


class Report(models.Model):
    """
    Model to represent a student's report for a specific term.

    Attributes:
        student (CustomUser): The student whose report is being generated.
        term (Integer): The academic term for which the report is created.
        school (School): The school where the report is generated.
        subject_scores (ManyToManyField): The subject scores associated with this report.
        total_score (Float): The aggregated score for all subjects in this term.
        attendance_percentage (Float): The percentage of school days the student attended.
        days_absent (Integer): The total number of days the student was absent.
        days_late (Integer): The total number of days the student was late.
        passed (Boolean): Whether the student passed the term based on their scores.
        year_end_score (Float): The aggregated score for the year if this is the final term report.
        year_end_report (Boolean): Indicates whether this is the year-end report.
        report_id (UUIDField): A unique identifier for each report record.
    """

    # Foreign key to the CustomUser model, representing the student. If the student is deleted, this record will be deleted as well.
    student = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='term_reports')
    
    # Integer field to store the academic term for which the report is created.
    term = models.IntegerField()

    # Foreign key to the School model, representing the school where the report is generated. If the school is deleted, this record will be deleted as well.
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='term_reports')

    # Many-to-many relationship with the SubjectScore model, allowing multiple subject scores to be associated with a report.
    subject_scores = models.ManyToManyField(SubjectScore, related_name='reports')

    # Float field to store the aggregated score for all subjects in this term. Can be null or blank.
    total_score = models.FloatField(null=True, blank=True)

    # Float field to store the percentage of school days the student attended. Can be null or blank.
    attendance_percentage = models.FloatField(null=True, blank=True)

    # Integer field to store the total number of days the student was absent, with a default value of 0.
    days_absent = models.IntegerField(default=0)

    # Integer field to store the total number of days the student was late, with a default value of 0.
    days_late = models.IntegerField(default=0)

    # Boolean field to indicate whether the student passed the term based on their scores. Default is False.
    passed = models.BooleanField(default=False)

    # Float field to store the aggregated score for the year if this is the final term report. Can be null or blank.
    year_end_score = models.FloatField(null=True, blank=True)

    # Boolean field to indicate whether this is the year-end report. Default is False.
    year_end_report = models.BooleanField(default=False)

    # UUID field to store a unique identifier for each report record. Automatically generates a UUID upon creation.
    report_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)

    class Meta:
        verbose_name = _('Report')
        verbose_name_plural = _('Reports')
        unique_together = ['student', 'term', 'school']
        # Ensures that each combination of student, term, and school is unique.

    def __str__(self):
        """
        String representation of the Report model.
        """
        return f"Report - {self.student} - Term {self.term}"

    def save(self, *args, **kwargs):
        """
        Override save method to calculate total_score, attendance_percentage,
        and year_end_score if applicable, before saving the report.
        """
        # Recalculate fields if the report already exists (updating)
        if self.pk:
            self.calculate_total_score()  # Calculate the total score based on subject scores.
            self.calculate_attendance_percentage()  # Calculate attendance percentage.
            self.determine_pass_status()  # Determine if the student passed based on total score.

            if self.term == 4:  # Assuming term 4 is the final term
                self.calculate_year_end_score()  # Calculate year-end score if this is the final term.

        super().save(*args, **kwargs)

    def calculate_total_score(self):
        """
        Calculate the total score for this report by summing the scores of all related SubjectScores.
        """
        self.total_score = sum(score.score for score in self.subject_scores.all())

    def calculate_attendance_percentage(self):
        """
        Calculate the student's attendance percentage for the term.

        This is calculated as:
        (Total Days Attended / Total School Days) * 100
        """
        total_school_days = self.get_total_school_days()  # Retrieve the total number of school days.
        days_attended = total_school_days - self.days_absent  # Calculate days attended.

        if total_school_days > 0:
            self.attendance_percentage = (days_attended / total_school_days) * 100
        else:
            self.attendance_percentage = 0

    def get_total_school_days(self):
        """
        Retrieve the total number of school days for the term.

        This might be implemented to fetch data from a school calendar model or another data source.

        Returns:
            int: Total number of school days in the term.
        """
        # Example static return; replace with actual logic to retrieve total school days
        return 90  # Example: Assume 90 school days in the term

    def determine_pass_status(self):
        """
        Determine whether the student passed the term based on their total score.

        This logic can be adjusted based on the school's pass criteria.
        """
        self.passed = self.total_score >= 50  # Example threshold, adjust as needed

    def calculate_year_end_score(self):
        """
        Calculate the year-end score by weighting the scores of all terms.

        This is typically done at the end of the academic year.
        """
        if self.term == 4:  # Assuming term 4 is the final term
            reports = Report.objects.filter(student=self.student, school=self.school, year_end_report=False)
            # Collect term scores from existing reports
            term_scores = {report.term: report.total_score for report in reports}

            # Calculate year-end score based on available term scores
            self.year_end_score = (
                term_scores.get(1, 0) * 0.2 +  # Example weight for term 1
                term_scores.get(2, 0) * 0.2 +  # Example weight for term 2
                term_scores.get(3, 0) * 0.2 +  # Example weight for term 3
                self.total_score * 0.4  # Weight for the final term
            )
            self.year_end_report = True

