# django
from django.db.models.signals import post_save
from django.dispatch import receiver

# models
from users.models import BaseUser

# mappings
from users.maps import role_specific_maps


@receiver(post_save, sender=BaseUser)
def update_user_counts_on_create(sender, instance, created, **kwargs):
    if created:
        role = instance.role

        if role in ['PRINCIPAL' ,'ADMIN', 'TEACHER', 'STUDENT']:

            # Get the appropriate model and related fields (select_related and prefetch_related)
            # for the requesting user's role from the mapping.
            Model = role_specific_maps.account_access_control_mapping[role]

            # Build the queryset for the requesting account with the necessary related fields.
            account = Model.objects.select_related('school').only('school').get(account_id=instance.account_id)
            school = account.school

            if role in ['PRINCIPAL', 'ADMIN']:
                school.admin_count = school.principal.count() + school.admins.count()
            elif role == 'STUDENT':
                school.student_count = school.students.count()
            elif role == 'TEACHER':
                school.teacher_count = school.teachers.count()

            school.save()


