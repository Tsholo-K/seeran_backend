# python 
import uuid

# django
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError

# models
from accounts.models import BaseAccount
from schools.models import School


class Announcement(models.Model):
    announcer = models.ForeignKey(BaseAccount, on_delete=models.SET_NULL, related_name='my_announcements', null=True, help_text="User who made the announcement")

    announcement_title = models.CharField(max_length=124, help_text="Title of the announcement")
    announcement_message = models.TextField(max_length=1024, help_text="Message of the announcement")

    accounts_reached = models.ManyToManyField(BaseAccount, help_text="All users who have seen the announcement")
   
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='announcements', help_text="School related to the announcement")

    timestamp = models.DateTimeField(auto_now_add=True, help_text="Time when the announcement was made")
    announcement_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)

    def __str__(self):
        return self.title

    class Meta:
        ordering = ['-timestamp']

    def reached(self, user):
        try:
            # Only add if the user hasn't been added before
            if not self.accounts_reached.filter(account_id=user).exists():
                requesting_account = BaseAccount.objects.get(account_id=user)
                self.accounts_reached.add(requesting_account)

        except BaseAccount.DoesNotExist:
            # Handle the case where the base user account does not exist.
            raise ValidationError(_('Could not process your request, an account with the provided credentials does not exist. Error updating announcement reached status.. Please check the account details and try again.'))


"""
    [
        {
            'announcer': 'John Smith',
            'announcement_title': 'School Holiday Announcement',
            'announcement_message': 'Please note that the school will be closed on Monday due to a public holiday.',
            'school': 'Green Valley High',
            'timestamp': datetime.datetime(2024, 10, 16, 16, 38, 5, 786910),
            'announcement_id': '728d6ae3-84ab-452c-ac26-c1b2a01ed80e'
        },
        {
            'announcer': 'Sarah Johnson',
            'announcement_title': 'New Curriculum Launch',
            'announcement_message': 'We are excited to announce a new curriculum for the upcoming term.',
            'school': 'Sunrise Academy',
            'timestamp': datetime.datetime(2024, 10, 16, 16, 38, 5, 787036),
            'announcement_id': '6451b230-46ca-4410-9394-7e92709f6740'
        },
        {
            'announcer': 'Michael Williams',
            'announcement_title': 'Parent-Teacher Meeting',
            'announcement_message': 'A Parent-Teacher meeting will be held this Friday at 10 AM in the main hall.',
            'school': 'Riverside School',
            'timestamp': datetime.datetime(2024, 10, 16, 16, 38, 5, 787094),
            'announcement_id': '5ed18dcc-1160-4e0b-90a9-454d80559587'
        },
        {
            'announcer': 'Emily Brown',
            'announcement_title': 'Extracurricular Activities Update',
            'announcement_message': 'We have updated our extracurricular activities for the new semester.',
            'school': 'Hilltop Primary',
            'timestamp': datetime.datetime(2024, 10, 16, 16, 38, 5, 787154),
            'announcement_id': '9b9b12bb-497b-4641-a323-19d75c0a86c5'
        },
        {
            'announcer': 'David Davis',
            'announcement_title': 'School Closure Due to Weather',
            'announcement_message': 'Due to inclement weather, the school will be closed tomorrow.',
            'school': 'Oakwood College',
            'timestamp': datetime.datetime(2024, 10, 16, 16, 38, 5, 787168),
            'announcement_id': 'cdec8922-63cd-4522-8573-2c8f71941f40'
        },
        {
            'announcer': 'Jessica Wilson',
            'announcement_title': 'Sports Day Announcement',
            'announcement_message': 'Join us for Sports Day on Saturday. All students are encouraged to participate.',
            'school': 'Silver Springs School',
            'timestamp': datetime.datetime(2024, 10, 16, 16, 38, 5, 787181),
            'announcement_id': '997fd454-b8ee-405b-aa27-d4a34ddbf084'
        },
        {
            'announcer': 'Daniel Miller',
            'announcement_title': 'Exam Schedule',
            'announcement_message': 'The exam schedule has been updated and posted on the noticeboard.',
            'school': 'Lakeview Secondary',
            'timestamp': datetime.datetime(2024, 10, 16, 16, 38, 5, 787191),
            'announcement_id': '0b99d57d-54f1-46f1-be0b-3598be372ea5'
        },
        {
            'announcer': 'Olivia Taylor',
            'announcement_title': 'Uniform Policy Update',
            'announcement_message': 'Please be informed that the school uniform policy has been updated. Refer to the school website for details.',
            'school': 'Westbrook Institute',
            'timestamp': datetime.datetime(2024, 10, 16, 16, 38, 5, 787206),
            'announcement_id': '4035a1ed-7e29-433c-9f23-7d5b964075b4'
        },
        {
            'announcer': 'James Anderson',
            'announcement_title': 'COVID-19 Safety Guidelines',
            'announcement_message': 'Here are the updated COVID-19 safety protocols for the school.',
            'school': 'Maple Grove School',
            'timestamp': datetime.datetime(2024, 10, 16, 16, 38, 5, 787239),
            'announcement_id': '91466334-bc8c-4a71-b3ff-a8f944f01a30'
        },
        {
            'announcer': 'Sophia Moore',
            'announcement_title': 'New School Canteen Menu',
            'announcement_message': 'We are happy to introduce a new, healthier menu at the school canteen.',
            'school': 'Bright Future Academy',
            'timestamp': datetime.datetime(2024, 10, 16, 16, 38, 5, 787251),
            'announcement_id': '06a31072-05e3-4a00-aac6-167a780461b4'
        }
    ]
"""