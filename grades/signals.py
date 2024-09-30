# django
from django.db import models
from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver

# models
from users.models import BaseUser, Student
from classrooms.models import Classroom

# mappings
from users.maps import role_specific_attr_maps


# @receiver(post_save, sender=Student)
# def update_grade_counts_on_create(sender, instance, created, **kwargs):
#     if created:
#         role = instance.role
        
#         if role == 'STUDENT':
#             # Get the appropriate model for the requesting user's role from the mapping.
#             Model= role_specific_maps.account_access_control_mapping[role]

#             # Build the queryset for the requesting account with the necessary related fields.
#             student = Model.objects.select_related('grade').get(account_id=instance.account_id)
#             grade = student.grade

#             grade.student_count = grade.students.count()
#             grade.save()


# @receiver(pre_delete, sender=BaseUser)
# def update_grade_and_subject_counts_on_delete(sender, instance, **kwargs):
#     role = instance.role

#     if role in ['STUDENT', 'TEACHER']:
#         # Get the appropriate model for the requesting user's role from the mapping.
#         Model = role_specific_maps.account_access_control_mapping[role]

#         if role == 'STUDENT':
#             # Build the queryset for the requesting account with the necessary related fields.
#             deleted_account = Model.objects.select_related('grade').prefetch_related('enrolled_classes').get(account_id=instance.account_id)

#             # Exclude the student being deleted from the count
#             deleted_account.grade.student_count = deleted_account.grade.students.exclude(account_id=instance.account_id).count()
#             deleted_account.grade.save()

#             for classroom in deleted_account.enrolled_classes.all().exclude(subject=None, register_class=True):
#                 if classroom.subject:
#                     # Update the subject student count, excluding the student being deleted
#                     classroom.subject.student_count = classroom.grade.classes.filter(subject=classroom.subject).exclude(students=deleted_account).aggregate(student_count=models.Count('students'))['student_count'] or 0
#                     classroom.subject.save()

#         elif role == 'TEACHER':
#             # Build the queryset for the requesting account with the necessary related fields.
#             deleted_account = Model.objects.prefetch_related('taught_classes').get(account_id=instance.account_id)

#             # Update teacher count for all related subjects, excluding the teacher being deleted
#             for classroom in deleted_account.taught_classes.all().exclude(subject=None, register_class=True):
#                 if classroom.subject:
#                     classroom.subject.teacher_count = classroom.grade.classes.filter(subject=classroom.subject).exclude(teacher=deleted_account).values_list('teacher', flat=True).distinct().count()
#                     classroom.subject.save()


# @receiver(post_save, sender=Classroom)
# def update_subject_counts_on_create(sender, instance, created, **kwargs):
#     if created and instance.subject:
#         # Update the count of classrooms associated with this subject
#         instance.subject.classrooms_count = instance.grade.classrooms.filter(subject=instance.subject).count()

#         # Update the count of unique teachers for this subject
#         if instance.teacher:
#             instance.subject.teacher_count = instance.grade.classrooms.filter(subject=instance.subject).exclude(teacher=None).values_list('teacher', flat=True).distinct().count()

#         # Save the updated subject instance
#         instance.subject.save()


# @receiver(pre_delete, sender=Classroom)
# def update_subject_counts_on_delete(sender, instance, **kwargs):
#     if instance.subject:
#         # Update the count of classrooms associated with this subject, excluding the classroom being deleted
#         instance.subject.classrooms_count = instance.grade.classrooms.filter(subject=instance.subject).exclude(id=instance.id).count()

#         # Update the count of unique teachers for this subject, excluding the classroom being deleted
#         if instance.teacher:
#             instance.subject.teacher_count = instance.grade.classrooms.filter(subject=instance.subject).exclude(id=instance.id).exclude(teacher=None).values_list('teacher', flat=True).distinct().count()

#         # Update the count of students for this subject, excluding the classroom being deleted
#         if instance.students.exists():
#             instance.subject.student_count = instance.grade.classrooms.filter(subject=instance.subject).exclude(id=instance.id).aggregate(student_count=models.Count('students'))['student_count'] or 0

#         # Save the updated subject instance
#         instance.subject.save()
