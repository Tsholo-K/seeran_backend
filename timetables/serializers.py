# rest framework
from rest_framework import serializers

# models
from .models import Schedule, Session


############################################ general serializer ##################################################


# schedule days
class SchedulesSerializer(serializers.ModelSerializer):
    
    id = serializers.SerializerMethodField()
    day = serializers.SerializerMethodField()

    class Meta:
        model = Schedule
        fields = [ 'day', 'id' ]
    
    def get_id(self, obj):
        return obj.schedule_id
    
    def get_day(self, obj):
        return obj.day.title()


# schedule sessions
class SessoinsSerializer(serializers.ModelSerializer):
    
    session_from = serializers.TimeField(format='%H:%M')
    session_till = serializers.TimeField(format='%H:%M')

    class Meta:
        model = Session
        fields = [ 'type', 'classroom', 'session_from', 'session_till' ]


##################################################################################################################
