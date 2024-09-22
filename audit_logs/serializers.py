# django
from django.utils.translation import gettext_lazy as _

# rest framework
from rest_framework import serializers

# models
from .models import AuditLog

# serilializers
from users.serializers.general_serializers import BasicAccountDetailsEmailSerializer


class AuditEntriesSerializer(serializers.ModelSerializer):

    actor = serializers.SerializerMethodField()
    outcome = serializers.SerializerMethodField()
    object = serializers.SerializerMethodField()

    class Meta:
        model = AuditLog
        fields = ['actor', 'outcome', 'object', 'timestamp', 'audit_id']

    def get_actor(self, obj):
        return f"{obj.actor.surname} {obj.actor.name}".title()
        
    def get_outcome(self, obj):
        return obj.get_outcome_display().lower()
        
    # For any choice field FOO, Django automatically generates a method get_FOO_display()
    # that returns the human-readable value of the choice, so you can apply this method 
    # to other choice fields like outcome or action as well, if needed.
    def get_object(self, obj):
        return obj.get_target_model_display().lower()


class AuditEntrySerializer(serializers.ModelSerializer):

    actor = serializers.SerializerMethodField()
    outcome = serializers.SerializerMethodField()
    object = serializers.SerializerMethodField()

    class Meta:
        model = AuditLog
        fields = ['actor', 'outcome', 'object', 'response', 'timestamp']

    def get_actor(self, obj):
        return BasicAccountDetailsEmailSerializer(obj.actor).data
        
    # For any choice field FOO, Django automatically generates a method get_FOO_display()
    # that returns the human-readable value of the choice, so you can apply this method 
    # to other choice fields like outcome or action as well, if needed.
    def get_outcome(self, obj):
        return obj.get_outcome_display()
    
    def get_object(self, obj):
        return obj.get_target_model_display()
