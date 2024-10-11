# rest framework
from rest_framework import serializers

# models
from .models import TimetableSession


class SessoinsSerializer(serializers.ModelSerializer):
    
    session_from = serializers.TimeField(format='%H:%M')
    session_till = serializers.TimeField(format='%H:%M')

    class Meta:
        model = TimetableSession
        fields = [ 'session_type', 'session_location', 'seesion_start_time', 'seesion_end_time' ]

