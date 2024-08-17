# django
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

# models
from users.models import CustomUser


@receiver(post_save, sender=CustomUser)
def update_user_counts_on_create(sender, instance, created, **kwargs):
    if created:
        role = instance.role
        
        if role in ['PRINCIPAL', 'ADMIN', 'STUDENT', 'TEACHER']:
            school = instance.school
            
            if role == 'PRINCIPAL':
                role = 'ADMIN'  # Treat principal as admin for counting purposes

            count = CustomUser.objects.filter(role=role, school=school).count()

            if role == 'STUDENT':
                school.student_count = count
            elif role == 'TEACHER':
                school.teacher_count = count
            elif role == 'ADMIN':
                school.admin_count = count

            school.save()

@receiver(post_delete, sender=CustomUser)
def update_user_counts_on_delete(sender, instance, **kwargs):
    role = instance.role

    if role in ['PRINCIPAL', 'ADMIN', 'STUDENT', 'TEACHER']:
        school = instance.school
        
        if role == 'PRINCIPAL':
            role = 'ADMIN'  # Treat principal as admin for counting purposes

        count = CustomUser.objects.filter(role=role, school=school).count()

        if role == 'STUDENT':
            school.student_count = count
        elif role == 'TEACHER':
            school.teacher_count = count
        elif role == 'ADMIN':
            school.admin_count = count

        school.save()