from django.db import models


def update_subject_counts(subject):
    grade = subject.grade
        
    subject.classrooms_count = grade.classrooms.filter(subject=subject).count()
    subject.teacher_count = grade.classrooms.filter(subject=subject).exclude(teacher=None).values_list('teacher', flat=True).distinct().count()
    subject.student_count = grade.classrooms.filter(subject=subject).aggregate(student_count=models.Count('students'))['student_count'] or 0
    subject.save(update_fields=['classrooms_count', 'teacher_count', 'student_count'])


def update_subject_role_counts(subject, role):
    grade = subject.grade
    
    if role == 'STUDENT':
        subject.student_count = grade.classrooms.filter(subject=subject).aggregate(student_count=models.Count('students'))['student_count'] or 0
    elif role == 'TEACHER':
        subject.teacher_count = grade.classrooms.filter(subject=subject).exclude(teacher=None).values_list('teacher', flat=True).distinct().count()

    subject.save(update_fields=['teacher_count', 'student_count'])


def update_subject_classrooms_count(subject):
    grade = subject.grade
        
    subject.classrooms_count = grade.classrooms.filter(subject=subject).count()
    subject.save(update_fields=['classrooms_count'])


def update_subject_teacher_count(subject):
    grade = subject.grade
        
    subject.teacher_count = grade.classrooms.filter(subject=subject).exclude(teacher=None).values_list('teacher', flat=True).distinct().count()
    subject.save(update_fields=['teacher_count'])


def update_subject_student_count(subject):
    grade = subject.grade
    
    subject.student_count = grade.classrooms.filter(subject=subject).aggregate(student_count=models.Count('students'))['student_count'] or 0
    subject.save(update_fields=['student_count'])
