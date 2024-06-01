# rest framework
from rest_framework import serializers

# models
from .models import Schedule, Session


####################################### admindashboard serializer ############################################


# teacher schedule days
class SchedulesSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = Schedule
        fields = [ 'day', 'schedule_id' ]


# schedule sessions
class SessoinsSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = Session
        fields = [ 'type', 'classroom', 'session_from', 'session_till' ]