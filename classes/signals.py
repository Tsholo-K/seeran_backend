# django
from django.db.models.signals import post_delete
from django.dispatch import receiver

# models
from .models import Classroom
from users.models import CustomUser


@receiver(post_delete, sender=CustomUser)
def update_user_counts_on_delete(sender, instance, **kwargs):
    role = instance.role

    if role == 'STUDENT':
        for classroom in instance.enrolled_classes.all():
            # Update the students count in the class
            classroom.student_count = classroom.students.count()
            classroom.save()
