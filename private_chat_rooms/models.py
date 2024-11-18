# python 
import uuid

# django 
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError


class PrivateChatRoom(models.Model):
    # Many-to-Many relationship with the 'BaseAccount' model using a custom through model
    participants = models.ManyToManyField(
        'accounts.BaseAccount',
        related_name='private_chat_rooms',
        through='PrivateChatRoomMembership'  # Use 'PrivateChatRoomMembership' as the through model
    )

    # Timestamp of the latest message sent in this chat room
    latest_message_timestamp = models.DateTimeField(null=True, blank=True)

    # Boolean flag indicating if there is only one participant left in the chat room
    has_single_participant = models.BooleanField(default=False)

    # Unique identifier for the chat room
    private_chat_room_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)

    def clean(self):
        """
        Custom validation logic to ensure the integrity of the chat room.
        """
        super().clean()
        
        # Retrieve all participants in the chat room and count them
        participants = list(self.participants.all())
        participants_count = len(participants)

        # Validation: Ensure the chat room does not have more than two participants
        if participants_count > 2:
            raise ValidationError("A private chat room must have exactly two participants.")

        # Validation: If there are exactly two participants, ensure they are not the same user
        if participants_count == 2:
            if participants[0] == participants[1]:
                raise ValidationError("A user cannot have a private chat room with themselves.")

        # Set the 'has_single_participant' flag if there is only one participant
        if participants_count == 1:
            self.has_single_participant = True
        else:
            self.has_single_participant = False

        # Validation: Prevent adding a new participant if the chat room has only one participant
        if self.has_single_participant and participants_count > 1:
            raise ValidationError("No additional participants can be added to this chat room.")

        # Validation: Ensure the latest message timestamp is not set to a future date
        if self.latest_message_timestamp and self.latest_message_timestamp > timezone.now():
            raise ValidationError("The latest message timestamp cannot be in the future.")

        # Validation: Check for duplicate chat rooms with the same two participants
        if participants_count == 2:
            # Query for any existing room with the same participants, excluding the current instance
            existing_room = PrivateChatRoom.objects.filter(
                participants=participants[0]
            ).filter(participants=participants[1]).exclude(pk=self.pk)
            
            if existing_room.exists():
                raise ValidationError("A chat room with these participants already exists.")

    def save(self, *args, **kwargs):
        """
        Custom save method to enforce restrictions on participant modifications
        and automatically purge the chat room if necessary.
        """
        # If the chat room has no participants, delete it
        if self.participants.count() == 0:
            self.delete()
        else:
            # Prevent modifications to participants if the chat room already exists
            if self.pk:  # Check if the instance is already saved in the database
                original = PrivateChatRoom.objects.get(pk=self.pk)
                # Compare the original set of participants with the current set
                if set(original.participants.all()) != set(self.participants.all()):
                    raise ValidationError("Participants cannot be modified after the chat room is created.")
            super().save(*args, **kwargs)


class PrivateChatRoomMembership(models.Model):
    """
    Through model to manage the Many-to-Many relationship between
    PrivateChatRoom and BaseAccount, ensuring unique participant entries.
    """
    chat_room = models.ForeignKey(PrivateChatRoom, on_delete=models.CASCADE)
    participant = models.ForeignKey('accounts.BaseAccount', on_delete=models.CASCADE)

    class Meta:
        # Enforce that a participant can only be added once per chat room
        unique_together = ('chat_room', 'participant')



