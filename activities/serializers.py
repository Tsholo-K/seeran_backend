# python 

# django

# rest framework
from rest_framework import serializers

# models
from .models import Activity
from classes.models import Classroom



class ActivityCreationSerializer(serializers.ModelSerializer):

    classroom = serializers.PrimaryKeyRelatedField(queryset=Classroom.objects.all(), required=False, allow_null=True)

    class Meta:
        model = Activity
        fields = ['offence', 'details', 'logger', 'recipient', 'school', 'classroom']


class ActivitySerializer(serializers.ModelSerializer):

    offence = serializers.SerializerMethodField()
    logger = serializers.SerializerMethodField()

    class Meta:
        model = Activity
        fields = ['offence', 'details', 'date_logged', 'logger']

    def get_offence(self, obj):
        return  obj.offence.title()

    def get_logger(self, obj):
        if  obj.logger:
            return {'name': obj.logger.name.title(), 'surname': obj.logger.surname.title(), 'identifier': obj.logger.account_id, 'image': '/default-user-image.svg'}
        
        return None


class ActivitiesSerializer(serializers.ModelSerializer):

    id = serializers.SerializerMethodField()
    offence = serializers.SerializerMethodField()

    class Meta:
        model = Activity
        fields = ['offence', 'date_logged', 'id']

    def get_id(self, obj):
        return  obj.activity_id

    def get_offence(self, obj):
        return  obj.offence.title()

