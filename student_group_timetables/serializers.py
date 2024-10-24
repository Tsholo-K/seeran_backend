# rest framework
from rest_framework import serializers

# models
from .models import StudentGroupTimetable


class StudentGroupTimetableCreationSerializer(serializers.ModelSerializer):

    class Meta:
        model = StudentGroupTimetable
        fields = ['group_name', 'description', 'grade', 'school']

    def __init__(self, *args, **kwargs):
        super(StudentGroupTimetableCreationSerializer, self).__init__(*args, **kwargs)
        self.fields['description'].required = False


class StudentGroupTimetableUpdateSerializer(serializers.ModelSerializer):

    class Meta:
        model = StudentGroupTimetable
        fields = ['group_name', 'description']

    def __init__(self, *args, **kwargs):
        super(StudentGroupTimetableUpdateSerializer, self).__init__(*args, **kwargs)
        for field in self.fields:
            self.fields[field].required = False


class StudentGroupTimetablesSerializer(serializers.ModelSerializer):

    class Meta:
        model = StudentGroupTimetable
        fields = ['group_name', 'students_count', 'timetables_count', 'group_timetable_id']


class StudentGroupTimetableDetailsSerializer(serializers.ModelSerializer):

    class Meta:
        model = StudentGroupTimetable
        fields = ['group_name', 'description', 'students_count', 'timetables_count']
