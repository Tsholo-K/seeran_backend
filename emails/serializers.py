# rest framework
from rest_framework import serializers

# models
from .models import Email


class EmailMessagesSerializer(serializers.ModelSerializer):

    class Meta:
        model = Email
        fields = ['body', 'is_incoming', 'received_at']
