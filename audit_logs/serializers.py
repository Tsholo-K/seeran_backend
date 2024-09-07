# python 

# django
from django.utils.translation import gettext_lazy as _

# rest framework
from rest_framework import serializers

# models
from .models import AuditLog

# serializers


class AuditEntiresSerializer(serializers.ModelSerializer):

    actor = serializers.SerializerMethodField()
    outcome = serializers.SerializerMethodField()
    object = serializers.SerializerMethodField()

    class Meta:
        model = AuditLog
        fields = ['actor', 'outcome', 'object', 'timestamp', 'audit_id']

    def get_actor(self, obj):
        return f"{obj.actor.surname} {obj.actor.name}"
        
    def get_outcome(self, obj):
        return obj.outcome.lower()
        
    def get_object(self, obj):
        return obj.target_model.lower()
