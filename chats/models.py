# python 
import uuid

# django 
from django.db import models
from django.utils.translation import gettext_lazy as _

# models
from users.models import CustomUser


class ChatRoom(models.Model):
    user_one = models.ForeignKey(CustomUser, on_delete=models.DO_NOTHING, related_name='user_one')
    user_two = models.ForeignKey(CustomUser, on_delete=models.DO_NOTHING, related_name='user_two')

    chatroom_id = models.CharField(max_length=15, unique=True)

    def __str__(self):
        return f"Chat between {self.user_one.surname + ' ' + self.user_one.name} and {self.user_two.surname + ' ' + self.user_two.name}"
    
    def save(self, *args, **kwargs):
        """
        Override save method to generate account_id if not provided.
        """

        if not self.chatroom_id:
            self.chatroom_id = self.generate_unique_id('CT')

        super().save(*args, **kwargs)

    @staticmethod
    def generate_unique_id(prefix=''):
        """
        Generate a unique account_id using UUID.
        """

        max_attempts = 10
        for _ in range(max_attempts):
            unique_part = uuid.uuid4().hex[:13]  # Take only the first 13 characters
            id = f"{prefix}{unique_part}"
            if not ChatRoom.objects.filter(chatroom_id=id).exists():
                return id

        raise ValueError('Failed to generate a unique account ID after 10 attempts.')
    

class ChatRoomMessage(models.Model):
    chat_room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE)
    
    sender = models.ForeignKey(CustomUser, on_delete=models.DO_NOTHING)

    edited = models.BooleanField(default=False)
    content = models.TextField()

    last = models.BooleanField(default=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    read_receipt = models.BooleanField(default=False)

