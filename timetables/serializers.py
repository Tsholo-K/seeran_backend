# rest framework
from rest_framework import serializers

# models
from .models import Schedule, Session


####################################### admindashboard serializer ############################################


# teacher schedule days
class SchedulesSerializer(serializers.ModelSerializer):
    
    id = serializers.SerializerMethodField()

    class Meta:
        model = Schedule
        fields = [ 'day', 'id' ]
    
    def get_id(self, obj):
        return obj.schedule_id



# schedule sessions
class SessoinsSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = Session
        fields = [ 'type', 'classroom', 'session_from', 'session_till' ]