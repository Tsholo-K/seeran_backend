"""
    functions to check if account A can perform actions on entity B

    - these functions check for permissions to determine if an account can view, update or message the entity they are trying to access
    - if the account passes the check then nothing is returned else an object with a error message is returned
"""


def view_account(requesting_account, requested_account):
    if requesting_account.role not in ['PRINCIPAL', 'ADMIN', 'TEACHER', 'PARENT', 'STUDENT']:
        return {"error": "unauthorized access. invalid role provided"}

    # No one can view the profile of a user with role not in ['PARENT', 'STUDENT', 'PRINCIPAL', 'ADMIN', 'TEACHER']
    if requested_account.role not in ['PARENT', 'STUDENT', 'PRINCIPAL', 'ADMIN', 'TEACHER']:
        return {"error": "unauthorized access. you are not permitted to view profiles outside of parents, students, principals, admins, and teachers"}

    # Admins and principals can only view profiles of accounts linked to their own school
    if requesting_account.role in ['PRINCIPAL', 'ADMIN']:
        if requested_account.role != 'PARENT' and requesting_account.school != requested_account.school:
            return {"error": "unauthorized access. you are not permitted to view profiles of accounts outside your own school"}
        if requested_account.role == 'PARENT' and not requested_account.children.filter(school=requesting_account.school).exists():
            return {"error": "unauthorized access. you can only view parent profiles associated with students in your school"}

    # Teachers can view parents and students in their own class, and admins/principals in their school
    if requesting_account.role == 'TEACHER':
        if requested_account.role in ['PRINCIPAL', 'ADMIN', 'TEACHER'] and requesting_account.school != requested_account.school:
            return {"error": "unauthorized access. you are not permitted to view profiles of admins, principals, or other teachers outside your own school"}
        if requested_account.role == 'PARENT' and not requested_account.children.filter(taught_classes__teacher=requesting_account).exists():
            return {"error": "unauthorized access. you can only view parent profiles associated with students you teach"}
        if requested_account.role == 'STUDENT' and not requesting_account.taught_classes.filter(students=requested_account).exists():
            return {"error": "unauthorized access. you can only view student profiles of students you teach"}

    # Parents can view their children (students), teachers of their children, admins/principals of their children's schools, and other parents they share children with
    if requesting_account.role == 'PARENT':
        if requested_account.role == 'STUDENT' and requested_account not in requesting_account.children.all():
            return {"error": "unauthorized access. you are not permitted to view profiles of students who are not your children"}
        if requested_account.role == 'TEACHER' and not requesting_account.children.filter(taught_classes__teacher=requested_account).exists():
            return {"error": "unauthorized access. you can only view profiles of teachers who teach your children"}
        if requested_account.role in ['PRINCIPAL', 'ADMIN'] and not requesting_account.children.filter(school=requested_account.school).exists():
            return {"error": "unauthorized access. you can only view profiles of admins and principals of your children's schools"}
        if requested_account.role == 'PARENT' and not requesting_account.children.filter(pk__in=requested_account.children.values_list('pk', flat=True)).exists():
            return {"error": "unauthorized access. you are not permitted to view profiles of parents who do not share children with you"}

    # Students can only view their parents, teachers who teach them, and admins/principals from their own school
    if requesting_account.role == 'STUDENT':
        if requested_account.role not in ['PARENT', 'TEACHER', 'PRINCIPAL', 'ADMIN']:
            return {"error": "unauthorized access. you are not permitted to view profiles outside of parents, teachers, principals, and admins"}
        if requested_account.role == 'PARENT' and requesting_account not in requested_account.children.all():
            return {"error": "unauthorized access. you can only view profiles of your parents"}
        if requested_account.role == 'TEACHER' and not requested_account.taught_classes.filter(students=requesting_account).exists():
            return {"error": "unauthorized access. you can only view profiles of teachers who teach you"}
        if requested_account.role in ['PRINCIPAL', 'ADMIN'] and requesting_account.school != requested_account.school:
            return {"error": "unauthorized access. you can only view profiles of admins and principals of your own school"}

    # If no errors, return None indicating permission granted
    return None


