


def update_classroom_student_count(classroom):
    # Update all counts for grade
    classroom.student_count = classroom.students.count()
    classroom.save()


