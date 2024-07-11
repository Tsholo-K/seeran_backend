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

    def __str__(self):
        return f"Chat between {self.user_one.surname + ' ' + self.user_one.name} and {self.user_two.surname + ' ' + self.user_two.name}"


class ChatRoomMessage(models.Model):
    chat_room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE)
    
    sender = models.ForeignKey(CustomUser, on_delete=models.DO_NOTHING)
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    
    read_receipt = models.BooleanField(default=False)

    def mark_as_read(self):
        self.read_receipt = True
        self.save()