def update_account(requesting_account, requested_account):
    if requesting_account.role not in ['PRINCIPAL', 'ADMIN']:
        return {"error": "unauthorized access. invalid role provided"}

    # No one can view the profile of a user with role not in ['PARENT', 'STUDENT', 'ADMIN', 'TEACHER']
    if requested_account.role not in ['PARENT', 'STUDENT', 'ADMIN', 'TEACHER']:
        return {"error": "unauthorized access. you are not permitted to update profiles outside of parents, students, admins, and teachers"}

    # Admins and principals can only view profiles of accounts linked to their own school
    if requested_account.role != 'PARENT' and requesting_account.school != requested_account.school:
        return {"error": "unauthorized access. you are not permitted to update profiles of accounts outside your own school"}
    if requested_account.role == 'PARENT' and not requested_account.children.filter(school=requesting_account.school).exists():
        return {"error": "unauthorized access. you can only update parent profiles associated with students in your school"}

    # If no errors, return None indicating permission granted
    return None


def message(requesting_account, requested_account):
    if requesting_account.role not in ['PRINCIPAL', 'ADMIN', 'TEACHER', 'PARENT', 'STUDENT']:
        return {"error": "unauthorized access. invalid role provided"}

    # No one can message a user with role not in ['PARENT', 'STUDENT', 'PRINCIPAL', 'ADMIN', 'TEACHER']
    elif requested_account.role not in ['PRINCIPAL', 'ADMIN', 'TEACHER', 'PARENT', 'STUDENT']:
        return {"error": "unauthorized access. you are not permitted to view profiles outside of parents, students, principals, admins, and teachers"}

    # Admins and principals can only message accounts linked to their own school
    elif requesting_account.role in ['PRINCIPAL', 'ADMIN']:
        if requested_account.role != 'PARENT' and requesting_account.school != requested_account.school:
            return {"error": "unauthorized access. you are not permitted to message accounts outside your own school"}
        elif requested_account.role == 'PARENT' and not requested_account.children.filter(school_id=requesting_account.school_id).exists():
            return {"error": "unauthorized access. you can only message parent accounts associated with students in your school"}

    # Teachers can message parents and students in their own class, and admins/principals in their school
    elif requesting_account.role == 'TEACHER':
        if requested_account.role in ['PRINCIPAL', 'ADMIN', 'TEACHER'] and requesting_account.school_id != requested_account.school_id:
            return {"error": "unauthorized access. you are not permitted to message admins, principals, or other teachers outside your own school"}
        elif requested_account.role == 'PARENT' and not requested_account.children.filter(enrolled_classrooms__teacher=requesting_account).exists():
            return {"error": "unauthorized access. you can only message parent accounts associated with students you teach"}
        elif requested_account.role == 'STUDENT' and not requesting_account.taught_classrooms.filter(students=requested_account).exists():
            return {"error": "unauthorized access. you can only message student accounts you teach"}

    # Parents can message their children (students), teachers of their children, admins/principals of their children's schools, and other parents they share children with
    elif requesting_account.role == 'PARENT':
        if requested_account.role in ['PRINCIPAL', 'ADMIN'] and not requesting_account.children.filter(school_id=requested_account.school_id).exists():
            return {"error": "unauthorized access. you can only message admins and principals of your children's schools"}
        elif requested_account.role == 'TEACHER' and not requesting_account.children.filter(enrolled_classrooms__teacher=requested_account).exists():
            return {"error": "unauthorized access. you can only message teachers who teach your children"}
        elif requested_account.role == 'STUDENT' and not requesting_account.children.filter(id=requested_account.id).exists():
            return {"error": "unauthorized access. you are not permitted to message students who are not your children"}
        elif requested_account.role == 'PARENT' and not requesting_account.children.filter(id__in=requested_account.children.values_list('id', flat=True)).exists():
            return {"error": "unauthorized access. you are not permitted to message parents who do not share children with you"}

    # Students can only message their parents, teachers who teach them, and admins/principals from their own school
    elif requesting_account.role == 'STUDENT':
        if requested_account.role not in ['PARENT', 'TEACHER', 'PRINCIPAL', 'ADMIN']:
            return {"error": "unauthorized access. you are not permitted to message accounts outside of parents, teachers, principals, and admins"}
        elif requested_account.role in ['PRINCIPAL', 'ADMIN'] and requesting_account.school != requested_account.school:
            return {"error": "unauthorized access. you can only message admins and principals of your own school"}
        elif requested_account.role == 'TEACHER' and not requesting_account.enrolled_classrooms.filter(teacher=requested_account).exists():
            return {"error": "unauthorized access. you can only message teachers who teach you"}
        elif requested_account.role == 'PARENT' and not requesting_account.parents.filter(id=requested_account.id).exists():
            return {"error": "unauthorized access. you can only message parent accounts of your parents"}

    # If no errors, return None indicating permission granted
    return None


