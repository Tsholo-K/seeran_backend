# rest framework
from rest_framework import serializers

# models
from .models import StudentGroupTimetable


class StudentGroupScheduleCreationSerializer(serializers.ModelSerializer):

    class Meta:
        model = StudentGroupTimetable
        fields = ['group_name', 'grade', 'school']


class StudentGroupTimetablesSerializer(serializers.ModelSerializer):

    class Meta:
        model = StudentGroupTimetable
        fields = [ 'group_name', 'students_count', 'timetables_count', 'group_timetable_id' ]

