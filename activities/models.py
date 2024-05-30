# python 
import uuid

# django 
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.db import IntegrityError

# models
from users.models import CustomUser
from schools.models import School
from classes.models import Classroom


class Activity(models.Model):
    
    logger = models.ForeignKey(CustomUser, on_delete=models.DO_NOTHING, related_name='logged_activities')
    recipient = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='received_activities')

    offence = models.CharField(_('offence'), max_length=2)
    message = models.TextField(_('message'), max_length=300)

    date_logged = models.DateTimeField(auto_now_add=True)
    
    classroom = models.ForeignKey(Classroom, on_delete=models.DO_NOTHING, related_name='classroom_activities', null=True, blank=True)
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='school_activities')

    # activity account id 
    activity_id = models.CharField(max_length=15, unique=True)

    class Meta:
        verbose_name = _('classroom')
        verbose_name_plural = _('classrooms')

    def __str__(self):
        return self.name

    # class account id creation handler
    def save(self, *args, **kwargs):
        if not self.activity_id:
            self.activity_id = self.generate_unique_account_id('AI')

        attempts = 0
        while attempts < 5:
            try:
                super().save(*args, **kwargs)
                break
            except IntegrityError:
                self.activity_id = self.generate_unique_account_id('AI') # Activity ID
                attempts += 1
        if attempts >= 5:
            raise ValueError('Could not create activity with unique account ID after 5 attempts. Please try again later.')

    @staticmethod
    def generate_unique_account_id(prefix=''):
        while True:
            unique_part = uuid.uuid4().hex
            account_id = prefix + unique_part
            account_id = account_id[:15].ljust(15, '0')

            if not Activity.objects.filter(activity_id=account_id).exists():
                return account_id
