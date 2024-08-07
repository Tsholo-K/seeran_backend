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
        request_user = self.context['request'].user
        return 'mine' if obj.sender == request_user else 'theirs'
    
