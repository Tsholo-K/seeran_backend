# rest framework
from rest_framework import serializers

# models
from .models import PrivateChatRoom

# serializers
from accounts.serializers.general_serializers import BasicAccountDetailsSerializer
from chat_room_messages.serializers import PrivateChatRoomMessageSerializer


class PrivateChatRoomsSerializer(serializers.ModelSerializer):
    
    participant = serializers.SerializerMethodField()
    last_message = serializers.SerializerMethodField()

    class Meta:
        model = PrivateChatRoom
        fields = ['participant', 'last_message']
    
    def get_participant(self, obj):
        # Access the user from the context and determine the sender
        requesting_account = self.context['account']
        return BasicAccountDetailsSerializer(obj.participant_two).data if str(obj.participant_one.account_id) == requesting_account else BasicAccountDetailsSerializer(obj.participant_one).data

    def get_last_message(self, obj):
        # Fetch the latest messages if no cursor is provided
        private_chat_room_last_message = obj.messages.order_by('-timestamp').first()
        return PrivateChatRoomMessageSerializer(private_chat_room_last_message, context={'participant': self.context['account']}).data
    
