# django
from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver

# models
from accounts.models import BaseAccount


# @receiver(post_save, sender=BaseUser)
# def update_user_counts_on_create(sender, instance, created, **kwargs):
#     if created:
#         role = instance.role

#         if role in ['PRINCIPAL', 'ADMIN', 'TEACHER', 'STUDENT']:
#             # Get the appropriate model for the created user's role from the mapping.
#             Model = role_specific_maps.account_access_control_mapping[role]

#             # Build the queryset for the requesting account with the necessary related fields.
#             created_account = Model.objects.select_related('school').get(account_id=instance.account_id)

#             if role in ['PRINCIPAL', 'ADMIN']:
#                 created_account.school.admin_count = created_account.school.principal.count() + created_account.school.admins.count()
#             elif role == 'STUDENT':
#                 created_account.school.student_count = created_account.school.students.count()
#             elif role == 'TEACHER':
#                 created_account.school.teacher_count = created_account.school.teachers.count()

#             created_account.school.save()


# @receiver(pre_delete, sender=BaseUser)
# def update_user_counts_on_delete(sender, instance, **kwargs):
#     role = instance.role

#     if role in ['PRINCIPAL', 'ADMIN', 'TEACHER', 'STUDENT']:
#         # Get the appropriate model for the deleted user's role from the mapping.
#         Model = role_specific_maps.account_access_control_mapping[role]

#         # Retrieve the account being deleted with the necessary related fields.
#         deleted_account = Model.objects.select_related('school').get(account_id=instance.account_id)

#         if role in ['PRINCIPAL', 'ADMIN']:
#             # Update the admin count, excluding the account being deleted
#             deleted_account.school.admin_count = deleted_account.school.principal.exclude(account_id=instance.account_id).count() + deleted_account.school.admins.exclude(account_id=instance.account_id).count()
#         elif role == 'STUDENT':
#             # Update the student count, excluding the student being deleted
#             deleted_account.school.student_count = deleted_account.school.students.exclude(account_id=instance.account_id).count()
#         elif role == 'TEACHER':
#             # Update the teacher count, excluding the teacher being deleted
#             deleted_account.school.teacher_count = deleted_account.school.teachers.exclude(account_id=instance.account_id).count()

#         # Save the updated school instance
#         deleted_account.school.save()
