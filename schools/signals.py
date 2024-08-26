# django
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

# models
from users.models import BaseUser, Principal, Admin, Teacher, Student


@receiver(post_save, sender=BaseUser)
def update_user_counts_on_create(sender, instance, created, **kwargs):
    if created:
        role = instance.role

        role_mapping = {
            'PRINCIPAL': Principal,
            'ADMIN': Admin,
            'TEACHER': Teacher,
            'STUDENT': Student,
        }

        if role in role_mapping:
            # Fetch the corresponding child model and serializer based on the user's role
            Model = role_mapping[role]
            account = Model.objects.get(account_id=instance.account_id)
            school = account.school

            if role in ['PRINCIPAL', 'ADMIN']:
                school.admin_count = school.principal.count() + school.admins.count()
            elif role == 'STUDENT':
                school.student_count = school.students.count()
            elif role == 'TEACHER':
                school.teacher_count = school.teachers.count()
        else:
            return

        school.save()


