# python 
import uuid
from datetime import date

# django
from django.core.exceptions import ValidationError
from django.db import models, IntegrityError
from django.utils.translation import gettext_lazy as _

# models
from users.models import Teacher, Student
from schools.models import School
from grades.models import Grade
from terms.models import Term
from subjects.models import Subject
from subject_scores.models import SubjectScore


class Classroom(models.Model):
    classroom_number = models.CharField(_('classroom identifier'), max_length=16, default='1')
    group = models.CharField(_('class group'), max_length=16, default='A')

    teacher = models.ForeignKey(Teacher, on_delete=models.SET_NULL, null=True, blank=True, related_name='taught_classes', help_text='The teacher assigned to the classroom.')
    students = models.ManyToManyField(Student, related_name='enrolled_classes', help_text='Students enrolled in the classroom.')

    student_count = models.IntegerField(default=0)

    pass_rate = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    average_score = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)

    students_failing_the_class = models.ManyToManyField(Student, related_name='failing_classes', help_text='Students who are failing the classroom.')

    grade = models.ForeignKey(Grade, on_delete=models.CASCADE, editable=False, related_name='classrooms', help_text='Grade level associated with the classroom.')

    register_class = models.BooleanField(_('is the class a register class'), editable=False, default=False, help_text='Ensure only one register class per teacher.')
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, editable=False, related_name='classrooms', null=True, blank=True, help_text='Subject taught in the classroom.')

    school = models.ForeignKey(School, on_delete=models.CASCADE, editable=False, related_name='classrooms', help_text='School to which the classroom belongs.')

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
        """
        Override save method to validate incoming data.
        """
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

    def update_pass_rate_and_average_score(self):
        """ Updates the pass rate and average score based on student performance. """
        total_students = self.students.count() if self.students.exists() else 0
        pass_count = self.students.filter(transcripts__weighted_score__gte=self.subject.pass_mark).count()
        
        if total_students > 0:
            self.pass_rate = (pass_count / total_students) * 100
        else:
            self.pass_rate = 0.0

        total_scores = self.assessments.aggregate(avg=models.Avg('scores__weighted_score'))['avg']
        self.average_score = total_scores or 0.0

        self.save()

    def get_current_term(school, grade):
        """ Get the current term based on today's date. """
        today = date.today()
        current_term = Term.objects.filter(school=school, grade=grade, start_date__lte=today, end_date__gte=today).first()
        return current_term

    def update_students_failing_the_class(self):
        """ Update the list of students failing the class based on their termly performance. """
        current_term = self.get_current_term(self.school, self.grade)
        if not current_term:
            raise ValidationError(_('could not update students failing the classroom, no term was found for your school and grade for the current period.'))

        failing_students = []

        for student in self.students.all():
            # Check if there are assessments for the subject in the current term
            assessments = student.assessments.filter(subject=self.subject, term=current_term, formal=True, grades_released=True)
            if not assessments.exists():
                continue

            # Get or create the student's subject score for the current term and subject
            subject_score, created = SubjectScore.objects.get_or_create(student=student, subject=self.subject, term=current_term, defaults={'grade': self.grade, 'school': self.school})

            # Check if the student's score is below the pass mark
            if subject_score.score < self.subject.pass_mark:
                failing_students.append(student)

        # Update the students_failing_the_class field
        self.students_failing_the_class.set(failing_students)
        self.save()

    def update_students(self, students_list=None, remove=False):
        """
        Add or remove the provided list of students (by account_id) to/from the class and update the students count.

        Args:
            students_list (list): List of student account IDs.
            remove (bool): Indicates if students should be removed.
        """
        if students_list:
            # Retrieve CustomUser instances corresponding to the account_ids
            students = self.school.students.prefetch_related('enrolled_classes__subject').filter(account_id__in=students_list)

            if not students.exists():
                return "no valid students found with the provided account IDs."
            
            if remove:
                # Check if students to be removed are actually in the class
                existing_students = self.students.filter(account_id__in=students_list).values_list('account_id', flat=True)
                if not existing_students:
                    return "could not proccess your request, all the provided students are not part of this classroom"

            else:
                # Check if students are already in a class of the same subject
                if self.subject:
                    students_in_subject = self.grade.students.filter(account_id__in=students_list, enrolled_classes__subject=self.subject).values_list('account_id', flat=True)
                    if students_in_subject:
                        return f'the following students are already assigned to a class in the provided subject and grade: {", ".join(students_in_subject)}'

                # Check if students are already in any register class
                if self.register_class:
                    students_in_register_classes = self.grade.students.filter(account_id__in=students_list, enrolled_classes__register_class=True).values_list('account_id', flat=True)
                    if students_in_register_classes:
                        return f'the following students are already assigned to a register class: {", ".join(students_in_register_classes)}'

                # Check if students are already in this specific class
                existing_students = self.students.filter(account_id__in=students_list).values_list('account_id', flat=True)
                if existing_students:
                    return f'the following students are already in this class: {", ".join(existing_students)}'

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
            return "Validation error: No students were provided."

    def update_teacher(self, teacher):
        """
        Update the class's teacher and update the subject's teacher count if applicable.
        This method ensures that a teacher can only be assigned to one register class per school.
        """
        try:
            if teacher:
                # Retrieve the CustomUser instance corresponding to the account_id
                teacher = Teacher.objects.prefetch_related('taught_classes__subject').get(account_id=teacher, school=self.school)
            
                # Check if the teacher is already assigned to another register class in the school
                if self.register_class and teacher.taught_classes.filter(register_class=True).exclude(pk=self.pk).exists():
                    raise ValueError("the provided teacher is already assigned to a register class. teachers can only be assigned to one register class in a school")
                
                # Check if the teacher is already assigned to another class in the subject
                elif self.subject and teacher.taught_classes.filter(subject=self.subject).exclude(pk=self.pk).exists():
                    raise ValueError("the provided teacher is already assigned to a class in the provided subject and grade. teachers can not teach more than one class in the same grade and subject")
                
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
