# django imports
from django.db import models, IntegrityError
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError

# models
from permission_groups.models import AdminPermissionGroup, TeacherPermissionGroup


class AdminAccountPermission(models.Model):
    """
    Represents the permissions granted to administrators within the system.
    Each permission is associated with a specific action and target model, 
    allowing for granular control over what administrators can do.
    """

    # Defining the possible actions that can be performed
    ACTION_CHOICES = [
        ('CREATE', 'Create'),       # Permission to create a new entity
        ('UPDATE', 'Update'),       # Permission to modify an existing entity
        ('VIEW', 'View'),           # Permission to view an entity
        ('ASSIGN', 'Assign'),       # Permission to assign an entity to another entity
        ('DELETE', 'Delete'),       # Permission to remove an entity
        ('SUBMIT', 'Submit'),       # Permission to finalize an entry
        ('GENERATE', 'Generate'),   # Permission to create reports or documents
        ('LINK', 'Link'),           # Permission to associate related entities
        ('UNLINK', 'Unlink'),       # Permission to remove associations between entities
    ]

    # Defining the possible target models that can be affected by actions
    TARGET_MODEL_CHOICES = [
        ('ACCOUNT', 'Account'),                     # User accounts
        ('PERMISSION', 'Permission'),               # Permission settings
        ('AUDIT_ENTRY', 'Audit Entry'),             # Audit Entries
        ('ANNOUNCEMENT', 'Announcement'),           # School announcements
        ('GRADE', 'Grade'),                         # Grade-related actions
        ('TERM', 'Term'),                           # Academic terms
        ('SUBJECT', 'Subject'),                     # Subjects offered
        ('PROGRESS_REPORT', 'Progress Report'),     # Student progress reports
        ('CLASSROOM', 'Classroom'),                 # Classroom settings
        ('ATTENDANCE', 'Attendance'),               # Attendance records
        ('ACTIVITY', 'Activity'),                   # Student Activity
        ('ASSESSMENT', 'Assessment'),               # Assessments and tests
        ('TRANSCRIPT', 'Transcript'),               # Student transcripts
        ('TIMETABLE', 'Timetable'),                 # Timetable
        ('GROUP_TIMETABLE', 'Group Timetable'),     # Timetables for groups of students
        ('TEACHER_TIMETABLE', 'Teacher Timetable'), # Individual teacher schedules
    ]

    # Foreign key linking to the permission group
    linked_permission_group = models.ForeignKey(AdminPermissionGroup, on_delete=models.CASCADE, related_name='permissions')

    # Field to store the action associated with the permission
    action = models.CharField(max_length=64, choices=ACTION_CHOICES)

    # Field to store the target model associated with the permission
    target_model = models.CharField(max_length=64, choices=TARGET_MODEL_CHOICES)

    # Boolean field to indicate if the permission can be executed
    can_execute = models.BooleanField(default=True)

    class Meta:
        # Ensures that the combination of permission group, action, and target model is unique
        unique_together = ('linked_permission_group', 'action', 'target_model')

    def __str__(self):
        # String representation of the permission instance
        return f"can {self.action} on {self.target_model}"

    def save(self, *args, **kwargs):
        """
        Overrides the default save method to implement custom validation 
        and ensure unique permissions for each permission group.
        """
        self.clean()  # Calls the clean method to validate the instance
        try:
            super().save(*args, **kwargs)  # Calls the parent class's save method
        except IntegrityError as e:
            # Handle unique constraint violation on permissions
            if 'unique constraint' in str(e).lower():
                raise ValidationError(_('Could not process your request, the provided permission group contains duplicate permissions. Please review the group\'s permissions and try again.'))
            else:
                raise e  # Re-raise the exception if it's a different IntegrityError

    def clean(self):
        """
        Custom validation method to ensure the integrity of the model's data.
        """
        if self.action not in dict(self.ACTION_CHOICES).keys():
            raise ValidationError(_('The specified action is not valid. Please check the available permission actions and ensure your input is correct.'))

        if self.target_model not in dict(self.TARGET_MODEL_CHOICES).keys():
            raise ValidationError(_('The specified target entity is invalid. Please verify the available target entities and ensure your input is correct.'))


class TeacherAccountPermission(models.Model):
    """
    Represents the permissions granted to teachers within the system.
    Similar to the AdminPermission model but tailored for teacher roles,
    with specific actions and target models relevant to their responsibilities.
    """

    # Defining the possible actions that can be performed by teachers
    ACTION_CHOICES = [
        ('CREATE', 'Create'),  # Permission to create new assessments or records
        ('UPDATE', 'Update'),  # Permission to modify existing assessments or records
        ('VIEW', 'View'),      # Permission to view assessments or records
        ('DELETE', 'Delete'),  # Permission to remove assessments or records
        ('SUBMIT', 'Submit'),  # Permission to finalize and submit records
        ('GENERATE', 'Generate'),   # Permission to create reports or documents
    ]

    # Defining the possible target models that can be affected by actions
    TARGET_MODEL_CHOICES = [
        ('ACCOUNT', 'Account'),         # User accounts
        ('PROGRESS_REPORT', 'Progress Report'),     # Student progress reports
        ('CLASSROOM', 'Classroom'),                 # Classroom settings
        ('ATTENDANCE', 'Attendance'),   # Related to attendance records
        ('ASSESSMENT', 'Assessment'),  # Related to assessments given to students
        ('TRANSCRIPT', 'Transcript'),   # Related to student transcripts
        ('ACTIVITY', 'Activity'),       # Student Activity
        ('TIMETABLE', 'Timetable'),       # Timetable
        ('GROUP_TIMETABLE', 'Group Timetable'),     # Timetables for groups of students
    ]

    # Foreign key linking to the teacher permission group
    linked_permission_group = models.ForeignKey(TeacherPermissionGroup, on_delete=models.CASCADE, related_name='permissions')

    # Field to store the action associated with the permission
    action = models.CharField(max_length=64, choices=ACTION_CHOICES)

    # Field to store the target model associated with the permission
    target_model = models.CharField(max_length=64, choices=TARGET_MODEL_CHOICES)

    # Boolean field to indicate if the permission can be executed
    can_execute = models.BooleanField(default=True)

    class Meta:
        # Ensures that the combination of permission group, action, and target model is unique
        unique_together = ('linked_permission_group', 'action', 'target_model')

    def __str__(self):
        # String representation of the permission instance
        return f"can {self.action} on {self.target_model}"

    def save(self, *args, **kwargs):
        """
        Overrides the default save method to implement custom validation 
        and ensure unique permissions for each permission group.
        """
        self.clean()  # Calls the clean method to validate the instance
        try:
            super().save(*args, **kwargs)  # Calls the parent class's save method
        except IntegrityError as e:
            # Handle unique constraint violation on permissions
            if 'unique constraint' in str(e).lower():
                raise ValidationError(_('Could not process your request, the provided permission group contains duplicate permissions. Please review the group\'s permissions and try again.'))
            else:
                raise e  # Re-raise the exception if it's a different IntegrityError

    def clean(self):
        """
        Custom validation method to ensure the integrity of the model's data.
        """
        if self.action not in dict(self.ACTION_CHOICES).keys():
            raise ValidationError(_('The specified action is not valid. Please check the available permission actions and ensure your input is correct.'))

        if self.target_model not in dict(self.TARGET_MODEL_CHOICES).keys():
            raise ValidationError(_('The specified target entity is invalid. Please verify the available target entities and ensure your input is correct.'))

