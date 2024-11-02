# python 
import uuid
from enum import Enum

# django 
from django.db import models, IntegrityError
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError

# models
from accounts.models import BaseAccount


class PrivateChatRoom(models.Model):
    participants = models.ManyToManyField('accounts.BaseAccount', related_name='private_chat_rooms')
    latest_message_timestamp = models.DateTimeField(null=True, blank=True)
    private_chat_room_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)

    def clean(self):
        # Validate for Private Chat Room
        participants_count = self.participants.count()
        if participants_count != 2:
            raise ValidationError("A private chat room must have exactly two participants.")

    def save(self, *args, **kwargs):
        if self.pk is None:
            self.latest_message_timestamp = timezone.now()
        super().save(*args, **kwargs)

    def remove_participant(self, participant):
        if participant in self.participants.all():
            self.participants.remove(participant)
            # If only one participant is left, mark messages from the removed participant as null
            if self.participants.count() == 1:
                # Mark the removed participant's messages or manage their presence in the room
                self.purge_messages(participant)  # Optionally remove messages, or just mark them as from None

    def purge_messages(self, participant):
        # Handle logic for purging messages or changing author to None
        messages = self.messages.filter(author=participant)
        # Here you can decide to either delete them or set their author to None
        for message in messages:
            message.author = None  # Or delete the message if you prefer
            message.save()

# @receiver(pre_delete, sender='accounts.BaseAccount')
def handle_account_deletion(sender, instance, **kwargs):
    # Handle account deletion in PrivateChatRoom
    private_chat_rooms = PrivateChatRoom.objects.filter(participants=instance)
    for chat_room in private_chat_rooms:
        chat_room.remove_participant(instance)  # Use the participant removal logic

class GroupChatRoom(models.Model):

    participants = models.ManyToManyField('accounts.BaseAccount', related_name='group_chat_rooms')
    admin = models.ForeignKey('accounts.BaseAccount', on_delete=models.CASCADE, related_name='admin_chat_rooms')

    group_chat_room_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)

    def clean(self):
        # Validate for Group Chat Room
        participants_count = self.participants.count()
        if participants_count < 1:
            raise ValidationError("A group chat room must have at least one participant (the admin).")

    def save(self, *args, **kwargs):
        if self.pk is None:
            self.latest_message_timestamp = timezone.now()
        super().save(*args, **kwargs)

    def add_participant(self, user):
        # Admin can add a participant
        if self.admin == user:
            self.participants.add(user)

    def remove_participant(self, user):
        # Admin can remove a participant, but cannot remove themselves
        if self.admin == user:
            raise ValidationError("Admin cannot remove themselves.")
        self.participants.remove(user)

    def appoint_admin(self, new_admin):
        # Admin can appoint another participant as admin
        if new_admin in self.participants.all():
            self.admin = new_admin
            self.save()
        else:
            raise ValidationError("User must be a participant to be appointed as admin.")

    def revoke_admin(self, admin_to_revoke):
        # Admin can revoke another participant's admin status
        if admin_to_revoke == self.admin:
            raise ValidationError("Cannot revoke the original admin.")
        # Logic to ensure the admin is still in the group
        if admin_to_revoke in self.participants.all():
            # Here you could implement logic to reassign admin or handle as needed
            self.admin = self.participants.first()  # Or some other logic
            self.save()
