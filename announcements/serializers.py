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
    
    id = serializers.SerializerMethodField()
    group_name = serializers.SerializerMethodField()
    students_count = serializers.SerializerMethodField()
    schedules_count = serializers.SerializerMethodField()

    class Meta:
        model = Announcement
        fields = [ 'title', 'message', 'announce_by' ]
    
    def get_id(self, obj):
        return obj.group_schedule_id
    
    def get_group_name(self, obj):
        return obj.group_name.title()
    
    def get_students_count(self, obj):
        return obj.students.count()
    
    def get_schedules_count(self, obj):
        return obj.schedules.count()


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
