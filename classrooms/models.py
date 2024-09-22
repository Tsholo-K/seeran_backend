# python 
import uuid
import numpy as np

# django
from django.core.exceptions import ValidationError
from django.db import models, IntegrityError
from django.utils.translation import gettext_lazy as _

# models
from users.models import Teacher, Student
from schools.models import School
from grades.models import Grade
from subjects.models import Subject

# utility functions
from terms import utils as term_utilities


class Classroom(models.Model):
    classroom_number = models.CharField(_('classroom identifier'), max_length=16, default='1')
    group = models.CharField(_('class group'), max_length=16, default='A')

    teacher = models.ForeignKey(Teacher, on_delete=models.SET_NULL, null=True, blank=True, related_name='taught_classrooms', help_text='The teacher assigned to the classroom.')
    students = models.ManyToManyField(Student, related_name='enrolled_classrooms', help_text='Students enrolled in the classroom.')

    student_count = models.PositiveIntegerField(default=0)

    # Pass rate
    pass_rate = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    # Failure rate (calculated as 100 - pass_rate, but explicitly stored)
    failure_rate = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)

    highest_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    lowest_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    average_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    median_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)

    # Students who are among the top performers based on their scores
    top_performers = models.ManyToManyField(Student, related_name='top_performers_classes', blank=True)
    # Students who are failing the classroom based on their scores
    students_failing_the_classroom = models.ManyToManyField(Student, related_name='failing_classes', help_text='Students who are failing the classroom.')

    # Measures the standard deviation of students' scores, providing insight into score variability
    std_dev_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    # A JSONField storing percentile data, where each key (e.g., "10th", "90th") maps to a list of students who fall within that percentile range
    percentile_distribution = models.JSONField(null=True, blank=True)

    # Tracks the percentage of students who have improved their scores compared to a previous assessment or term
    improvement_rate = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    # Percentage of students who completed all assessments
    completion_rate = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)

    grade = models.ForeignKey(Grade, on_delete=models.CASCADE, editable=False, related_name='classrooms', help_text='Grade level associated with the classroom.')

    register_class = models.BooleanField(_('is the class a register class'), editable=False, default=False, help_text='Ensure only one register class per teacher.')
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, editable=False, related_name='classrooms', null=True, blank=True, help_text='Subject taught in the classroom.')

    school = models.ForeignKey(School, on_delete=models.CASCADE, editable=False, related_name='classrooms', help_text='School to which the classroom belongs.')
    
    last_updated = models.DateTimeField(auto_now=True)

    classroom_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['group', 'grade', 'subject'], name='unique_group_grade_subject_classroom'),
            models.UniqueConstraint(fields=['group', 'grade', 'register_class'], name='unique_group_grade_register_classroom')
        ]

    def __str__(self):
        return f"{self.school} - Grade {self.grade} - {self.classroom_number}"
    
    def clean(self):
        if not self.subject and not self.register_class:
            raise ValidationError("a classroom needs to either be a register classroom or be associated with one subject in the grade. classroom which are not register classrooms and not associated with and subject are not permitted. please revize the provided information and try again")

        if self.subject:
            if self.subject.grade != self.grade:
                raise ValidationError("could not proccess request. the subject provided to be associated with the classroom is assigned to a different grade than the one assigned to the classroom. a classrooms subject should be associated with the same grade as the classroom. please the check the provided information and try again")
                
    def save(self, *args, **kwargs):
        self.clean()

        try:
            super().save(*args, **kwargs)

        except IntegrityError as e:
            # Check if the error is related to unique constraints
            if 'unique_group_grade_subject_classroom' in str(e).lower():
                raise ValidationError(_('a classroom with the provided group in the grade and subject already exists for your school. duplicate classroom groups in the same grade and subject are not permitted. please choose a different classroom group and try again'))
            elif 'unique_group_grade_register_classroom' in str(e).lower():
                raise ValidationError(_('a classroom with the provided group in the grade and register classrooms already exists for your school. duplicate classroom groups in the same grade and register classrooms are not permitted. please choose a different classroom group and try again'))
            else:
                # Re-raise the original exception if it's not related to unique constraints
                raise

    def update_performance_metrics(self):
        if self.subject:
            current_term = term_utilities.get_current_term(self.school, self.grade)
            if not current_term:
                raise ValidationError(_('could not update performance metrics. no term found for the current period.'))
            
            performances = self.subject.student_performances.filter(student__in=self.students.all(), term=current_term)            
            if not performances.exists():
                self.pass_rate = self.failure_rate = self.average_score = None
                self.median_score = self.std_dev_score = self.percentile_distribution = None
                return
            
            pass_mark = self.subject.pass_mark

            performance_data = performances.aggregate(
                highest_score=models.Max('normalized_score'),
                lowest_score=models.Min('normalized_score'),
                average_score=models.Avg('normalized_score'),
                stddev=models.StdDev('normalized_score'),
                students_passing_the_classroom_count=models.Count('student', filter(normalized_score__gte=pass_mark)),
                students_in_the_classroom_count=models.Count('student')
            )
                
            # Find students who passed the subject in the current term
            self.pass_rate = (performance_data['students_passing_the_classroom_count'] / performance_data['students_in_the_classroom_count']) * 100
            self.failure_rate = 100 - self.pass_rate

            self.highest_score = performance_data['highest_score']
            self.lowest_score = performance_data['lowest_score']
            self.average_score = performance_data['average_score']
            self.standard_deviation = performance_data['stddev']

            # Retrieve all scores for the subject in the current term
            scores = performances.values_list('normalized_score', flat=True)

            # Calculate median score
            self.median_score = np.median(scores)

            percentiles = np.percentile(scores, [10, 25, 50, 75, 90])
            self.percentile_distribution = {
                '10th': percentiles[0], 
                '25th': percentiles[1], 
                '50th': percentiles[2],
                '75th': percentiles[3], 
                '90th': percentiles[4]
            }

            # Calculate improvement rate
            previous_term = term_utilities.get_previous_term(self.school, self.grade)
            if previous_term:
                previous_scores = self.subject.student_performances.filter(student__in=self.students.all(), term=previous_term).values_list('normalized_score', flat=True)
                if previous_scores:
                    improved_students = performances.filter(normalized_score__gt=models.F('previous_score')).count()
                    self.improvement_rate = (improved_students / performance_data['students_in_the_classroom_count']) * 100 if performance_data['students_in_the_classroom_count'] > 0 else 0
                else:
                    self.improvement_rate = None
            else:
                self.improvement_rate = None

            student_submissions = self.students.annotate(
                submission_count=models.Count(
                    'submissions',
                    filter=models.Q(submissions__assessment__classroom=self, submissions__assessment__term=current_term, submissions__assessment__formal=True, submissions__status__neq='NOT_SUBMITTED')
                )
            )
            # Track the total number of required assessments per student
            required_assessments = self.subject.assessments.filter(classroom=self, term=current_term, formal=True).count()

            # Calculate the completion rate
            completed_students = student_submissions.filter(submission_count__gte=required_assessments).count()
            self.completion_rate = (completed_students / performance_data['students_in_the_classroom_count']) * 100

            # Determine top performers
            top_performers_count = 3
            top_performers = performances.filter(normalized_score__gte=self.subject.pass_mark).values_list('student_id', flat=True).order_by('-normalized_score')[:top_performers_count]
            if top_performers.exists():
                self.top_performers.set(top_performers)

            # Query to get students who are failing the subject in the current term
            students_failing_the_classroom = self.subject.student_performances.filter(student__in=self.students.all(), term=current_term, normalized_score__lt=self.subject.pass_mark).values_list('student_id', flat=True)
            if students_failing_the_classroom.exists():
                self.students_failing_the_classroom.set(students_failing_the_classroom)

            self.save()


    def update_students(self, students_list=None, remove=False):
        if students_list:
            # Retrieve CustomUser instances corresponding to the account_ids
            students = self.grade.students.prefetch_related('enrolled_classes__subject').filter(account_id__in=students_list)

            if not students.exists():
                raise ValueError("no valid students were found in the grade with the provided account IDs.")
            
            if remove:
                # Check if students to be removed are actually in the class
                existing_students = self.students.filter(account_id__in=students_list).values_list('account_id', flat=True)
                if not existing_students:
                    raise ValueError("could not proccess your request, all the provided students are not part of this classroom")

            else:
                # Check if students are already in a class of the same subject
                if self.subject:
                    students_in_subject_classrooms = self.grade.students.filter(account_id__in=students_list, enrolled_classes__subject=self.subject).values_list('surname', 'name')
                    if students_in_subject_classrooms:
                        student_names = [f"{surname} {name}" for surname, name in students_in_subject_classrooms]
                        raise ValueError(f'the following students are already assigned to a classroom in the provided subject and grade: {", ".join(student_names)}')

                # Check if students are already in any register class
                elif self.register_class:
                    students_in_register_classrooms = self.grade.students.filter(account_id__in=students_list, enrolled_classes__register_class=True).values_list('surname', 'name')
                    if students_in_register_classrooms:
                        student_names = [f"{surname} {name}" for surname, name in students_in_register_classrooms]
                        raise ValueError(f'the following students are already assigned to a register classroom: {", ".join(student_names)}')

                # Check if students are already in this specific class
                students_in_provided_classroom = self.students.filter(account_id__in=students_list).values_list('surname', 'name')
                if students_in_provided_classroom:
                    student_names = [f"{surname} {name}" for surname, name in students_in_provided_classroom]
                    raise ValueError(f'the following students are already in this class: {", ".join(student_names)}')

            # Proceed with adding or removing students
            if remove:
                self.students.remove(*students)
            else:
                self.students.add(*students)

            # Save the classroom instance first to ensure student changes are persisted
            self.save()

            # Update the students count in the class
            self.student_count = self.students.count()
            self.save()  # Save again to update students_count field

            if self.subject:
                # Update the subject student count
                self.subject.student_count = self.grade.classes.filter(subject=self.subject).aggregate(student_count=models.Count('students'))['student_count'] or 0
                self.subject.save()
            
        else:
            raise ValueError("could not proccess your request, no students were provided to be added or removed from the classroom. please provide a valid list of students and try again")

    def update_teacher(self, teacher):
        try:
            if teacher:
                # Retrieve the CustomUser instance corresponding to the account_id
                teacher = Teacher.objects.get(account_id=teacher, school=self.school)
            
                # Check if the teacher is already assigned to another register class in the school
                if self.register_class and teacher.taught_classes.filter(register_class=True).exclude(pk=self.pk).exists():
                    raise ValueError("could not proccess your request, the provided teacher is already assigned to a register classroom. teachers can only be assigned to one register classroom in a school")
                
                # Check if the teacher is already assigned to another class in the subject
                elif self.subject and teacher.taught_classes.filter(subject=self.subject).exclude(pk=self.pk).exists():
                    raise ValueError("could not proccess your request, the provided teacher is already assigned to a classroom in the provided subject and grade. teachers can not teach more than one classroom in the same grade and subject")
                
                # Assign the teacher to the classroom
                self.teacher = teacher
            else:
                # Remove the teacher assignment
                self.teacher = None

            # Save the classroom instance with the updated teacher
            self.save()
            
            # Update the teacher count in the subject if applicable
            if self.subject:
                # Count unique teachers assigned to classrooms for this subject
                self.subject.teacher_count =  self.grade.classes.filter(subject=self.subject).exclude(teacher=None).values_list('teacher', flat=True).distinct().count()
                self.subject.save()

        except Teacher.DoesNotExist:
            raise ValueError("a teacher account in your school with the provided credentials does not exist. please check the teachers details and try again")
