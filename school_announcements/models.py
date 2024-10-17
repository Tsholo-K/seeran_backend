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
            'announcement_message': 'Dear Students and Parents, we are excited to inform you that the school will be closed this coming Monday in observance of a public holiday. This is a perfect opportunity to spend quality time with your family and recharge for the upcoming week. Enjoy your day off, and we look forward to seeing everyone back in class on Tuesday, bright-eyed and ready to learn!',
            'school': 'Green Valley High',
            'timestamp': datetime.datetime(2024, 10, 16, 16, 38, 5, 786910),
            'announcement_id': '728d6ae3-84ab-452c-ac26-c1b2a01ed80e'
        },
        {
            'announcer': 'Sarah Johnson',
            'announcement_title': 'New Curriculum Launch',
            'announcement_message': 'We are thrilled to announce the launch of our new curriculum for the upcoming term! After careful planning and consideration, we have revamped our educational approach to better align with modern learning techniques. This new curriculum promises to provide a more engaging and holistic learning experience for all students. We invite all parents to attend the upcoming informational meeting next Wednesday at 5 PM to learn more about what’s in store. Together, we can make this transition seamless and beneficial for our students!',
            'school': 'Sunrise Academy',
            'timestamp': datetime.datetime(2024, 10, 16, 16, 38, 5, 787036),
            'announcement_id': '6451b230-46ca-4410-9394-7e92709f6740'
        },
        {
            'announcer': 'Michael Williams',
            'announcement_title': 'Parent-Teacher Meeting',
            'announcement_message': 'Attention Parents! We are pleased to invite you to our upcoming Parent-Teacher meeting scheduled for this Friday at 10 AM in the main hall. This is an excellent opportunity to discuss your child's progress, share your insights, and collaborate with teachers to ensure your child's success in school. Your involvement is crucial, and we look forward to seeing as many of you there as possible. Thank you for your continued support in making our school a wonderful place for learning!',
            'school': 'Riverside School',
            'timestamp': datetime.datetime(2024, 10, 16, 16, 38, 5, 787094),
            'announcement_id': '5ed18dcc-1160-4e0b-90a9-454d80559587'
        },
        {
            'announcer': 'Emily Brown',
            'announcement_title': 'Extracurricular Activities Update',
            'announcement_message': 'Hello, Students! We are excited to announce that we have revamped our extracurricular activities for the new semester! From sports teams to art clubs, there’s something for everyone. We believe these activities are vital for personal growth and social development, so we encourage every student to participate. Detailed schedules and registration information will be available on our website by the end of this week. Let’s make this semester vibrant and full of opportunities!',
            'school': 'Hilltop Primary',
            'timestamp': datetime.datetime(2024, 10, 16, 16, 38, 5, 787154),
            'announcement_id': '9b9b12bb-497b-4641-a323-19d75c0a86c5'
        },
        {
            'announcer': 'David Davis',
            'announcement_title': 'School Closure Due to Weather',
            'announcement_message': 'Dear Families, due to the forecast of severe weather conditions, we regret to inform you that the school will be closed tomorrow for the safety of our students and staff. Please stay tuned for updates as the situation develops, and ensure that you keep your children safe at home. Thank you for your understanding and cooperation as we prioritize the well-being of our school community. Stay safe!',
            'school': 'Oakwood College',
            'timestamp': datetime.datetime(2024, 10, 16, 16, 38, 5, 787168),
            'announcement_id': 'cdec8922-63cd-4522-8573-2c8f71941f40'
        },
        {
            'announcer': 'Jessica Wilson',
            'announcement_title': 'Sports Day Announcement',
            'announcement_message': 'Exciting news, everyone! We are thrilled to announce our annual Sports Day event happening this Saturday! All students are encouraged to participate in a variety of athletic competitions, games, and fun activities. It’s a fantastic way to showcase your talents and cheer on your classmates. Parents, we invite you to join us in supporting our young athletes and enjoying a day full of excitement and community spirit. Don’t forget to bring your enthusiasm and school spirit!',
            'school': 'Silver Springs School',
            'timestamp': datetime.datetime(2024, 10, 16, 16, 38, 5, 787181),
            'announcement_id': '997fd454-b8ee-405b-aa27-d4a34ddbf084'
        },
        {
            'announcer': 'Daniel Miller',
            'announcement_title': 'Exam Schedule',
            'announcement_message': 'Attention Students! The updated exam schedule has been finalized and is now posted on the noticeboard. We encourage all students to review it carefully and prepare accordingly. Remember, adequate preparation is key to success. If you have any questions or concerns regarding your exam schedules, please feel free to reach out to your teachers for guidance. Good luck with your studies, and aim high!',
            'school': 'Lakeview Secondary',
            'timestamp': datetime.datetime(2024, 10, 16, 16, 38, 5, 787191),
            'announcement_id': '0b99d57d-54f1-46f1-be0b-3598be372ea5'
        },
        {
            'announcer': 'Olivia Taylor',
            'announcement_title': 'Uniform Policy Update',
            'announcement_message': 'Dear Parents and Students, we would like to inform you that the school uniform policy has been updated to reflect our commitment to creating a positive and professional learning environment. Please refer to the school website for detailed information regarding the changes and new requirements. We appreciate your cooperation in ensuring that all students adhere to the uniform guidelines. Together, let’s foster a sense of pride and community within our school!',
            'school': 'Westbrook Institute',
            'timestamp': datetime.datetime(2024, 10, 16, 16, 38, 5, 787206),
            'announcement_id': '4035a1ed-7e29-433c-9f23-7d5b964075b4'
        },
        {
            'announcer': 'James Anderson',
            'announcement_title': 'COVID-19 Safety Guidelines',
            'announcement_message': 'In light of ongoing health concerns, we want to remind all students and staff about the updated COVID-19 safety protocols that are now in effect. Please take the time to review these guidelines to ensure a safe environment for everyone at our school. Compliance with these measures is crucial for the health and safety of our community. Thank you for your diligence and support in keeping our school safe!',
            'school': 'Maple Grove School',
            'timestamp': datetime.datetime(2024, 10, 16, 16, 38, 5, 787239),
            'announcement_id': '91466334-bc8c-4a71-b3ff-a8f944f01a30'
        },
        {
            'announcer': 'Sophia Moore',
            'announcement_title': 'New School Canteen Menu',
            'announcement_message': 'We are delighted to introduce a brand-new, healthier menu at the school canteen, designed to provide our students with nutritious and delicious options. From fresh salads to wholesome sandwiches, there’s something for everyone! We believe that healthy eating plays a vital role in student well-being and academic success. Please encourage your children to try the new menu items, and let’s work together towards healthier habits!',
            'school': 'Bright Future Academy',
            'timestamp': datetime.datetime(2024, 10, 16, 16, 38, 5, 787251),
            'announcement_id': '06a31072-05e3-4a00-aac6-167a780461b4'
        }
    ]
"""