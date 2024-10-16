# django
from django.utils.translation import gettext_lazy as _

# rest framework
from rest_framework import serializers

# models
from .models import AuditLog

# serilializers
from accounts.serializers.general_serializers import BasicAccountDetailsEmailSerializer


class AuditEntriesSerializer(serializers.ModelSerializer):

    actor = serializers.SerializerMethodField()

    class Meta:
        model = AuditLog
        fields = ['actor', 'outcome', 'target_model', 'timestamp', 'audit_entry_id']

    def get_actor(self, obj):
        return f'{obj.actor.surname} {obj.actor.name}'


class AuditEntrySerializer(serializers.ModelSerializer):

    actor = serializers.SerializerMethodField()

    class Meta:
        model = AuditLog
        fields = ['actor', 'outcome', 'target_model', 'server_response', 'timestamp']

    def get_actor(self, obj):
        return BasicAccountDetailsEmailSerializer(obj.actor).data
            
