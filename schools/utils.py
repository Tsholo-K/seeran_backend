

def update_school_counts(school):
    school.admin_count = school.principal.count() + school.admins.count()
    school.student_count = school.students.count()
    school.teacher_count = school.teachers.count()

    school.save()

def update_school_role_counts(school, role):
    if role in ['PRINCIPAL', 'ADMIN']:
        school.admin_count = school.principal.count() + school.admins.count()
    elif role == 'STUDENT':
        school.student_count = school.students.count()
    elif role == 'TEACHER':
        school.teacher_count = school.teachers.count()

    school.save()

