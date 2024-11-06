# rest framework
from rest_framework import serializers

# models
from .models import Email


class EmailMessagesSerializer(serializers.ModelSerializer):

    assigned_to = serializers.SerializerMethodField()

    class Meta:
        model = Email
        fields = ['body', 'is_incoming', 'received_at', 'created_at', 'updated_at']
