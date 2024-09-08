# python 
import uuid

# django 
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone

# models
from users.models import BaseUser


class ChatRoom(models.Model):
    user_one = models.ForeignKey(BaseUser, on_delete=models.CASCADE, related_name='user_one')
    user_two = models.ForeignKey(BaseUser, on_delete=models.CASCADE, related_name='user_two')

    latest_message_timestamp = models.DateTimeField(null=True, blank=True, default=None)
    last_updated = models.DateTimeField(auto_now=True)

    chatroom_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)

    def __str__(self):
        return f"Chat between {self.user_one.surname + ' ' + self.user_one.name} and {self.user_two.surname + ' ' + self.user_two.name}"

    def save(self, *args, **kwargs):
        if self.pk is None:
            # This means the object is being created
            self.last_updated = timezone.now()
        super().save(*args, **kwargs)


class ChatRoomMessage(models.Model):
    chat_room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE, related_name='messages')
    
    sender = models.ForeignKey(BaseUser, on_delete=models.DO_NOTHING)

    edited = models.BooleanField(default=False)
    content = models.TextField()

    last = models.BooleanField(default=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    read_receipt = models.BooleanField(default=False)
    
    last_updated = models.DateTimeField(auto_now=True)

    chatroom_message_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)

    def save(self, *args, **kwargs):
        if self.pk is None:
            # This means the object is being created
            self.last_updated = timezone.now()
        super().save(*args, **kwargs)

