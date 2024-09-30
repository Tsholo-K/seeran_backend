permission_check = {
    'PARENT': (None, 'children__school, children__enrolled_classrooms__teacher'),
    'PRINCIPAL': ('school', None),
    'ADMIN': ('school', None),
    'TEACHER': ('school', 'taught_classrooms__students'),
    'STUDENT': ('school', 'enrolled_classrooms__teacher'),
}
