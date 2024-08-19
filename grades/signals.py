# django
from django.db import models
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

# models
from users.models import CustomUser
from classes.models import Classroom

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
    grade = instance.grade
    
    if role == 'STUDENT':
        grade.student_count = CustomUser.objects.filter(role=role, grade=grade).count()
        grade.save()

@receiver(post_save, sender=Classroom)
def update_class_counts_on_create_or_update(sender, instance, created, **kwargs):
    if created and instance.subject:
        # Update the count of classrooms associated with this subject
        instance.subject.classes_count = instance.grade.grade_classes.filter(subject=instance.subject).count()

        # Update the count of unique teachers for this subject
        if instance.teacher:
            instance.subject.teacher_count = instance.grade.grade_classes.filter(subject=instance.subject).exclude(teacher=None).values_list('teacher', flat=True).distinct().count()

        # Save the updated subject instance
        instance.subject.save()

@receiver(post_delete, sender=Classroom)
def update_class_counts_on_delete(sender, instance, **kwargs):
    if instance.subject:
        # Update the count of classrooms associated with this subject
        instance.subject.classes_count = instance.grade.grade_classes.filter(subject=instance.subject).count()

        # Update the count of unique teachers for this subject
        if instance.teacher:
            instance.subject.teacher_count = instance.grade.grade_classes.filter(subject=instance.subject).exclude(teacher=None).values_list('teacher', flat=True).distinct().count()
        
        # Update the count of students for this subject
        if instance.students:
            instance.subject.student_count = instance.grade.grade_classes.filter(subject=instance.subject).aggregate(count=models.Sum('students__count'))['count'] or 0

        # Save the updated subject instance
        instance.subject.save()