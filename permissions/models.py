# python 
import uuid

# django imports
from django.db import models, IntegrityError
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError

# models
from users.models import Admin, Teacher
from schools.models import School

# utility functions



class AdminPermissionGroup(models.Model):
    name = models.CharField(max_length=64)
    description = models.TextField(blank=True, null=True)

    actors = models.ManyToManyField(Admin, related_name='permissions')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='permission_groups')

    permission_group_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)

    class Meta:
        unique_together = ('name', 'school')

    def __str__(self):
        return f"{self.name} - {self.school.name}"

    def save(self, *args, **kwargs):
        self.clean()
        
        try:
            super().save(*args, **kwargs)

        except IntegrityError as e:
            # Handle unique constraint violation on the email field
            if 'unique constraint' in str(e).lower():
                raise ValidationError(_('a permission group with the provided name already exists for your school, please pick a different name'))
            else:
                raise e  # Re-raise the exception if it's a different IntegrityError


class AdminPermission(models.Model):

    ACTION_CHOICES = [
        ('CREATE', 'Create'),
        ('UPDATE', 'Update'),
        ('DELETE', 'Delete'),
        ('SUBMIT', 'Submit'),
        ('GRADE', 'Grade'),
        ('LINK', 'Link'),
        ('UNLINK', 'Unlink'),
    ]

    TARGET_MODEL_CHOICES = [
        ('ACCOUNT', 'Account'),
        ('GRADE', 'Grade'),
        ('TERM', 'Term'),
        ('SUBJECT', 'Subject'),
        ('CLASSROOM', 'Classroom'),
        ('ATTENDANCE', 'Attendance'),
        ('ANNOUNCEMENT', 'Announcement'),
        ('ASSESSMENT', 'Assessment'),
        ('DAILY_SCHEDULE', 'Daily Schedule'),
        ('GROUP_TIMETABLE', 'Group Timetable'),
        ('TEACHER_TIMETABLE', 'Teacher Timetable'),
    ]

    permission_group = models.ForeignKey(AdminPermissionGroup, on_delete=models.CASCADE, related_name='permissions')

    action = models.CharField(max_length=64, choices=ACTION_CHOICES)

    target_model = models.CharField(max_length=64, choices=TARGET_MODEL_CHOICES)

    can_execute = models.BooleanField(default=True)

    class Meta:
        ...

    def __str__(self):
        return f"can {self.action} on {self.target_model}"
    

class TeacherPermissionGroup(models.Model):
    name = models.CharField(max_length=64)
    description = models.TextField(blank=True, null=True)

    actors = models.ManyToManyField(Teacher, related_name='permissions')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='permission_groups')

    permission_group_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)

    class Meta:
        unique_together = ('name', 'school')

    def __str__(self):
        return f"{self.name} - {self.school.name}"

    def save(self, *args, **kwargs):
        self.clean()
        
        try:
            super().save(*args, **kwargs)

        except IntegrityError as e:
            # Handle unique constraint violation on the email field
            if 'unique constraint' in str(e).lower():
                raise ValidationError(_('a permission group with the provided name already exists for your school, please pick a different name'))
            else:
                raise e  # Re-raise the exception if it's a different IntegrityError



class TeacherPermission(models.Model):

    ACTION_CHOICES = [
        ('CREATE', 'Create'),
        ('UPDATE', 'Update'),
        ('DELETE', 'Delete'),
        ('SUBMIT', 'Submit'),
        ('GRADE', 'Grade'),
    ]

    TARGET_MODEL_CHOICES = [
        ('ASSESSMENT', 'Assessment'),
        ('ATTENDANCE', 'Attendance'),
    ]

    permission_group = models.ForeignKey(TeacherPermissionGroup, on_delete=models.CASCADE, related_name='permissions')

    action = models.CharField(max_length=64, choices=ACTION_CHOICES)

    target_model = models.CharField(max_length=64, choices=TARGET_MODEL_CHOICES)

    can_execute = models.BooleanField(default=True)

    class Meta:
        ...

    def __str__(self):
        return f"can {self.action} on {self.target_model}"
