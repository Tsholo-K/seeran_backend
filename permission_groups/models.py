# python 
import uuid

# django imports
from django.db import models, IntegrityError
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError


class AdminPermissionGroup(models.Model):
    """
    Represents a group of permissions assigned to administrators in a school.
    Each permission group can contain multiple permissions and can be linked
    to multiple subscribers (admins). This model facilitates the management 
    of admin roles and their associated permissions within a school.
    """

    group_name = models.CharField(max_length=64)
    description = models.TextField(blank=True, null=True)

    # Many-to-many relationship with the Admin model, allowing multiple admins
    # to be linked to this permission group
    subscribers = models.ManyToManyField('accounts.Admin', related_name='permissions')

    # Counters for tracking the number of subscribers and permissions
    subscribers_count = models.IntegerField(default=0)
    permissions_count = models.IntegerField(default=0)

    # Foreign key linking this permission group to a specific school
    school = models.ForeignKey('schools.School', on_delete=models.CASCADE, related_name='admin_permission_groups')

    last_updated = models.DateTimeField(auto_now=True)  # Automatically set to now when the object is updated
    
    timestamp = models.DateTimeField(auto_now_add=True)
    permission_group_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)  # Unique identifier for the permission group

    class Meta:
        unique_together = ('group_name', 'school')  # Ensure unique group name per school

    def __str__(self):
        # String representation of the permission group instance
        return f"{self.group_name} - {self.school.name}"

    def save(self, *args, **kwargs):
        """
        Overrides the default save method to implement custom validation 
        and ensure unique permission groups for each school.
        """
        self.clean()  # Calls the clean method to validate the instance
        try:
            super().save(*args, **kwargs)  # Calls the parent class's save method
        except IntegrityError as e:
            # Handle unique constraint violation on group name
            if 'unique constraint' in str(e).lower():
                raise ValidationError(_('Could not process your request, an admin permission group with the provided group name already exists for your school. Please choose a different group name and try again.'))
            else:
                raise e  # Re-raise the exception if it's a different IntegrityError
        except Exception as e:
            raise ValidationError(_(str(e)))

    def clean(self):
        """
        Custom validation method to ensure the integrity of the model's data.
        """
        if not self.group_name:
            raise ValidationError(_('Could not process your request, every permission group should have a group name. Please provide a name for the group and try again.'))
        
        if len(self.group_name) > 64:  # Ensure group name length is valid
            raise ValidationError(_('Could not process your request, the maximum group name length is 64 characters. Please update the name of the group to fall under this length and try again.'))
        
        self.permissions_count = self.permissions.count()

    def update_subscribers(self, subscribers_list=None, subscribe=False):
        try:
            if subscribers_list:
                if subscribe:
                    # Check if subscribers are already in the group
                    if self.subscribers.exists():
                        subscribers_in_the_group = self.subscribers.filter(account_id__in=subscribers_list).values_list('surname', 'name')
                        if subscribers_in_the_group.exists():
                            subscriber_names = [f"{surname} {name}" for surname, name in subscribers_in_the_group]
                            raise ValidationError(f'Could not process your request, the following admins are already assigned to this permission group: {", ".join(subscriber_names)}.')
                        
                    # Retrieve CustomUser instances corresponding to the account_ids
                    subscribers = self.school.admins.filter(account_id__in=subscribers_list)
                    self.subscribers.add(*subscribers)

                else:
                    # Check if students to be removed are actually in the class
                    subscribers = self.subscribers.filter(account_id__in=subscribers_list).values_list('account_id', flat=True)
                    if not subscribers:
                        raise ValidationError("could not proccess your request, cannot remove accounts from the group. None of the provided admins are part of this permission group.")

                    self.subscribers.remove(*subscribers)

                # Save the classroom instance first to ensure student changes are persisted
                self.subscribers_count = self.subscribers.count()
                self.save()
                
            else:
                raise ValidationError("Could not proccess your request, no admins were provided to be added or removed from the permission group. Please provide a valid list of admins and try again")

        except Exception as e:
            raise ValidationError(_(str(e)))


