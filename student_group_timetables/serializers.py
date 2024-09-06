# rest framework
from rest_framework import serializers

# models
from .models import StudentGroupTimetable


class StudentGroupScheduleCreationSerializer(serializers.ModelSerializer):

    class Meta:
        model = StudentGroupTimetable
        fields = ['group_name', 'grade']


class StudentGroupScheduleSerializer(serializers.ModelSerializer):
    
    id = serializers.SerializerMethodField()
    group_name = serializers.SerializerMethodField()
    students_count = serializers.SerializerMethodField()
    schedules_count = serializers.SerializerMethodField()

    class Meta:
        model = StudentGroupTimetable
        fields = [ 'id', 'group_name', 'students_count', 'schedules_count' ]
    
    def get_id(self, obj):
        return str(obj.group_schedule_id)
    
    def get_group_name(self, obj):
        return obj.group_name.title()
    
    def get_students_count(self, obj):
        return obj.students.count()
    
    def get_schedules_count(self, obj):
        return obj.schedules.count()
