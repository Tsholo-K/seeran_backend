# django
from django.db.models.signals import m2m_changed, post_delete
from django.dispatch import receiver

# models
from .models import Classroom
from users.models import CustomUser


@receiver(m2m_changed, sender=Classroom.students.through)
def update_students_count(sender, instance, action, **kwargs):
    if action == "post_add" or action == "post_remove":
        instance.students_count = instance.students.count()
        instance.save()


@receiver(post_delete, sender=CustomUser)
def update_student_count_on_delete(sender, instance, **kwargs):
    role = instance.role
    grade = instance.school
    
    if role == 'STUDENT':
        grade.student_count = CustomUser.objects.filter(role=role, grade=grade).count()
        grade.save()
