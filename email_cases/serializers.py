# rest framework
from rest_framework import serializers

# models
from .models import Case

# serializers
from accounts.serializers.founders.serializers import FounderAccountNamesSerializer, FounderDisplayAccountDetailsSerializer


class EmailCasesSerializer(serializers.ModelSerializer):

    assigned_to = serializers.SerializerMethodField()
    email_address = serializers.SerializerMethodField()

    class Meta:
        model = Case
        fields = ['title', 'email_address', 'updated_at', 'assigned_to', 'case_id']

    def get_assigned_to(self, obj):
        return FounderAccountNamesSerializer(obj.assigned_to).data if obj.assigned_to else None
    
    def get_email_address(self, obj):
        if obj.initial_email:
            if obj.initial_email.is_incoming:
                return obj.initial_email.sender
            else:
                return obj.initial_email.recipient_email                


class EmailCaseSerializer(serializers.ModelSerializer):

    assigned_to = serializers.SerializerMethodField()
    email_address = serializers.SerializerMethodField()

    class Meta:
        model = Case
        fields = ['title', 'description', 'status', 'created_at', 'updated_at', 'email_address', 'assigned_to']

    def get_assigned_to(self, obj):
        return FounderDisplayAccountDetailsSerializer(obj.assigned_to).data if obj.assigned_to else None
    
    def get_email_address(self, obj):
        if obj.initial_email:
            if obj.initial_email.is_incoming:
                return obj.initial_email.sender
            else:
                return obj.initial_email.recipient_email                
