# rest framework
from rest_framework import serializers

# models
from .models import StudentActivity
from classrooms.models import Classroom

# serializers
from accounts.serializers.general_serializers import SourceAccountSerializer


class ActivityCreationSerializer(serializers.ModelSerializer):

    class Meta:
        model = StudentActivity
        fields = ['activity_summary', 'activity_details', 'recipient', 'auditor', 'classroom', 'school']

    def __init__(self, *args, **kwargs):
        super(ActivityCreationSerializer, self).__init__(*args, **kwargs)
        # Make classroom optional 
        self.fields['classroom'].required = False


class ActivitiesSerializer(serializers.ModelSerializer):

    class Meta:
        model = StudentActivity
        fields = ['activity_summary', 'timestamp', 'student_activity_id']


class ActivitySerializer(serializers.ModelSerializer):

    auditor = serializers.SerializerMethodField()

    class Meta:
        model = StudentActivity
        fields = ['activity_summary', 'activity_details', 'timestamp', 'auditor']

    def get_auditor(self, obj):
        if  obj.auditor:
            return SourceAccountSerializer(obj.auditor).data
        return None

