# rest framework
from rest_framework import serializers

# models
from .models import Announcement


############################################ general serializer ##################################################


class AnnouncementCreationSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = Announcement
        fields = [ 'title', 'message', 'school', 'announce_by' ]


class AnnouncementSerializer(serializers.ModelSerializer):
    
    title = serializers.SerializerMethodField()
    announce_by = serializers.SerializerMethodField()

    class Meta:
        model = Announcement
        fields = [ 'title', 'message', 'announce_by', 'announced_at' ]
        
    def get_title(self, obj):
        return obj.title.title()

    def get_announce_by(self, obj):    
        if obj.announce_by:
            return { 
                "name" : obj.announce_by.name.title(), 
                "surname" : obj.announce_by.surname.title(), 
                "identifier" : obj.announce_by.account_id, 
                'image': '/default-user-image.svg' 
            }
        else:
            return None


class AnnouncementsSerializer(serializers.ModelSerializer):
    
    title = serializers.SerializerMethodField()
    id = serializers.SerializerMethodField()
    seen = serializers.SerializerMethodField()

    class Meta:
        model = Announcement
        fields = [ 'title', 'message', 'announced_at', 'seen', 'id' ]
    
    def get_title(self, obj):
        return obj.title.title()
    
    def get_id(self, obj):
        return obj.announcement_id
    
    def get_seen(self, obj):
        user = self.context.get('user')
        if user:
            return obj.reached.filter(account_id=user).exists()
        return False
    

##################################################################################################################
