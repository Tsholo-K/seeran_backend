# python 


# django


# rest framework
from rest_framework import serializers

# models
from .models import ChatRoom, ChatRoomMessage


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
        return { 'name' : obj.user_two.name.title() , 'surname' : obj.user_two.surname.title(), 'image' : '/default-user-image.svg', 'id' : obj.user_two.account_id} \
            if obj.user_one.account_id == user else \
            {'name' : obj.user_one.name.title(), 'surname' : obj.user_one.surname.title(), 'image' : '/default-user-image.svg', 'id' : obj.user_one.account_id}

    def get_last_message(self, obj):
        # Fetch the latest messages if no cursor is provided
        message = ChatRoomMessage.objects.filter(chat_room=obj).order_by('-timestamp').first()
        serializer = ChatMessageSerializer(message, context={'user': self.context['user']})
        return serializer.data
    
    def get_unread(self, obj):
        user = self.context['user']
        return ChatRoomMessage.objects.filter(chat_room=obj, read_receipt=False, sender__ne=user).count()


class ChatMessageSerializer(serializers.ModelSerializer):
    
    read_receipt = serializers.SerializerMethodField()

    class Meta:
        model = ChatRoomMessage
        fields = ['content', 'timestamp', 'read_receipt']

    def get_read_receipt(self, obj):
        # Access the user from the context and determine the sender
        user = self.context['user']
        return True if obj.sender.account_id == user else obj.read_receipt
    

class ChatRoomMessageCreationSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = ChatRoomMessage
        fields = [ 'content', 'timestamp', 'read_receipt' ]


class ChatRoomMessageSerializer(serializers.ModelSerializer):
    
    read_receipt = serializers.SerializerMethodField()
    whos = serializers.SerializerMethodField()

    class Meta:
        model = ChatRoomMessage
        fields = ['content', 'timestamp', 'read_receipt', 'edited', 'last', 'whos']

    def get_read_receipt(self, obj):
        # Access the user from the context and determine the sender
        user = self.context['user']
        return True if obj.sender.account_id == user else obj.read_receipt

    def get_whos(self, obj):
        # Access the user from the context and determine the sender
        user = self.context['user']
        return 'mine' if obj.sender.account_id == user else 'theirs'
    
