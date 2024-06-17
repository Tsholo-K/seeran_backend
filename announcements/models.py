# python 
import uuid

# django
from django.db import models

# models
from schools.models import School
from users.models import CustomUser


class Announcement(models.Model):

    title = models.CharField(max_length=200, help_text="Title of the announcement")
    message = models.TextField(max_length=1024, help_text="Message of the announcement")

    announcement_date = models.DateField(null=True, blank=True, help_text="Date of the announcement")

    announced_at = models.DateTimeField(auto_now_add=True, help_text="Datetime when the announcement was made")
    announce_by = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='my_announcements', help_text="User who made the announcement")
   
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='school_announcements', help_text="School related to the announcement")

    announcement_id = models.CharField(max_length=15, unique=True)

    def __str__(self):
        return self.title

    # annoumcement id creation handler
    def save(self, *args, **kwargs):
        if not self.announcement_id:
            self.announcement_id = self.generate_unique_id('AN')

        super(Announcement, self).save(*args, **kwargs)

    @staticmethod
    def generate_unique_id(prefix=''):
     
        max_attempts = 10
      
        for _ in range(max_attempts):
            unique_part = uuid.uuid4().hex[:13]  # Take only the first 13 characters
            id = f"{prefix}{unique_part}"
            if not Announcement.objects.filter(announcement_id=id).exists():
                return id
        raise ValueError('failed to generate a unique announcement ID after 10 attempts, please try again later.')

