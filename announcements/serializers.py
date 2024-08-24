# rest framework
from rest_framework import serializers

# models
from .models import Announcement

# serializers
from users.serializers import BySerializer


class AnnouncementCreationSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = Announcement
        fields = ['title', 'message', 'school', 'announce_by']


class AnnouncementsSerializer(serializers.ModelSerializer):
    
    title = serializers.SerializerMethodField()
    seen = serializers.SerializerMethodField()

    class Meta:
        model = Announcement
        fields = ['title', 'message', 'announced_at', 'seen', 'announcement_id']
    
    def get_title(self, obj):
        return obj.title.title()
    
    def get_seen(self, obj):
        user = self.context.get('user')
        if user:
            return obj.reached.filter(account_id=user).exists()
        return False


class AnnouncementSerializer(serializers.ModelSerializer):
    
    title = serializers.SerializerMethodField()
    announce_by = serializers.SerializerMethodField()

    class Meta:
        model = Announcement
        fields = ['title', 'message', 'announce_by', 'announced_at']
        
    def get_title(self, obj):
        return obj.title.title()

    def get_announce_by(self, obj):    
        if obj.announce_by:
            return BySerializer(obj.announce_by).data
        else:
            return None
    