# rest framework
from rest_framework import serializers

# models
from .models import TimetableSession


class SessoinsSerializer(serializers.ModelSerializer):
    
    seesion_start_time = serializers.TimeField(format='%H:%M')
    seesion_end_time = serializers.TimeField(format='%H:%M')

    class Meta:
        model = TimetableSession
        fields = [ 'session_type', 'session_location', 'seesion_start_time', 'seesion_end_time' ]

