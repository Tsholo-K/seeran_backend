# django
from django.db.models.signals import pre_delete
from django.dispatch import receiver

# models
from users.models import Student


@receiver(pre_delete, sender=Student)
def update_user_counts_on_delete(sender, instance, **kwargs):
    for classroom in instance.enrolled_classes.all():
        # Update the student count in the class, excluding the student being deleted
        classroom.student_count = classroom.students.exclude(account_id=instance.account_id).count()
        classroom.save()

