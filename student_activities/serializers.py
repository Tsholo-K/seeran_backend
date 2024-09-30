# rest framework
from rest_framework import serializers

# models
from .models import StudentActivity
from classrooms.models import Classroom

# serializers
from accounts.serializers.general_serializers import SourceAccountSerializer


class ActivityCreationSerializer(serializers.ModelSerializer):

    classroom = serializers.PrimaryKeyRelatedField(queryset=Classroom.objects.all(), required=False, allow_null=True)

    class Meta:
        model = StudentActivity
        fields = ['offence', 'details', 'logger', 'recipient', 'school', 'classroom']


class ActivitiesSerializer(serializers.ModelSerializer):

    offence = serializers.SerializerMethodField()

    class Meta:
        model = StudentActivity
        fields = ['offence', 'date_logged', 'activity_id']

    def get_offence(self, obj):
        return  obj.offence.title()


class ActivitySerializer(serializers.ModelSerializer):

    offence = serializers.SerializerMethodField()
    logger = serializers.SerializerMethodField()

    class Meta:
        model = StudentActivity
        fields = ['offence', 'details', 'date_logged', 'logger']

    def get_offence(self, obj):
        return  obj.offence.title()

    def get_logger(self, obj):
        if  obj.logger:
            return SourceAccountSerializer(obj.logger).data
        return None

