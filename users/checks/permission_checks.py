

def check_profile_or_id_view_permissions(account, requested_user):
    """
    Check if the account has permission to view the requested user's profile or ID.

    Args:
        account (CustomUser): The user making the request.
        requested_user (CustomUser): The user whose profile is being requested.

    Returns:
        dict: A dictionary containing an error message if the user doesn't have permission,
              or None if the user has permission.
    """
    # No one can view the profile of a user with role not in ['PARENT', 'STUDENT', 'PRINCIPAL', 'ADMIN', 'TEACHER']
    if requested_user.role not in ['PARENT', 'STUDENT', 'PRINCIPAL', 'ADMIN', 'TEACHER']:
        return {"error": "unauthorized access. you are not permitted to view profiles outside of parents, students, principals, admins, and teachers"}

    # Admins and principals can only view profiles of accounts linked to their own school
    if account.role in ['PRINCIPAL', 'ADMIN']:
        if requested_user.role != 'PARENT' and account.school != requested_user.school:
            return {"error": "unauthorized access. you are not permitted to view profiles of accounts outside your own school"}
        if requested_user.role == 'PARENT' and not requested_user.children.filter(school=account.school).exists():
            return {"error": "unauthorized access. you can only view parent profiles associated with students in your school"}

    # Teachers can view parents and students in their own class, and admins/principals in their school
    if account.role == 'TEACHER':
        if requested_user.role in ['PRINCIPAL', 'ADMIN', 'TEACHER'] and account.school != requested_user.school:
            return {"error": "unauthorized access. you are not permitted to view profiles of admins, principals, or other teachers outside your own school"}
        if requested_user.role == 'PARENT' and not requested_user.children.filter(taught_classes__teacher=account).exists():
            return {"error": "unauthorized access. you can only view parent profiles associated with students you teach"}
        if requested_user.role == 'STUDENT' and not account.taught_classes.filter(students=requested_user).exists():
            return {"error": "unauthorized access. you can only view student profiles of students you teach"}

    # Parents can view their children (students), teachers of their children, admins/principals of their children's schools, and other parents they share children with
    if account.role == 'PARENT':
        if requested_user.role == 'STUDENT' and requested_user not in account.children.all():
            return {"error": "unauthorized access. you are not permitted to view profiles of students who are not your children"}
        if requested_user.role == 'TEACHER' and not account.children.filter(taught_classes__teacher=requested_user).exists():
            return {"error": "unauthorized access. you can only view profiles of teachers who teach your children"}
        if requested_user.role in ['PRINCIPAL', 'ADMIN'] and not account.children.filter(school=requested_user.school).exists():
            return {"error": "unauthorized access. you can only view profiles of admins and principals of your children's schools"}
        if requested_user.role == 'PARENT' and not account.children.filter(pk__in=requested_user.children.values_list('pk', flat=True)).exists():
            return {"error": "unauthorized access. you are not permitted to view profiles of parents who do not share children with you"}

    # Students can only view their parents, teachers who teach them, and admins/principals from their own school
    if account.role == 'STUDENT':
        if requested_user.role not in ['PARENT', 'TEACHER', 'PRINCIPAL', 'ADMIN']:
            return {"error": "unauthorized access. you are not permitted to view profiles outside of parents, teachers, principals, and admins"}
        if requested_user.role == 'PARENT' and account not in requested_user.children.all():
            return {"error": "unauthorized access. you can only view profiles of your parents"}
        if requested_user.role == 'TEACHER' and not requested_user.taught_classes.filter(students=account).exists():
            return {"error": "unauthorized access. you can only view profiles of teachers who teach you"}
        if requested_user.role in ['PRINCIPAL', 'ADMIN'] and account.school != requested_user.school:
            return {"error": "unauthorized access. you can only view profiles of admins and principals of your own school"}

    # If no errors, return None indicating permission granted
    return None
