# rest framework
from rest_framework import serializers

# models
from .models import PrivateChatRoom, PrivateMessage

# serializers
from accounts.serializers.general_serializers import BasicAccountDetailsSerializer


class PrivateMessageCreationSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = PrivateMessage
        fields = ['chat_room', 'author', 'message_content']


class PrivateChatRoomsSerializer(serializers.ModelSerializer):
    
    participant = serializers.SerializerMethodField()
    last_message = serializers.SerializerMethodField()

    class Meta:
        model = PrivateChatRoom
        fields = ['participant', 'last_message']
    
    def get_participant(self, obj):
        # Access the user from the context and determine the sender
        requesting_account = self.context['user']
        return BasicAccountDetailsSerializer(obj.participant_two).data if str(obj.participant_one.account_id) == requesting_account else BasicAccountDetailsSerializer(obj.participant_one).data

    def get_last_message(self, obj):
        # Fetch the latest messages if no cursor is provided
        private_chat_room_last_message = obj.messages.select_related('message_content', 'timestamp', 'read_receipt').get(timestamp=obj.latest_message_timestamp)
        return PrivateChatRoomsMessageSerializer(private_chat_room_last_message).data


class PrivateChatRoomsMessageSerializer(serializers.ModelSerializer):

    class Meta:
        model = PrivateMessage
        fields = ['message_content', 'timestamp', 'read_receipt']


class PrivateChatRoomMessageSerializer(serializers.ModelSerializer):
    
    whos = serializers.SerializerMethodField()

    class Meta:
        model = PrivateMessage
        fields = ['message_content', 'timestamp', 'read_receipt', 'last', 'whos']

    def get_whos(self, obj):
        # Access the user from the context and determine the sender
        requesting_account = self.context['user']
        return 'mine' if str(obj.author.account_id) == requesting_account else 'theirs'
    
