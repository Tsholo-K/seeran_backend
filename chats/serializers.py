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

    class Meta:
        model = ChatRoomMessage
        fields = [ 'content', 'timestamp', 'read_receipt', 'edited' ]
    