class TeacherPermissionGroup(models.Model):
    """
    Represents a group of permissions assigned to teachers in a school.
    Each permission group can contain multiple permissions and can be linked
    to multiple subscribers (teachers). This model facilitates the management 
    of teacher roles and their associated permissions within a school.
    """

    group_name = models.CharField(max_length=64)
    description = models.TextField(blank=True, null=True)

    # Many-to-many relationship with the Teacher model, allowing multiple teachers
    # to be linked to this permission group
    subscribers = models.ManyToManyField('accounts.Teacher', related_name='permissions')
    
    # Counters for tracking the number of subscribers and permissions
    subscribers_count = models.IntegerField(default=0)
    permissions_count = models.IntegerField(default=0)

    # Foreign key linking this permission group to a specific school
    school = models.ForeignKey('schools.School', on_delete=models.CASCADE, related_name='teacher_permission_groups')
    
    last_updated = models.DateTimeField(auto_now=True)  # Automatically set to now when the object is updated

    timestamp = models.DateTimeField(auto_now_add=True)
    permission_group_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)  # Unique identifier for the permission group

    class Meta:
        unique_together = ('group_name', 'school')  # Ensure unique group name per school

    def __str__(self):
        # String representation of the permission group instance
        return f"{self.group_name} - {self.school.name}"

    def save(self, *args, **kwargs):
        """
        Overrides the default save method to implement custom validation 
        and ensure unique permission groups for each school.
        """
        self.clean()  # Calls the clean method to validate the instance
        try:
            super().save(*args, **kwargs)  # Calls the parent class's save method
        except IntegrityError as e:
            # Handle unique constraint violation on group name
            if 'unique constraint' in str(e).lower():
                raise ValidationError(_('Could not process your request, a teacher permission group with the provided group name already exists for your school. Please choose a different group name and try again.'))
            else:
                raise e  # Re-raise the exception if it's a different IntegrityError
        except Exception as e:
            raise ValidationError(_(str(e)))

    def clean(self):
        """
        Custom validation method to ensure the integrity of the model's data.
        """
        if not self.group_name:
            raise ValidationError(_('Could not process your request, every permission group should have a group name. Please provide a name for the group and try again.'))
        
        if len(self.group_name) > 64:  # Ensure group name length is valid
            raise ValidationError(_('Could not process your request, the maximum group name length is 64 characters. Please update the name of the group to fall under this length and try again.'))

    def update_counts(self):
        self.subscribers_count = self.subscribers.count()
        self.permissions_count = self.permissions.count()
        self.save()

    def update_subscribers(self, subscribers_list=None, subscribe=False):
        try:
            if subscribers_list:
                if subscribe:
                    # Check if subscribers are already in the group
                    if self.subscribers.exists():
                        subscribers_in_the_group = self.subscribers.filter(account_id__in=subscribers_list).values_list('surname', 'name')
                        if subscribers_in_the_group.exists():
                            subscriber_names = [f"{surname} {name}" for surname, name in subscribers_in_the_group]
                            raise ValidationError(f'Could not process your request, the following teachers are already assigned to this permission group: {", ".join(subscriber_names)}.')
                        
                    # Retrieve CustomUser instances corresponding to the account_ids
                    subscribers = self.school.teachers.filter(account_id__in=subscribers_list)
                    self.subscribers.add(*subscribers)

                else:
                    # Check if students to be removed are actually in the class
                    subscribers = self.subscribers.filter(account_id__in=subscribers_list).values_list('account_id', flat=True)
                    if not subscribers:
                        raise ValidationError("could not proccess your request, cannot remove accounts from the group. None of the provided teachers are part of this permission group.")

                    self.subscribers.remove(*subscribers)

                # Save the classroom instance first to ensure student changes are persisted
                self.save()
                
            else:
                raise ValidationError("Could not proccess your request, no teacchers were provided to be added or removed from the permission group. Please provide a valid list of teachers and try again")

        except Exception as e:
            raise ValidationError(_(str(e)))



