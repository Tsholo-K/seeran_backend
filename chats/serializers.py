# python 

# django

# rest framework
from rest_framework import serializers

# models
from .models import ChatRoom, ChatRoomMessage

# serializers
from users.serializers.general_serializers import BasicAccountDetailsSerializer


class ChatSerializer(serializers.ModelSerializer):
    
    user = serializers.SerializerMethodField()
    last_message = serializers.SerializerMethodField()
    unread = serializers.SerializerMethodField()

    class Meta:
        model = ChatRoom
        fields = ['user', 'last_message', 'unread']
    
    def get_user(self, obj):
        # Access the user from the context and determine the sender
        user = self.context['user']
        return BasicAccountDetailsSerializer(obj.user_two).data if str(obj.user_one.account_id) == user else BasicAccountDetailsSerializer(obj.user_one).data

    def get_last_message(self, obj):
        # Fetch the latest messages if no cursor is provided
        message = obj.messages.order_by('-timestamp').first()
        serializer = ChatMessageSerializer(message, context={'user': self.context['user']})
        return serializer.data
    
    def get_unread(self, obj):
        user = self.context['user']
        # Count unread messages in the chat room that were not sent by the current user
        unread_count = obj.messages.filter(read_receipt=False).exclude(sender__account_id=user).count()
        return unread_count


class ChatRoomMessageCreationSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = ChatRoomMessage
        fields = ['content', 'timestamp', 'read_receipt']


class ChatMessageSerializer(serializers.ModelSerializer):
    
    read_receipt = serializers.SerializerMethodField()

    class Meta:
        model = ChatRoomMessage
        fields = ['content', 'timestamp', 'read_receipt']

    def get_read_receipt(self, obj):
        return obj.read_receipt


class ChatRoomMessageSerializer(serializers.ModelSerializer):
    
    read_receipt = serializers.SerializerMethodField()
    whos = serializers.SerializerMethodField()

    class Meta:
        model = ChatRoomMessage
        fields = ['content', 'timestamp', 'read_receipt', 'edited', 'last', 'whos']

    def get_read_receipt(self, obj):
        return obj.read_receipt

    def get_whos(self, obj):
        # Access the user from the context and determine the sender
        user = self.context['user']
        return 'mine' if str(obj.sender.account_id) == user else 'theirs'
    
