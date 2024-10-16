# rest framework
from rest_framework import serializers

# models
from .models import Announcement

# serializers
from accounts.serializers.general_serializers import SourceAccountSerializer


class AnnouncementCreationSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = Announcement
        fields = ['announcement_title', 'announcement_message', 'announcer', 'school']


class AnnouncementsSerializer(serializers.ModelSerializer):
    
    seen = serializers.SerializerMethodField()

    class Meta:
        model = Announcement
        fields = ['announcement_title', 'announcement_message', 'timestamp', 'seen', 'announcement_id']
    
    def get_seen(self, obj):
        user = self.context.get('account')
        return obj.accounts_reached.filter(account_id=user).exists() if user else False


class AnnouncementSerializer(serializers.ModelSerializer):
    
    announcer = serializers.SerializerMethodField()

    class Meta:
        model = Announcement
        fields = ['announcement_title', 'announcement_message', 'timestamp', 'announcer']

    def get_announcer(self, obj):    
        return SourceAccountSerializer(obj.announcer).data if obj.announcer else None
       
    