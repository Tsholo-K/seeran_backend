# python 
import uuid
import statistics

# django
from django.core.exceptions import ValidationError
from django.db import models, IntegrityError
from django.utils.translation import gettext_lazy as _
from django.db.models import Avg

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

    teacher = models.ForeignKey(Teacher, on_delete=models.SET_NULL, null=True, blank=True, related_name='taught_classes', help_text='The teacher assigned to the classroom.')
    students = models.ManyToManyField(Student, related_name='enrolled_classrooms', help_text='Students enrolled in the classroom.')

    student_count = models.IntegerField(default=0)

    pass_rate = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)

    average_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    median_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)

    students_failing_the_class = models.ManyToManyField(Student, related_name='failing_classes', help_text='Students who are failing the classroom.')

    grade = models.ForeignKey(Grade, on_delete=models.CASCADE, editable=False, related_name='classrooms', help_text='Grade level associated with the classroom.')

    register_class = models.BooleanField(_('is the class a register class'), editable=False, default=False, help_text='Ensure only one register class per teacher.')
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, editable=False, related_name='classrooms', null=True, blank=True, help_text='Subject taught in the classroom.')

    school = models.ForeignKey(School, on_delete=models.CASCADE, editable=False, related_name='classrooms', help_text='School to which the classroom belongs.')
    
    last_updated = models.DateTimeField(auto_now=True)

    classroom_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)

    class Meta:
        unique_together = (
            ('group', 'grade', 'subject'),  # Unique combination in subject classes
            ('group', 'grade', 'register_class')  # Unique combination in register classes
        ) 

    def __str__(self):
        return f"{self.school} - Grade {self.grade} - {self.classroom_number}"
    
    def clean(self):
        if not self.subject and not self.register_class:
            raise ValidationError("a classroom needs to either be a register classroom or be associated with one subject in the grade. classroom which are not register classrooms and not associated with and subject are not permitted. please revize the provided information and try again")

        if self.subject:
            if self.subject.grade != self.grade:
                return {"error": "could not proccess request. the subject provided to be associated with the classroom is assigned to a different grade than the one assigned to the classroom. a classrooms subject should be associated with the same grade as the classroom. please the check the provided information and try again"}
                
    def save(self, *args, **kwargs):
        self.clean()

        try:
            super().save(*args, **kwargs)

        except IntegrityError as e:
            # Check if the error is related to unique constraints
            if 'unique constraint' in str(e).lower():
                raise ValidationError(_('a classroom with the provided group in the grade and subject/register already exists for your school. duplicate classroom groups in the same grade and subject/register are not permitted. please choose a different classroom group and try again'))
            else:
                # Re-raise the original exception if it's not related to unique constraints
                raise

    def update_performance_metrics(self):
        total_students = self.students.count() if self.students.exists() else 0
        
        current_term = term_utilities.get_current_term(self.school, self.grade)
        if not current_term:
            raise ValidationError(_('could not update performance metrics. no term found for the current period.'))

        # Calculate pass rate
        if self.subject:
            if total_students > 0:
                # Find students who passed the subject in the current term
                passing_scores = self.student_performances.filter(student__in=self.students.all(), term=current_term, score__lte=self.subject.pass_mark).count()
                self.pass_rate = (passing_scores / total_students) * 100
            else:
                self.pass_rate = None

            # Calculate average score
            total_scores = self.student_performances.filter(student__in=self.students.all(), term=current_term).aggregate(avg=models.Avg('score'))['avg']
            self.average_score = total_scores or 0.0

        # Retrieve all scores for the subject in the current term
        scores = list(self.student_performances.filter(student__in=self.students.all(), term=current_term).values_list('score', flat=True))

        # Calculate average score
        total_scores = self.student_performances.filter(student__in=self.students.all(), term=current_term).aggregate(avg=Avg('score'))['avg']
        self.average_score = total_scores or 0.0

        # Calculate median score
        if scores:
            self.median_score = statistics.median(scores)
        else:
            self.median_score = 0.0

        self.save()

    def update_students_failing_the_class(self):
        current_term = term_utilities.get_current_term(self.school, self.grade)
        if not current_term:
            raise ValidationError(_('could not update performance metrics. no term found for the current period.'))

        # Query to get students who are failing the subject in the current term
        failing_students_account_ids = self.student_performances.filter(student__in=self.students.all(), term=current_term, score__lte=self.subject.pass_mark).values_list('student__account_id', flat=True)

        # Fetch student instances
        failing_students = Student.objects.filter(account_id__in=failing_students_account_ids)

        # Update the students_failing_the_class field
        self.students_failing_the_class.set(failing_students)
        self.save()

    def update_students(self, students_list=None, remove=False):
        if students_list:
            # Retrieve CustomUser instances corresponding to the account_ids
            students = self.grade.students.prefetch_related('enrolled_classes__subject').filter(account_id__in=students_list)

            if not students.exists():
                return "no valid students were found in the grade with the provided account IDs."
            
            if remove:
                # Check if students to be removed are actually in the class
                existing_students = self.students.filter(account_id__in=students_list).values_list('account_id', flat=True)
                if not existing_students:
                    return "could not proccess your request, all the provided students are not part of this classroom"

            else:
                # Check if students are already in a class of the same subject
                if self.subject:
                    students_in_subject_classrooms = self.grade.students.filter(account_id__in=students_list, enrolled_classes__subject=self.subject).values_list('surname', 'name')
                    if students_in_subject_classrooms:
                        student_names = [f"{surname} {name}" for surname, name in students_in_subject_classrooms]
                        return f'the following students are already assigned to a classroom in the provided subject and grade: {", ".join(student_names)}'

                # Check if students are already in any register class
                elif self.register_class:
                    students_in_register_classrooms = self.grade.students.filter(account_id__in=students_list, enrolled_classes__register_class=True).values_list('surname', 'name')
                    if students_in_register_classrooms:
                        student_names = [f"{surname} {name}" for surname, name in students_in_register_classrooms]
                        return f'the following students are already assigned to a register classroom: {", ".join(student_names)}'

                # Check if students are already in this specific class
                students_in_provided_classroom = self.students.filter(account_id__in=students_list).values_list('surname', 'name')
                if students_in_provided_classroom:
                    student_names = [f"{surname} {name}" for surname, name in students_in_provided_classroom]
                    return f'the following students are already in this class: {", ".join(student_names)}'

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
