# django
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

# models
from users.models import BaseUser


@receiver(post_save, sender=BaseUser)
def update_user_counts_on_create(sender, instance, created, **kwargs):
    if created:
        role = instance.role
        
        if role in ['PRINCIPAL', 'ADMIN', 'STUDENT', 'TEACHER']:
            school = instance.school
            
            if role in ['PRINCIPAL']:
                school.admin_count = school.principal.count()
            if role in ['ADMIN']:
                school.admin_count = school.admins.count()
            elif role == 'STUDENT':
                school.student_count = school.students.count()
            elif role == 'TEACHER':
                school.teacher_count = school.teachers.count()

            school.save()

@receiver(post_delete, sender=BaseUser)
def update_user_counts_on_delete(sender, instance, **kwargs):
    role = instance.role

    if role in ['PRINCIPAL', 'ADMIN', 'STUDENT', 'TEACHER']:
        school = instance.school
        
        if role in ['PRINCIPAL']:
            school.admin_count = school.principal.count()
        if role in ['ADMIN']:
            school.admin_count = school.admins.count()
        elif role == 'STUDENT':
            school.student_count = school.students.count()
        elif role == 'TEACHER':
            school.teacher_count = school.teachers.count()

        school.save()