# python 


# django


# rest framework
from rest_framework import serializers

# models
from .models import ChatRoomMessage


class ChatRoomMessageCreationSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = ChatRoomMessage
        fields = [ 'content', 'timestamp', 'read_receipt' ]


class ChatRoomMessageSerializer(serializers.ModelSerializer):
    
    whos = serializers.SerializerMethodField()

    class Meta:
        model = ChatRoomMessage
        fields = ['content', 'timestamp', 'read_receipt', 'edited', 'last', 'whos']

    def get_whos(self, obj):
        # Access the user from the context and determine the sender
        user = self.context['user'].user
        return 'mine' if obj.sender.account_id == user else 'theirs'
    
