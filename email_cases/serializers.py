# rest framework
from rest_framework import serializers

# models
from .models import Case

# serializers
from accounts.serializers.founders.serializers import FounderAccountNamesSerializer, FounderDisplayAccountDetailsSerializer


class EmailCasesSerializer(serializers.ModelSerializer):

    assigned_to = serializers.SerializerMethodField()

    class Meta:
        model = Case
        fields = ['title', 'created_at', 'updated_at', 'assigned_to', 'case_id']

    def get_assigned_to(self, obj):
        return FounderAccountNamesSerializer(obj.assigned_to).data if obj.assigned_to else None

    # def __init__(self, *args, **kwargs):
    #     super(EmailCasesSerializer, self).__init__(*args, **kwargs)
    #     # Remove the unique together validator that's added by DRF
    #     self.fields['email_address'].validators = []
    #     self.fields['contact_number'].validators = []


class EmailCaseSerializer(serializers.ModelSerializer):

    assigned_to = serializers.SerializerMethodField()

    class Meta:
        model = Case
        fields = ['title', 'description', 'status', 'created_at', 'updated_at', 'assigned_to']

    def get_assigned_to(self, obj):
        return FounderDisplayAccountDetailsSerializer(obj.assigned_to).data if obj.assigned_to else None
