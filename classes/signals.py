# django
from django.db.models.signals import post_delete
from django.dispatch import receiver

# models
from users.models import Student


@receiver(post_delete, sender=Student)
def update_user_counts_on_delete(sender, instance, **kwargs):
    for classroom in instance.enrolled_classes.all():
        # Update the students count in the class
        classroom.student_count = classroom.students.count()
        classroom.save()
