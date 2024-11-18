# rest framework
from rest_framework import serializers

# models
from .models import PrivateChatRoom

# serializers
from accounts.serializers.general_serializers import BasicAccountDetailsSerializer
from private_chat_room_messages.serializers import PrivateChatRoomMessageSerializer


class PrivateChatRoomsSerializer(serializers.ModelSerializer):
    
    participant = serializers.SerializerMethodField()
    last_message = serializers.SerializerMethodField()
    unread = serializers.SerializerMethodField()

    class Meta:
        model = PrivateChatRoom
        fields = ['participant', 'last_message', 'unread']
    
    def get_participant(self, obj):
        requesting_account = self.context['account']
        # Exclude the requesting user from the participants and serialize the other participant
        other_participant = obj.participants.exclude(account_id=requesting_account).first()
        return BasicAccountDetailsSerializer(other_participant).data if other_participant else None

    def get_last_message(self, obj):
        private_chat_room_last_message = obj.messages.order_by('-timestamp').first()
        # Fetch the latest messages if no cursor is provided
        return PrivateChatRoomMessageSerializer(private_chat_room_last_message, context={'participant': self.context['account']}).data

    def get_unread(self, obj):
        requesting_account = self.context['account']
        # Count unread messages that were not authored by the requesting user
        return obj.messages.filter(read_receipt=False).exclude(author__account_id=requesting_account).count()
    
