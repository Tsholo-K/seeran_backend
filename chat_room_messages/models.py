# python 
import uuid

# django 
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone


class PrivateMessage(models.Model):
    chat_room = models.ForeignKey('chat_rooms.PrivateChatRoom', on_delete=models.CASCADE, related_name='messages')
    
    author = models.ForeignKey('accounts.BaseAccount', on_delete=models.DO_NOTHING)
    message_content = models.TextField()

    last_message = models.BooleanField(default=True)

    read_receipt = models.BooleanField(default=False)
    edited = models.BooleanField(default=False)
    
    last_updated = models.DateTimeField(auto_now=True)

    timestamp = models.DateTimeField(auto_now_add=True)
    private_chat_room_message_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)

    def save(self, *args, **kwargs):
        self.chat_room.latest_message_timestamp = self.timestamp = timezone.now()
        self.chat_room.save(update_fields=['latest_message_timestamp'])

        super().save(*args, **kwargs)