# rest framework
from rest_framework import serializers

# models
from .models import GroupSchedule, Schedule, Session


class GroupScheduleSerializer(serializers.ModelSerializer):
    
    id = serializers.SerializerMethodField()
    group_name = serializers.SerializerMethodField()
    students_count = serializers.SerializerMethodField()
    schedules_count = serializers.SerializerMethodField()

    class Meta:
        model = GroupSchedule
        fields = [ 'id', 'group_name', 'students_count', 'schedules_count' ]
    
    def get_id(self, obj):
        return str(obj.group_schedule_id)
    
    def get_group_name(self, obj):
        return obj.group_name.title()
    
    def get_students_count(self, obj):
        return obj.students.count()
    
    def get_schedules_count(self, obj):
        return obj.schedules.count()


# schedule days
class ScheduleSerializer(serializers.ModelSerializer):
    
    id = serializers.SerializerMethodField()
    day = serializers.SerializerMethodField()

    class Meta:
        model = Schedule
        fields = [ 'day', 'id' ]
    
    def get_id(self, obj):
        return str(obj.schedule_id)
    
    def get_day(self, obj):
        return obj.day.title()


# schedule sessions
class SessoinsSerializer(serializers.ModelSerializer):
    
    session_from = serializers.TimeField(format='%H:%M')
    session_till = serializers.TimeField(format='%H:%M')

    class Meta:
        model = Session
        fields = [ 'type', 'classroom', 'session_from', 'session_till' ]

