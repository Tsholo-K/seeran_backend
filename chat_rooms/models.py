# python 
import uuid

# django 
from django.db import models, IntegrityError
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError

# models
from accounts.models import BaseAccount


class PrivateChatRoom(models.Model):
    participant_one  = models.ForeignKey(BaseAccount, on_delete=models.CASCADE, related_name='participant_one')
    participant_two = models.ForeignKey(BaseAccount, on_delete=models.CASCADE, related_name='participant_two')

    last_updated = models.DateTimeField(auto_now=True)
    latest_message_timestamp = models.DateTimeField(null=True, blank=True, default=None)

    timestamp = models.DateTimeField(auto_now_add=True)
    private_chat_room_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)

    def __str__(self):
        return f"Chat between {self.participant_one.surname + ' ' + self.participant_one.name} and {self.participant_two.surname + ' ' + self.participant_two.name}"

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['participant_one', 'participant_two'], name='unique_private_chat_room_participants')
        ]

    def save(self, *args, **kwargs):
        # Call the clean method to ensure proper validation
        self.clean()
        try:
            # Call the parent class's save method to actually save the instance
            super().save(*args, **kwargs)
        except IntegrityError as e:
            # Handle unique constraint violations (e.g., if a duplicate transcript exists)
            if 'unique constraint' in str(e).lower():
                raise ValidationError('Could not process your request, could not create a private chat room betwenn you and the provided account. A private chat room between you and the provided account already exists.')
            raise
        except Exception as e:
            # Catch all other exceptions and raise them as validation errors
            raise ValidationError(_(str(e).lower()))

    def clean(self):
        """
        Ensure participant_one always has a lower ID than participant_two.
        This ensures that the order doesn't matter when creating the chat room.
        """
        if self.participant_one == self.participant_two:
            raise ValidationError('Could not process your request, an account cannot have a private chat with themselves.')

        # Sort participants by their IDs to enforce uniqueness without order
        if self.participant_one.id > self.participant_two.id:
            self.participant_one, self.participant_two = self.participant_two, self.participant_one


