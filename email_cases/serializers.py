# rest framework
from rest_framework import serializers

# models
from .models import Case

# serializers
from accounts.serializers.founders.serializers import FounderAccountNamesSerializer, FounderDisplayAccountDetailsSerializer


class EmailCasesSerializer(serializers.ModelSerializer):

    agent = serializers.SerializerMethodField()
    email_address = serializers.SerializerMethodField()

    class Meta:
        model = Case
        fields = ['title', 'email_address', 'updated_at', 'unread_emails',  'agent', 'case_id']

    def get_agent(self, obj):
        return FounderAccountNamesSerializer(obj.agent).data if obj.agent else None
    
    def get_email_address(self, obj):
        if obj.initial_email:
            if obj.initial_email.is_incoming:
                return obj.initial_email.sender
            else:
                return obj.initial_email.recipient              


class EmailCaseSerializer(serializers.ModelSerializer):

    agent = serializers.SerializerMethodField()
    email_address = serializers.SerializerMethodField()

    class Meta:
        model = Case
        fields = ['title', 'description', 'status', 'created_at', 'updated_at', 'unread_emails', 'email_address', 'agent']

    def get_agent(self, obj):
        return FounderDisplayAccountDetailsSerializer(obj.agent).data if obj.agent else None
    
    def get_email_address(self, obj):
        if obj.initial_email:
            if obj.initial_email.is_incoming:
                return obj.initial_email.sender
            else:
                return obj.initial_email.recipient              
