# rest framework
from rest_framework import serializers

# models
from .models import PrivateMessage


class PrivateMessageCreationSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = PrivateMessage
        fields = ['chat_room', 'author', 'message_content']


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