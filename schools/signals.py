# django
from django.db.models.signals import post_save, pre_delete, post_delete
from django.dispatch import receiver

# models
from users.models import BaseUser


@receiver(post_save, sender=BaseUser)
def update_user_counts_on_create(sender, instance, created, **kwargs):
    if created:
        role = instance.role
        
        if role in ['PRINCIPAL', 'ADMIN']:
            if role == 'PRINCIPAL':
                school = instance.principal.school
            elif role == 'ADMIN':
                school = instance.admin.school
            school.admin_count = school.principal.count() + school.admins.count()
        elif role == 'STUDENT':
            school.student_count = instance.student.school.students.count()
        elif role == 'TEACHER':
            school.teacher_count = instance.teacher.school.teachers.count()
        else:
            return

        school.save()

@receiver(pre_delete, sender=BaseUser)
def update_user_counts_on_delete(sender, instance, **kwargs):
    role = instance.role

    if role in ['PRINCIPAL', 'ADMIN']:
        if role == 'PRINCIPAL':
            school = instance.principal.school
        elif role == 'ADMIN':
            school = instance.admin.school
        school.admin_count -= 1
    elif role == 'STUDENT':
        school.student_count -= 1
    elif role == 'TEACHER':
        school.teacher_count -= 1
    else:
        return
