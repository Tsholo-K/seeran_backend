


def update_grade_counts(grade):
    # Update all counts for grade
    grade.teacher_count = grade.classrooms.exclude(teacher=None).values_list('teacher', flat=True).distinct().count()
    grade.student_count = grade.students.count()
    grade.classroom_count = grade.classrooms.count()
    grade.subject_count = grade.subjects.count()
    grade.term_count = grade.terms.count()
    
    grade.save(update_fields=['teacher_count', 'student_count', 'classroom_count', 'subject_count', 'term_count'])


def update_grade_role_counts(grade, role):
    # Update all counts for grade
    if role == 'STUDENT':
        grade.teacher_count = grade.classrooms.exclude(teacher=None).values_list('teacher', flat=True).distinct().count()
    elif role == 'TEACHER':
        grade.student_count = grade.students.count()
    
    grade.save(update_fields=['teacher_count', 'student_count'])


def update_grade_teacher_count(grade):
    # Update teacher count for grade
    grade.teacher_count = grade.classrooms.exclude(teacher=None).values_list('teacher', flat=True).distinct().count()
    grade.save(update_fields=['teacher_count'])


def update_grade_student_count(grade):
    # Update student count for grade
    grade.student_count = grade.students.count()
    grade.save(update_fields=['student_count'])


def update_grade_classrooms_count(grade):
    # Update classrooms count for grade
    grade.classroom_count = grade.classrooms.count()
    grade.save(update_fields=['classroom_count'])


def update_grade_subject_count(grade):
    # Update subject count for grade
    grade.subject_count = grade.subjects.count()
    grade.save(update_fields=['subject_count'])


def update_grade_term_count(grade):
    # Update term count for grade
    grade.term_count = grade.terms.count()
    grade.save(update_fields=['term_count'])


