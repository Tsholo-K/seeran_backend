# python 
import uuid

# django
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError

# models
from accounts.models import BaseUser
from schools.models import School


class Announcement(models.Model):
    announcer = models.ForeignKey(BaseUser, on_delete=models.CASCADE, related_name='my_announcements', help_text="User who made the announcement")

    announcement_title = models.CharField(max_length=124, help_text="Title of the announcement")
    announcement_message = models.TextField(max_length=1024, help_text="Message of the announcement")

    accounts_reached = models.ManyToManyField(BaseUser, help_text="All users who have seen the announcement")
   
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='announcements', help_text="School related to the announcement")

    announced_at = models.DateTimeField(auto_now_add=True, help_text="Time when the announcement was made")
    announcement_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)

    def __str__(self):
        return self.title

    class Meta:
        ordering = ['-announced_at']

    def reached(self, user):
        try:
            requesting_account = BaseUser.objects.get(account_id=user)
            
            # Only add if the user hasn't been added before
            if not self.accounts_reached.filter(id=requesting_account.id).exists():
                self.accounts_reached.add(requesting_account)

        except BaseUser.DoesNotExist:
            # Handle the case where the base user account does not exist.
            raise ValidationError(_('Could not process your request, an account with the provided credentials does not exist. Error updating announcement reached status.. Please check the account details and try again.'))
