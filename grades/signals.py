# django
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

# models
from users.models import CustomUser


@receiver(post_save, sender=CustomUser)
def update_user_counts_on_create(sender, instance, created, **kwargs):
    if created:
        role = instance.role
        grade = instance.grade
        
        if role == 'STUDENT':
            grade.student_count = CustomUser.objects.filter(role=role, grade=grade).count()
            grade.save()

@receiver(post_delete, sender=CustomUser)
def update_user_counts_on_delete(sender, instance, **kwargs):
    role = instance.role
    grade = instance.school
    
    if role == 'STUDENT':
        grade.student_count = CustomUser.objects.filter(role=role, grade=grade).count()
        grade.save()

