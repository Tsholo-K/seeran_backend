# python 
import uuid

# django
from django.db import models
from django.utils.translation import gettext_lazy as _

# models
from users.models import BaseUser
from schools.models import School


class Announcement(models.Model):
    announcer = models.ForeignKey(BaseUser, on_delete=models.CASCADE, related_name='my_announcements', help_text="User who made the announcement")
    announced_at = models.DateTimeField(auto_now_add=True, help_text="Time when the announcement was made")

    title = models.CharField(max_length=124, help_text="Title of the announcement")
    message = models.TextField(max_length=1024, help_text="Message of the announcement")

    reached = models.ManyToManyField(BaseUser, help_text="All users who have seen the announcement")
   
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='announcements', help_text="School related to the announcement")

    announcement_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)

    def __str__(self):
        return self.title

    class Meta:
        ordering = ['-announced_at']

