# rest framework
from rest_framework import serializers

# models
from .models import Announcement

# serializers
from accounts.serializers.general_serializers import SourceAccountSerializer


class AnnouncementCreationSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = Announcement
        fields = ['title', 'message', 'announcer', 'school']


class AnnouncementsSerializer(serializers.ModelSerializer):
    
    title = serializers.SerializerMethodField()
    seen = serializers.SerializerMethodField()

    class Meta:
        model = Announcement
        fields = ['title', 'message', 'announced_at', 'seen', 'announcement_id']
    
    def get_title(self, obj):
        return obj.title.title()
    
    def get_seen(self, obj):
        user = self.context.get('account')
        if user:
            return obj.reached.filter(account_id=user).exists()
        return False


class AnnouncementSerializer(serializers.ModelSerializer):
    
    title = serializers.SerializerMethodField()
    announcer = serializers.SerializerMethodField()

    class Meta:
        model = Announcement
        fields = ['title', 'message', 'announcer', 'announced_at']
        
    def get_title(self, obj):
        return obj.title.title()

    def get_announcer(self, obj):    
        if obj.announce_by:
            return SourceAccountSerializer(obj.announce_by).data
        else:
            return None
    