def view_classroom(account, classroom):
    # Ensure the account has a valid role
    if account.role not in ['PRINCIPAL', 'ADMIN', 'TEACHER', 'PARENT', 'STUDENT']:
        return {"error": "Unauthorized access. Invalid role provided."}

    # Admins and principals can only access classrooms within their own school
    if account.role in ['PRINCIPAL', 'ADMIN']:
        if account.school != classroom.school:
            return {"error": "Unauthorized access. You are not permitted to access classroom information outside your own school."}

    # Teachers can access classrooms they teach, within their own school
    if account.role == 'TEACHER':
        if account.school != classroom.school or not classroom in account.taught_classes.all():
            return {"error": "Unauthorized access. You can only access classroom information of classes you teach."}

    # Parents can access classrooms their children are part of, within their children's school
    if account.role == 'PARENT':
        # Check if any of the parent's children are in the classroom
        if not account.children.filter(id__in=classroom.students.values_list('id', flat=True)).exists():
            return {"error": "Unauthorized access. You are not permitted to access classroom information of classes your children are not part of."}

    # Students can access classrooms they are part of, within their own school
    if account.role == 'STUDENT':
        if account.school != classroom.school or not classroom.students.filter(id=account.id).exists():
            return {"error": "Unauthorized access. You can only access classroom information of classes you are part of."}

    # If no errors, return None indicating permission granted
    return None


def view_activity(requesting_account, activity):
    # Ensure the account has a valid role
    if requesting_account.role not in ['PRINCIPAL', 'ADMIN', 'TEACHER', 'PARENT', 'STUDENT']:
        return {"error": "Unauthorized access. Invalid role provided."}

    # Admins and principals can only access activities within their own school
    if requesting_account.role in ['PRINCIPAL', 'ADMIN']:
        if requesting_account.school != activity.school:
            return {"error": "Unauthorized access. You are not permitted to access activities outside your own school."}

    # Teachers can only access activities they have logged, within their own school
    if requesting_account.role == 'TEACHER':
        if requesting_account.school != activity.school or not activity.logger == requesting_account:
            return {"error": "Unauthorized access. You can only access activities that you have logged."}

    # Parents can access activities where their children are the recipient, within their children's school
    if requesting_account.role == 'PARENT':
        if requesting_account.school != activity.school or not requesting_account.children.filter(id=activity.recipient.id).exists():
            return {"error": "Unauthorized access. You are not permitted to access activities involving students who are not your children."}

    # Students can only access activities where they are the recipient, within their own school
    if requesting_account.role == 'STUDENT':
        if requesting_account.school != activity.school or activity.recipient != requesting_account:
            return {"error": "Unauthorized access. You can only access activities that involve you as the recipient."}

    # If no errors, return None indicating permission granted
    return None


def view_group_timetable(requesting_account, group_schedule):
    # Ensure the account has a valid role
    if requesting_account.role not in ['PRINCIPAL', 'ADMIN', 'TEACHER', 'PARENT', 'STUDENT']:
        return {"error": "Unauthorized access. Invalid role provided."}
    
    # Students can only access schedules if they are in the group schedule's students
    if requesting_account.role == 'STUDENT' and not group_schedule.subscribers.filter(id=requesting_account.id).exists():
        return {"error": "As a student, you can only view schedules for groups you are subscribed to. Please check your group assignments and try again."}

    # Parents can only access schedules if at least one of their children is in the group schedule's students
    if requesting_account.role == 'PARENT' and not group_schedule.subscribers.filter(id__in=requesting_account.children.values_list('id', flat=True)).exists():
        return {"error": "As a parent, you can only view schedules for groups that your children are subscribed to. Please check your child's group assignments and try again."}

    # Teachers, Admins, and Principals can only access schedules if they belong to the same school as the group schedule's grade
    if requesting_account.role in ['TEACHER', 'ADMIN', 'PRINCIPAL'] and requesting_account.school != group_schedule.grade.school:
        return {"error": "You can only view schedules for groups within your own school. Please check the group schedule and try again."}

    # If no errors, return None indicating permission granted
    return None
