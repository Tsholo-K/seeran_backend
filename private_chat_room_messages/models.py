# python 
import uuid

# django 
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.core.exceptions import ValidationError


class PrivateMessage(models.Model):
    chat_room = models.ForeignKey(
        'private_chat_rooms.PrivateChatRoom',
        on_delete=models.CASCADE,
        related_name='messages'
    )
    unread_by = models.ManyToManyField(
        'accounts.BaseAccount', 
        related_name="unread_messages"
    )
    author = models.ForeignKey(
        'accounts.BaseAccount', 
        on_delete=models.DO_NOTHING
    )

    # Core message content
    message_content = models.TextField(max_length=1024, blank=True, null=True)

    # Media fields
    sticker = models.URLField(blank=True, null=True)  # URL to the sticker
    gif = models.URLField(blank=True, null=True)      # URL to the GIF
    image = models.ImageField(upload_to="chat_images/", blank=True, null=True)
    video = models.FileField(upload_to="chat_videos/", blank=True, null=True)
    voice_note = models.FileField(upload_to="voice_notes/", blank=True, null=True)

    # Message attributes
    edited = models.BooleanField(default=False)
    edited_at = models.DateTimeField(blank=True, null=True)
    is_reply = models.BooleanField(default=False)
    replied_to = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="replies"
    )

    last_message = models.BooleanField(default=True)
    read_receipt = models.BooleanField(default=False)

    last_updated = models.DateTimeField(auto_now=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    private_chat_room_message_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)

    MAX_MESSAGE_LENGTH = 1024

    def save(self, *args, **kwargs):
        # Enforce edit time limit (5 minutes)
        if self.pk and self.edited:
            time_difference = timezone.now() - self.timestamp
            if time_difference.total_seconds() > 300:  # 5 minutes
                raise ValidationError("Messages can only be edited within the first 5 minutes.")

        if self.pk is None:
            self.chat_room.latest_message_timestamp = self.timestamp = timezone.now()
            self.chat_room.save(update_fields=['latest_message_timestamp'])

        super().save(*args, **kwargs)

    def clean(self):
        # Validate message or media presence
        if not self.message_content and not (self.sticker or self.gif or self.image or self.video or self.voice_note):
            raise ValidationError("Message must contain text or a media attachment.")

        # Ensure only one media type is set
        media_fields = [self.sticker, self.gif, self.image, self.video, self.voice_note]
        if sum(1 for field in media_fields if field) > 1:
            raise ValidationError("Only one type of media (sticker, GIF, image, video, voice note) is allowed per message.")

